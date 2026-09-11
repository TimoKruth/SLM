#!/usr/bin/env python3
"""Bounded, read-only summary of local SLM campaign artifacts; no ML imports."""
import argparse
import datetime as dt
import json
from pathlib import Path
import subprocess
import sys
import time

ACTIVE = {"running", "starting", "evaluating", "training"}
MAX_BYTES = 2_000_000


def read_json(path, errors):
    try:
        with path.open("rb") as file:
            raw = file.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError("JSON exceeds 2 MB limit")
        return json.loads(raw)
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as exc:
        errors.append({"file": str(path), "error": str(exc)})
        return None


def timestamp(value):
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.timestamp() if parsed.tzinfo else None
    except (AttributeError, TypeError, ValueError, OverflowError):
        return None


def iso(value):
    return dt.datetime.fromtimestamp(value).astimezone().isoformat(timespec="seconds")


def age(path, now):
    try:
        return round(now - path.stat().st_mtime, 1)
    except OSError:
        return None


def process(pid):
    if not isinstance(pid, int) or pid <= 0:
        return {"pid": pid, "present": None}
    try:
        result = subprocess.run(["ps", "-p", str(pid), "-o", "stat="],
                                capture_output=True, text=True, timeout=2)
        state = result.stdout.strip()
        if result.returncode not in (0, 1):
            return {"pid": pid, "present": None, "error": "ps failed"}
        return {"pid": pid, "present": bool(state), "state": state or None,
                "zombie": state.startswith("Z")}
    except (OSError, subprocess.TimeoutExpired):
        return {"pid": pid, "present": None}


def discover(project, errors, now):
    candidates = []
    for path in sorted((project / "runs").glob("*/status.json")):
        data = read_json(path, errors)
        if not isinstance(data, dict) or "status" not in data:
            continue
        # Exclude standalone trial/system-status files from automatic campaign selection.
        if not any(k in data for k in ("stages", "phase", "finished_at", "started", "finished")):
            continue
        stamp = next((timestamp(data.get(k)) for k in
                      ("heartbeat", "finished", "finished_at", "started")
                      if timestamp(data.get(k)) is not None), 0)
        active = data.get("status") in ACTIVE
        candidates.append({"run": str(path.parent), "status": data["status"],
                           "phase": data.get("phase"), "timestamp": stamp,
                           "status_age_seconds": age(path, now),
                           "process": process(data.get("pid")) if active else None})
    plausible = [c for c in candidates if c["status"] in ACTIVE and
                 c["process"]["present"] is not False and not c["process"].get("zombie")]
    if len(plausible) == 1:
        return Path(plausible[0]["run"]), candidates
    if len(plausible) > 1:
        return None, plausible
    latest = max(candidates, key=lambda c: c["timestamp"], default=None)
    return (Path(latest["run"]) if latest else None), candidates


def summarize(run, now, errors):
    data = read_json(run / "status.json", errors)
    if not isinstance(data, dict):
        return {"run": str(run), "error": "missing_or_invalid_status"}
    result = {"run": str(run), "status": data.get("status"), "phase": data.get("phase"),
              "warnings": [], "status_age_seconds": age(run / "status.json", now)}
    for key in ("started", "finished", "finished_at", "deadline", "heartbeat", "evonn_current",
                "total_budget_spent_seconds", "frozen_inputs_unchanged"):
        if key in data:
            result[key] = data[key]
    heartbeat = timestamp(data.get("heartbeat"))
    result["heartbeat_age_seconds"] = round(now - heartbeat, 1) if heartbeat else None
    deadline = timestamp(data.get("deadline"))
    if deadline:
        result["budget_seconds_remaining_now"] = max(0, round(deadline - now))
    if data.get("status") in ACTIVE:
        result["supervisor_process"] = process(data.get("pid"))
        freshness = result["heartbeat_age_seconds"]
        if freshness is None:
            freshness = result["status_age_seconds"]
        if freshness is None or freshness > 180:
            result["warnings"].append("stale_or_missing_liveness_timestamp")
        if freshness is not None and freshness < -5:
            result["warnings"].append("timestamp_in_future_check_clock")
        if result["supervisor_process"]["present"] is False or result["supervisor_process"].get("zombie"):
            result["warnings"].append("recorded_running_but_supervisor_not_live")
        if deadline and now > deadline:
            result["warnings"].append("recorded_running_past_deadline")
    if (run / "STOP").exists():
        result["warnings"].append("STOP_file_present")
    plan = read_json(run / "plan.json", errors)
    jobs = plan.get("jobs", []) if isinstance(plan, dict) else []
    jobs = jobs if isinstance(jobs, list) else []
    job_names = [j if isinstance(j, str) else j.get("name") for j in jobs if isinstance(j, (str, dict))]
    raw_stages = data.get("stages", [])
    stages = [s for s in raw_stages if isinstance(s, dict)] if isinstance(raw_stages, list) else []
    result["stages_completed"] = sum(s.get("status") == "completed" for s in stages)
    result["unsuccessful_stages"] = [{k: s[k] for k in ("name", "status", "exit_code") if k in s}
                                        for s in stages if s.get("status") in ("failed", "timeout", "paused")
                                        or s.get("exit_code") not in (None, 0)]
    # Distinguish training count from evaluation stages and controls.
    train_stages = [s for s in stages if s.get("name") in job_names]
    completed_names = {s.get("name") for s in train_stages if s.get("status") == "completed"}
    result["training_counts"] = {"planned": len(job_names) or None,
        "completed": len(completed_names) if job_names else None}
    result["completed_training"] = []
    for name in sorted(completed_names):
        if not isinstance(name, str) or Path(name).name != name or name in ("", ".", ".."):
            continue
        trial = read_json(run / "trials" / name / "status.json", errors)
        if isinstance(trial, dict):
            result["completed_training"].append({"name": name, **{k: trial[k] for k in
                ("status", "additional_tokens", "cumulative_tokens", "elapsed_seconds", "endpoint") if k in trial}})
    active = [s for s in stages if s.get("status") in ACTIVE]
    result["active_stages"] = []
    for stage in active:
        current = {k: stage[k] for k in ("name", "module", "started", "maximum_seconds") if k in stage}
        current["process"] = process(stage.get("pid"))
        if current["process"]["present"] is False or current["process"].get("zombie"):
            result["warnings"].append("active_stage_process_not_live: " + str(stage.get("name")))
        start = timestamp(stage.get("started"))
        budget = stage.get("maximum_seconds")
        if start:
            current["wall_elapsed_seconds"] = round(now - start)
            if isinstance(budget, (int, float)) and budget > 0:
                current["stage_budget_end_estimate"] = iso(start + budget)
                current["budget_fraction_elapsed"] = round((now - start) / budget, 4)
        name = stage.get("name", "")
        if isinstance(name, str) and Path(name).name == name and name not in ("", ".", ".."):
            trial_path = run / "trials" / name / "status.json"
            trial = read_json(trial_path, errors)
            if isinstance(trial, dict):
                current["training"] = {k: trial[k] for k in
                    ("status", "event", "step", "additional_tokens", "cumulative_tokens", "elapsed_seconds", "lr") if k in trial}
                current["training_status_age_seconds"] = age(trial_path, now)
                if current["training_status_age_seconds"] is not None and current["training_status_age_seconds"] > 180:
                    result["warnings"].append("active_training_status_stale: " + name)
        result["active_stages"].append(current)
    quality = read_json(run / "quality.json", errors)
    if isinstance(quality, list):
        result["quality"] = [{k: row[k] for k in ("repetition", "condition", "endpoint", "accuracy", "answer_loss") if k in row}
                             for row in quality if isinstance(row, dict)]
        result["quality_file_age_seconds"] = age(run / "quality.json", now)
    assessment = read_json(run / "assessment.json", errors)
    if assessment:
        result["assessment"] = assessment
    result["condition_files"] = [str(run / name) for name in
                                 ("RUN_CONDITIONS.json", "RUN_CONDITIONS.md", "START_AUTHORIZATION.json") if (run / name).exists()]
    return result


def resources():
    script = Path.home() / ".codex/skills/read-system-resources/scripts/snapshot.py"
    try:
        output = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, timeout=8)
        if output.returncode:
            return {"error": "resource helper failed", "exit_code": output.returncode}
        data = json.loads(output.stdout)
        window = data.get("window", {})
        return {"latest": data.get("latest"), "live_memory": data.get("live_memory"),
                "cpu_5min": window.get("cpu_busy_pct"), "gpu_5min": window.get("gpu_device_pct"),
                "swapouts_5min": window.get("swapouts"), "sample_count": window.get("sample_count"),
                "warnings": data.get("warnings", []), "error": data.get("powerwatch_error")}
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        return {"error": str(exc)}


def main():
    started = time.perf_counter()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--run", type=Path)
    parser.add_argument("--resources", action="store_true")
    args = parser.parse_args()
    now = time.time()
    errors = []
    run = args.run.expanduser().resolve() if args.run else None
    candidates = []
    if run is None:
        run, candidates = discover(args.project.expanduser().resolve(), errors, now)
    result = {"queried_at": iso(now)}
    if run:
        result.update(summarize(run, now, errors))
    else:
        result.update({"error": "ambiguous_campaigns" if candidates else "no_campaign_found", "candidates": candidates})
    if args.resources:
        result["resources"] = resources()
    result["read_errors"] = errors
    result["query_elapsed_ms"] = round((time.perf_counter() - started) * 1000, 1)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
