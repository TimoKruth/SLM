"""Local, sandboxed development code diagnostic; never an official benchmark score."""
import argparse
import ast
from collections import Counter
from datetime import datetime
import hashlib
import json
import math
import os
import re
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import uuid
import psutil

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sandbox_profile(directory):
    # macOS Seatbelt is inherited by executed code. No credentials/home access,
    # networking, forks or writes outside an ephemeral task directory.
    paths = ['/System', '/usr', '/Library', '/private/var/db', sys.base_prefix,
             str(Path(sys.prefix).resolve()), str(Path(directory).resolve())]
    allows = ' '.join('(subpath ' + json.dumps(p) + ')' for p in paths)
    return f'''(version 1)
(allow default)
(deny network*)
(deny process-fork)
(deny file-read* (subpath "/Users") (subpath "/Volumes") (subpath "/private") (subpath "/tmp"))
(deny file-write*)
(allow file-read* {allows} (literal "/dev/null") (literal "/dev/urandom"))
(allow file-write* (subpath {json.dumps(str(Path(directory).resolve()))}) (literal "/dev/null"))
'''


def run_python(code, stdin='', timeout=3):
    with tempfile.TemporaryDirectory(prefix='slm-eval-') as tmp:
        d = Path(tmp).resolve()
        (d / 'sandbox.sb').write_text(sandbox_profile(d))
        (d / 'candidate.py').write_text(code)
        # Limits are set before evaluating the candidate, inside the sandbox.
        (d / 'runner.py').write_text("import resource\nresource.setrlimit(resource.RLIMIT_CPU, (2, 2))\nresource.setrlimit(resource.RLIMIT_FSIZE, (1048576, 1048576))\nresource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))\nresource.setrlimit(resource.RLIMIT_CORE, (0, 0))\nexec(compile(open('candidate.py').read(), 'candidate.py', 'exec'), {'__name__': '__main__'})\n")
        (d / 'input').write_text(stdin)
        with (d / 'input').open() as inp, (d / 'stdout').open('w+') as out, (d / 'stderr').open('w+') as err:
            p = subprocess.Popen(['/usr/bin/sandbox-exec', '-f', str(d / 'sandbox.sb'), str(Path(sys.executable).resolve()), '-I', '-B', str(d / 'runner.py')], stdin=inp, stdout=out, stderr=err, cwd=d, start_new_session=True, env={'PATH': '/usr/bin:/bin', 'TMPDIR': str(d), 'HOME': str(d), 'LC_ALL': 'C.UTF-8'})
            timed_out = False
            memory_exceeded = False
            deadline = time.monotonic() + timeout
            while p.poll() is None:
                timed_out = time.monotonic() >= deadline
                try:
                    memory_exceeded = psutil.Process(p.pid).memory_info().rss > 512 * 1024**2
                except psutil.NoSuchProcess:
                    pass
                if timed_out or memory_exceeded:
                    try:
                        os.killpg(p.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    p.wait()
                    break
                time.sleep(0.01)
            out.seek(0); err.seek(0)
            return {'returncode': p.returncode, 'timeout': timed_out, 'memory_exceeded': memory_exceeded, 'stdout': out.read(1048576), 'stderr': err.read(4000)}


def same_output(actual, expected):
    # APPS-style whitespace token comparison, with numeric tolerance; no unordered matching.
    aa, bb = actual.split(), expected.split()
    if len(aa) != len(bb):
        return False
    for a, b in zip(aa, bb):
        if a == b:
            continue
        if re.fullmatch(r'[-+]?\d+', a) and re.fullmatch(r'[-+]?\d+', b):
            if int(a) != int(b):
                return False
            continue
        try:
            if not math.isclose(float(a), float(b), rel_tol=1e-6, abs_tol=1e-6):
                return False
        except ValueError:
            return False
    return True


def score(code, task):
    try:
        ast.parse(code)
    except (SyntaxError, ValueError) as e:
        return {'status': 'syntax_error', 'syntax_valid': False, 'passed_cases': 0, 'total_cases': len(task['cases']), 'detail': str(e)}
    passed = 0
    for index, case in enumerate(task['cases']):
        if task['source'] == 'mbpp':
            marker = 'SLM_ASSERT_OK_' + uuid.uuid4().hex
            script = task.get('setup', '') + '\n' + code + '\n' + case['assertion'] + '\nprint(' + repr(marker) + ')\n'
            stdin = ''
        else:
            script, stdin = code, case['input']
        r = run_python(script, stdin)
        if r['timeout']:
            status = 'timeout'
        elif r['returncode']:
            status = 'wrong_answer' if task['source'] == 'mbpp' and r['stderr'].rstrip().endswith('AssertionError') else 'runtime_error'
        elif task['source'] == 'mbpp' and marker not in r['stdout'].splitlines():
            status = 'wrong_answer'
        elif task['source'] == 'apps' and not same_output(r['stdout'], case['output']):
            status = 'wrong_answer'
        else:
            passed += 1
            continue
        return {'status': status, 'syntax_valid': True, 'passed_cases': passed, 'total_cases': len(task['cases']), 'first_failure': index, 'detail': r['stderr'][-1000:], 'actual': r['stdout'][:1000]}
    return {'status': 'passed', 'syntax_valid': True, 'passed_cases': passed, 'total_cases': len(task['cases'])}


def load_tasks():
    import pyarrow.parquet as pq
    dev = {}
    for line in (ROOT / 'data/records.jsonl').open():
        row = json.loads(line)
        if row['source'] in ('apps', 'mbpp') and row['split'] == 'dev':
            key = (row['source'], row['original_id'])
            dev.setdefault(key, {'row': row, 'references': []})['references'].append(row['answer'])
    tasks = []
    excluded = Counter()
    for line in (ROOT / 'data/raw/apps/train.jsonl').open():
        raw = json.loads(line)
        key = ('apps', str(raw['id']))
        if key not in dev:
            continue
        io = json.loads(raw['input_output'] or '{}')
        if io.get('fn_name'):
            excluded['apps_function_interface_not_implemented'] += 1
            continue
        if not io.get('inputs') or len(io['inputs']) != len(io.get('outputs', [])):
            excluded['apps_missing_or_unaligned_tests'] += 1
            continue
        for field in ('inputs', 'outputs'):
            io[field] = ['\n'.join(v) if isinstance(v, list) and all(isinstance(x, str) for x in v) else v for v in io[field]]
        if not all(isinstance(v, str) for v in io['inputs'] + io['outputs']):
            excluded['apps_non_string_stdio'] += 1
            continue
        tasks.append(dict(source='apps', id=key[1], prompt=dev[key]['row']['prompt'], references=dev[key]['references'], cases=[dict(input=a, output=b) for a, b in zip(io['inputs'], io['outputs'])], difficulty=raw['difficulty']))
    for raw in pq.read_table(ROOT / 'data/raw/mbpp/full/train-00000-of-00001.parquet').to_pylist():
        key = ('mbpp', str(raw['task_id']))
        if key in dev:
            tasks.append(dict(source='mbpp', id=key[1], prompt=dev[key]['row']['prompt'], references=dev[key]['references'], setup=raw['test_setup_code'], cases=[{'assertion': s} for s in raw['test_list']]))
    return sorted(tasks, key=lambda t: (t['source'], int(t['id']))), dict(excluded)


def generate(model, tokenizer, prompt, maximum=512, cached=True):
    """Generate one bounded answer, with an eager path retained for equivalence checks."""
    from .inference import greedy_generate
    return greedy_generate(model, tokenizer, prompt, maximum, cached=cached)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', default='runs/night-2026-09-06')
    parser.add_argument('--output', default='runs/code-eval-2026-09-07')
    args = parser.parse_args()
    run, output = ROOT / args.run, ROOT / args.output
    output.mkdir(exist_ok=True, parents=True)
    assert not (output / 'results.jsonl').exists(), 'Refuse to overwrite an evaluation'
    tasks, exclusions = load_tasks()
    protocol = dict(created=datetime.now().astimezone().isoformat(), checkpoint=str(run / 'best.safetensors'), checkpoint_sha256=sha(run / 'best.safetensors'), checkpoint_selection=json.loads((run / 'best.json').read_text()), tokenizer_sha256=sha(run / 'tokenizer.json'), records_sha256=sha(ROOT / 'data/records.jsonl'), evaluator_sha256=sha(__file__), tasks=[{'source': t['source'], 'id': t['id'], 'test_cases': len(t['cases'])} for t in tasks], exclusions=exclusions, decoding='one greedy generation, at most 512 new tokens within original 1024 context, no retries or code repair', scope='internal development, original prompts, all original cases for selected tasks; no official held-out benchmarks; MBPP prompts lack function signatures as in training', timeout_seconds_per_case=3, external_benchmarks_loaded=False)
    (output / 'protocol.json').write_text(json.dumps(protocol, indent=2))
    # Validate infrastructure before any model execution.
    assert run_python('print(42)')['stdout'].strip() == '42'
    assert run_python("open('/Users/timokruth/Projekte/SLM/README.md').read()")['returncode'] != 0
    assert run_python("import socket; socket.socket().connect(('1.1.1.1',80))")['returncode'] != 0
    validated = []
    for i, task in enumerate(tasks):
        checks = []
        for ref in task['references']:
            checks.append(score(ref, task))
            if checks[-1]['status'] == 'passed':
                break
        valid = checks[-1]['status'] == 'passed'
        entry = {'source': task['source'], 'id': task['id'], 'reference_valid': valid, 'reference_checks': checks}
        with (output / 'reference_checks.jsonl').open('a') as f:
            f.write(json.dumps(entry) + '\n')
        if valid:
            validated.append(task)
        print(f'Reference {i+1}/{len(tasks)} {task["source"]}:{task["id"]} {valid}', flush=True)
    import mlx.core as mx
    from tokenizers import Tokenizer
    from .model import LanguageModel, ModelConfig
    mx.set_memory_limit(8 * 1024**3); mx.set_cache_limit(512 * 1024**2)
    config = json.loads((run / 'config.json').read_text())
    model = LanguageModel(ModelConfig(**config['model']))
    model.load_weights(str(run / 'best.safetensors')); model.eval()
    mx.eval(model.parameters())
    tokenizer = Tokenizer.from_file(str(run / 'tokenizer.json'))
    results = []
    for i, task in enumerate(validated):
        begin = time.monotonic()
        generated = generate(model, tokenizer, task['prompt'])
        result = dict(source=task['source'], id=task['id'], prompt=task['prompt'], **generated, **score(generated['generated'], task), seconds=time.monotonic()-begin)
        results.append(result)
        with (output / 'results.jsonl').open('a') as f:
            f.write(json.dumps(result) + '\n')
        print(f'Model {i+1}/{len(validated)} {task["source"]}:{task["id"]} {result["status"]} ({result["seconds"]:.1f}s)', flush=True)
    summary = {'completed': datetime.now().astimezone().isoformat(), 'selected_tasks': len(tasks), 'reference_validated_tasks': len(validated), 'reference_invalid_tasks': len(tasks)-len(validated), 'by_source': {s: dict(Counter(r['status'] for r in results if r['source']==s)) for s in ('apps','mbpp')}, 'syntax_valid': sum(r['syntax_valid'] for r in results), 'passed': sum(r['status']=='passed' for r in results), 'generation_token_limit': sum(r['stop_reason']=='token_limit' for r in results), 'total_original_test_cases_validated': sum(len(t['cases']) for t in validated), 'mlx_peak_gb': mx.get_peak_memory()/1e9, 'external_benchmarks_loaded': False}
    (output / 'summary.json').write_text(json.dumps(summary, indent=2))
    lines = ['# Code-Diagnose des besten Checkpoints', '', f"Abgeschlossen: {summary['completed']}", '', f"{summary['passed']} von {len(validated)} Aufgaben vollständig gelöst; {summary['syntax_valid']} syntaktisch gültige Antworten.", '', '| Quelle | Aufgaben | Gelöst | Syntaxfehler | Laufzeitfehler | Falsche Ausgabe | Timeout |', '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for s, c in summary['by_source'].items():
        lines.append(f"| {s} | {sum(c.values())} | {c.get('passed',0)} | {c.get('syntax_error',0)} | {c.get('runtime_error',0)} | {c.get('wrong_answer',0)} | {c.get('timeout',0)} |")
    lines += ['', f"Ausgewählt: {len(tasks)} Aufgaben. Davon {len(validated)} durch mindestens eine auf allen Originalfällen bestandene Referenzlösung bestätigt; {len(tasks)-len(validated)} wegen fehlgeschlagener Referenzprüfung separat ausgeschlossen. {summary['total_original_test_cases_validated']} Original-Testfälle in den bestätigten Aufgaben. Beim Modell Abbruch pro Aufgabe nach dem ersten Fehler; keine erfundene Testfall-Erfolgsquote.", '', 'Interne Entwicklungsdiagnose: Aufgaben aus den zurückgehaltenen Original-Trainingsanteilen, nicht im Modelltraining. Der Checkpoint wurde bereits anhand von Entwicklungsloss ausgewählt. APPS nur Standard-Ein-/Ausgabe-Aufgaben; 139 APPS-Funktionsaufgaben sind nicht Teil dieses Prüflaufs. MBPP verwendet wie beim Training den Aufgabentext ohne zusätzliche Tests oder Funktionssignatur; dadurch können Schnittstellenfehler auftreten. Dies ist kein offizieller APPS-/MBPP-Score und keine Messung neuer Benchmark-Familien.', '', f"Ein greedy Versuch je Aufgabe, maximal 512 neue Tokens bei insgesamt 1.024 Tokens Kontext. {summary['generation_token_limit']} Antworten erreichten das Tokenlimit. Keine Reparatur, kein Umbenennen von Funktionen, keine zusätzlichen Imports. Python 3.12 in macOS-Sandbox, ohne Netzwerk, mit Prozess-, Ausgabe- und Zeitgrenzen. APPS-Ausgaben werden nach Whitespace-Tokens mit numerischer Toleranz 1e-6 verglichen; alternative gültige Ausgaben werden nicht durch Spezialchecker geprüft.", '', 'LiveCodeBench, IFBench und BBEH bleiben geschlossen. Dateien: `protocol.json`, `reference_checks.jsonl`, `results.jsonl`, `summary.json`.']
    (output / 'REPORT.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    main()
