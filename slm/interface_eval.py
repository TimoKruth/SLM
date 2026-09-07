"""Supplement: MBPP with one public example; score only the other original cases."""
import argparse
from datetime import datetime
from collections import Counter
import json
import mlx.core as mx
from tokenizers import Tokenizer
from .code_eval import ROOT, load_tasks, generate, score, sha
from .model import LanguageModel, ModelConfig


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--run',default='runs/night-2026-09-06')
    parser.add_argument('--output',default='runs/code-eval-2026-09-07')
    args=parser.parse_args()
    output=(ROOT/args.output).resolve()
    run=(ROOT/args.run).resolve()
    path = output/'mbpp_public_example.json'
    assert not path.exists()
    tasks = [t for t in load_tasks()[0] if t['source']=='mbpp']
    mx.set_memory_limit(8*1024**3); mx.set_cache_limit(512*1024**2)
    model = LanguageModel(ModelConfig(**json.loads((run/'config.json').read_text())['model']))
    model.load_weights(str(run/'best.safetensors')); model.eval(); mx.eval(model.parameters())
    tok = Tokenizer.from_file(str(run/'tokenizer.json'))
    results=[]
    for task in tasks:
        example = task['cases'][0]['assertion']
        prompt = task['prompt'] + '\n\nYour function must satisfy this example:\n' + example
        remaining = dict(task, cases=task['cases'][1:])
        assert remaining['cases']
        assert any(score(ref,remaining)['status']=='passed' for ref in task['references'])
        result = dict(source='mbpp',id=task['id'],prompt=prompt,public_example=example,**generate(model,tok,prompt))
        result.update(score(result['generated'],remaining));results.append(result)
        print(task['id'],result['status'],flush=True)
    summary=dict(completed=datetime.now().astimezone().isoformat(),protocol='Same best checkpoint, one greedy response per MBPP dev task; first original assertion visible in prompt, only remaining assertions scored; separate diagnostic, not comparable to original prompt score or official MBPP.',scorer_sha256=sha(ROOT/'slm/code_eval.py'),script_sha256=sha(__file__),checkpoint_sha256=sha(run/'best.safetensors'),counts=dict(Counter(r['status'] for r in results)),tasks=len(results),results=results)
    path.write_text(json.dumps(summary,indent=2))
    with (output/'REPORT.md').open('a') as f:
        f.write(f"\nZusatzdiagnose MBPP mit einem sichtbaren Originalbeispiel pro Aufgabe (einschließlich erwarteten Funktionsnamens): {summary['counts'].get('passed',0)}/{len(results)} Aufgaben bestanden die jeweils zwei übrigen, nicht gezeigten Assertions. Ein eigener greedy Versuch, gleicher Checkpoint und Tokenrahmen, keine Referenzlösung im Prompt. Separat vom Hauptwert ausweisen; die Zusatzdiagnose untersucht die fehlende Schnittstellenangabe. Details in `mbpp_public_example.json`.\n")
    print(json.dumps({k:v for k,v in summary.items() if k!='results'},indent=2))


if __name__=='__main__':main()
