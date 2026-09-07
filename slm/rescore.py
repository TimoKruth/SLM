"""Recheck saved generations with the current sandbox scorer, without resampling."""
import ast
from collections import Counter
from datetime import datetime
import json
from pathlib import Path
from .code_eval import ROOT, load_tasks, score, sha


def main():
    output = ROOT / 'runs/code-eval-2026-09-07'
    tasks, _ = load_tasks()
    by_id = {(t['source'], t['id']):t for t in tasks}
    original = [json.loads(line) for line in (output/'results.jsonl').open()]
    checked = []
    for row in original:
        result = score(row['generated'], by_id[(row['source'],row['id'])])
        checked.append(dict(source=row['source'], id=row['id'], **result))
    changes = [dict(source=a['source'],id=a['id'],before=a['status'],after=b['status']) for a,b in zip(original,checked) if a['status']!=b['status']]
    nonempty = sum(bool(ast.parse(a['generated']).body) for a in original if a['syntax_valid'])
    verification = dict(time=datetime.now().astimezone().isoformat(), scorer_sha256=sha(ROOT/'slm/code_eval.py'), rescorer_sha256=sha(__file__), saved_generations_sha256=sha(output/'results.jsonl'), tasks_rechecked=len(checked), changes=changes, parses_with_at_least_one_statement=nonempty, details=checked, assertion_completion_marker=True)
    (output/'rescore.json').write_text(json.dumps(verification,indent=2))
    (output/'evaluator.py').write_text((ROOT/'slm/code_eval.py').read_text())
    assert not changes, changes
    with (output/'REPORT.md').open('a') as f:
        f.write(f'\nAlle {len(checked)} gespeicherten Antworten wurden nochmals ausgeführt; die Fehlerklassen blieben unverändert. MBPP bestätigt die tatsächlich erreichte Assertion durch eine zufällige Abschlussmarkierung, damit ein vorzeitiges `sys.exit(0)` nicht als Erfolg zählt. {nonempty} der syntaktisch parsebaren Antworten enthalten mindestens eine Python-Anweisung; bloße Kommentare zählen bei Parsebarkeit mit, lösen aber keine Aufgabe. Details in `rescore.json`.\n')
    print(json.dumps({k:v for k,v in verification.items() if k!='details'},indent=2))


if __name__ == '__main__':
    main()
