"""Serve aggregate training telemetry on loopback; never modify a run."""
import argparse
from datetime import datetime, timezone
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
from pathlib import Path
import time
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
ASSETS = Path(__file__).parent


def read_json(path, fallback=None):
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return fallback


def timestamp(value):
    try:
        return datetime.fromisoformat(value).timestamp()
    except (ValueError, TypeError):
        return None


def numeric(value):
    return isinstance(value, (int, float)) and math.isfinite(value)


def history(path):
    """Minute means for speed; minute endpoints for exposure. Keep resume gaps."""
    segments, development, sessions = [], [], []
    current = None
    last_time = None
    buckets = {}
    bad_lines = 0
    pending_start = None

    def flush():
        nonlocal buckets, pending_start
        if buckets:
            segments.append(([pending_start] if pending_start is not None else []) + [dict(time=b['time'], step=b['step'], tokens=b['tokens'],
                                  speed=b['speed_sum']/b['count']) for b in buckets.values()])
        buckets = {}
        pending_start = None

    try:
        f = path.open()
    except FileNotFoundError:
        return dict(segments=[], development=[], sessions=[], incomplete_lines=0)
    with f:
        for line in f:
            try:
                row = json.loads(line)
            except ValueError:
                # A writer may currently be appending the final JSONL record.
                bad_lines += 1
                continue
            at = timestamp(row.get('time'))
            if at is None:
                continue
            event = row.get('event')
            if sessions and event != 'start':
                sessions[-1]['end'] = max(sessions[-1]['end'], at)
            if event == 'start':
                flush()
                current = at
                pending_start = dict(time=at, step=row.get('step'), tokens=row.get('tokens'), speed=None)
                last_time = None
                sessions.append(dict(time=at, end=at, step=row.get('step'), tokens=row.get('tokens'), resumed=row.get('resumed', False)))
            elif event == 'development' and numeric(row.get('macro_answer_loss')):
                development.append(dict(time=at, loss=row['macro_answer_loss'], step=row.get('step'), session=current))
            elif event == 'train' and all(numeric(row.get(k)) for k in ['step', 'tokens', 'tokens_per_second']):
                if last_time is not None and at-last_time > 180:
                    flush()
                last_time = at
                minute = int(at//60)
                b = buckets.setdefault(minute, dict(speed_sum=0., count=0))
                b.update(time=at, step=row['step'], tokens=row['tokens'])
                b['speed_sum'] += row['tokens_per_second']
                b['count'] += 1
            elif event == 'finished':
                flush()
    flush()
    return dict(segments=segments, development=development, sessions=sessions, incomplete_lines=bad_lines)


def process_present(pid):
    if not isinstance(pid, int):
        return False
    import psutil
    try:
        p = psutil.Process(pid)
        return p.is_running() and p.status() != psutil.STATUS_ZOMBIE
    except psutil.Error:
        return False


def snapshot(run):
    now = time.time()
    state = read_json(run/'status.json', {})
    trainer = read_json(run/'model/status.json', {})
    best = read_json(run/'model/best.json', {})
    latest = read_json(run/'model/latest.json', {})
    checkpoint = latest.get('checkpoint')
    saved = {}
    if checkpoint and Path(checkpoint).name == checkpoint:
        saved = read_json(run/'model'/checkpoint/'state.json', {})
    config = read_json(run/'model/config.json', {})
    heartbeat = timestamp(state.get('heartbeat'))
    age = max(0, now-heartbeat) if heartbeat is not None else None
    supervisor_alive = process_present(state.get('pid'))
    status = state.get('status', 'unknown')
    fresh = age is not None and age <= 90
    live = status == 'running' and fresh and supervisor_alive
    # Paused trainer status can still say running; show the recoverable checkpoint.
    recoverable = status == 'paused'
    progress = saved if recoverable else trainer
    metrics = history(run/'model/metrics.jsonl')
    evaluations = []
    for name in ['final-dev', 'final-confirmation']:
        summary = read_json(run/'evaluations'/name/'summary.json')
        suite = read_json(Path(config.get('data', '.'))/(name.removeprefix('final-')+'-suite.json'), {}) if summary else {}
        expected = len(suite.get('general', []))
        complete = bool(summary and expected and summary.get('evaluated_general') == expected
                        and summary.get('answer_loss', {}).get('examples') == expected
                        and not summary.get('deadline_reached')
                        and not any(v.get('context_exceeded') for v in summary.get('by_source', {}).values()))
        evaluations.append(dict(name=name, completed=complete,
                                evaluated=summary.get('evaluated_general') if summary else None))
    return dict(generated_at=now, run=run.name, status=status, phase=state.get('phase', 'unknown'),
                live=live, heartbeat_age=age, supervisor_alive=supervisor_alive, error=state.get('error'),
                stop=(run/'STOP').exists(), started=timestamp(state.get('started')),
                deadline=timestamp(state.get('deadline')), training_until=timestamp(config.get('until')),
                extension_started=timestamp(state.get('extension', {}).get('budget_started')),
                active_seconds=state.get('active_controller_seconds', state.get('budget_spent_seconds')),
                steps=progress.get('step'), tokens=progress.get('tokens'), recoverable=recoverable,
                speed=trainer.get('tokens_per_second') if live and state.get('phase') == 'training'
                and now-(timestamp(trainer.get('updated_at')) or 0) <= 90 else None,
                best_dev_loss=best.get('macro_answer_loss'), checkpoint=checkpoint,
                checkpoint_step=saved.get('step'), checkpoint_tokens=saved.get('tokens'),
                trainer_updated=timestamp(trainer.get('updated_at', trainer.get('finished_at'))),
                parameters=config.get('parameters'), evaluations=evaluations, report_ready=(run/'REPORT.md').exists(),
                history=metrics)


class Handler(BaseHTTPRequestHandler):
    def __init__(self, *args, run, **kwargs):
        self.run = run
        super().__init__(*args, **kwargs)

    def do_GET(self):
        # Refuse arbitrary Host headers (including DNS rebinding).
        if self.headers.get('Host', '').split(':')[0] not in ['127.0.0.1', 'localhost']:
            self.send_error(403)
            return
        route = urlsplit(self.path).path
        try:
            if route == '/api/status':
                content = json.dumps(snapshot(self.run), allow_nan=False).encode()
                kind = 'application/json; charset=utf-8'
            elif route in ['/', '/app.js', '/time_axis.js', '/style.css']:
                filename = {'/': 'index.html', '/app.js': 'app.js', '/time_axis.js': 'time_axis.js', '/style.css': 'style.css'}[route]
                content = (ASSETS/filename).read_bytes()
                kind = {'/': 'text/html', '/app.js': 'text/javascript', '/time_axis.js': 'text/javascript', '/style.css': 'text/css'}[route]+'; charset=utf-8'
            else:
                self.send_error(404)
                return
        except (OSError, ValueError, TypeError) as exc:
            content = json.dumps({'error': 'Unable to read a consistent snapshot; refresh again.', 'type': type(exc).__name__}).encode()
            kind = 'application/json; charset=utf-8'
            self.send_response(503)
        else:
            self.send_response(200)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, *args):
        pass


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', required=True, type=Path)
    p.add_argument('--port', type=int, default=8765)
    args = p.parse_args()
    run = args.run.resolve()
    if not (run/'status.json').is_file():
        p.error('Select a campaign directory containing status.json')
    server = ThreadingHTTPServer(('127.0.0.1', args.port), partial(Handler, run=run))
    print(f'Training dashboard: http://127.0.0.1:{server.server_port} — {run.name}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
