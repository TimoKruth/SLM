"""Broad internal development evaluation; frozen final benchmarks remain unopened."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime
import json
from pathlib import Path
import re
import string
import time

from .breadth import SOURCE_FAMILY
from .train import atomic_json

NARRATIVE = {'hellaswag', 'piqa'}
CODE = {'apps', 'mbpp', 'code_contests'}
QA = {'squad', 'quoref', 'ropes', 'drop', 'hotpotqa'}


def normalize(text):
    """Normalize case, punctuation and spacing for QA exact/F1 diagnostics."""
    return ' '.join(re.sub(r'\b(a|an|the)\b', ' ', text.lower().translate(str.maketrans('', '', string.punctuation))).split())


def final_answer(text, source):
    """Extract explicit final answers; never substitute a reference or repair reasoning."""
    if source == 'gsm8k':
        text = text.rsplit('####', 1)[-1].strip()
        if not re.fullmatch(r'[-+]?\d[\d,]*(?:\.\d+)?', text):
            return None
        return text.replace(',', '')
    if source == 'math':
        marker = '\\boxed{'
        if marker not in text:
            return None
        rest = text.rsplit(marker, 1)[-1]
        depth = 1
        for i, char in enumerate(rest):
            depth += (char == '{') - (char == '}')
            if depth == 0:
                return re.sub(r'\s+', '', rest[:i])
        return None
    if source in {'aqua_rat', 'qasc'}:
        if 'Answer:' not in text:
            return None
        return text.rsplit('Answer:', 1)[-1].strip().casefold()
    return ' '.join(text.strip().casefold().split())


def score_general(row, generated, memorization=False):
    """Keep recall, executable correctness, narrative quality and answer proxies distinct."""
    source = row['source']
    if memorization:
        return {'metric': 'training_answer_recall', 'correct': generated.strip() == row['answer'].strip()}
    if source in CODE:
        import ast
        try:
            ast.parse(generated)
            syntax = bool(generated.strip())
        except (SyntaxError, ValueError):
            syntax = False
        return {'metric': 'syntax_only_not_functional', 'syntax_valid': syntax}
    if source in NARRATIVE:
        words = generated.split()
        return {'metric': 'unscored_open_generation', 'nonempty': bool(words),
                'unique_word_fraction': len(set(words))/max(1,len(words))}
    if source in {'spider', 'wikisql'}:
        return {'metric': 'sql_text_match_not_execution', 'text_match': generated.strip().rstrip(';').casefold() == row['answer'].strip().rstrip(';').casefold()}
    if source in QA:
        expected = row.get('answers', [row['answer']])
        actual = normalize(generated)
        f1s = []
        for answer in expected:
            a, b = Counter(actual.split()), Counter(normalize(answer).split())
            overlap = sum((a & b).values())
            f1s.append(2*overlap/max(1,sum(a.values())+sum(b.values())))
        return {'metric': 'answer_exact_and_token_f1', 'correct': any(actual == normalize(a) for a in expected), 'token_f1': max(f1s)}
    if row.get('choices') and re.fullmatch(r'[A-Z][.)]?', generated.strip()):
        index = ord(generated.strip()[0])-65
        if 0 <= index < len(row['choices']):
            generated = row['choices'][index]
    actual, expected = final_answer(generated, source), final_answer(row['answer'], source)
    return {'metric': 'final_answer_match' if source in {'gsm8k','math','aqua_rat','qasc'} else 'answer_match',
            'correct': actual is not None and expected is not None and actual == expected,
            'reference_parseable': expected is not None}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--run', required=True)
    p.add_argument('--suite', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--partition', choices=['dev', 'memorization'], default='dev')
    p.add_argument('--checkpoint', choices=['best','latest'], default='best')
    p.add_argument('--maximum', type=int, default=192)
    p.add_argument('--max-seconds', type=float, default=900)
    p.add_argument('--skip-code', action='store_true')
    args = p.parse_args()
    run, out = Path(args.run), Path(args.output)
    if out.exists():
        raise ValueError('Use a new evaluation directory')
    out.mkdir(parents=True)
    suite = json.loads(Path(args.suite).read_text())
    config = json.loads((run/'config.json').read_text())
    import mlx.core as mx
    from tokenizers import Tokenizer
    from .model import LanguageModel, ModelConfig
    from .inference import greedy_generate
    from .code_eval import score, sha
    mx.set_default_device(mx.gpu)
    mx.set_memory_limit(12*1024**3)
    mx.set_cache_limit(512*1024**2)
    model = LanguageModel(ModelConfig(**config['model']))
    path = run/'best.safetensors'
    if args.checkpoint == 'latest':
        path = run/json.loads((run/'latest.json').read_text())['checkpoint']/'model.safetensors'
    model.load_weights(str(path))
    model.eval()
    tokenizer = Tokenizer.from_file(str(run/'tokenizer.json'))
    if sha(run/'tokenizer.json') != suite['tokenizer_sha256']:
        raise ValueError('Suite tokenizer mismatch')
    cutoff = time.time() + args.max_seconds
    results, code_results, excluded = [], [], Counter()
    rows = suite['memorization' if args.partition=='memorization' else 'general']
    atomic_json(out/'protocol.json', dict(suite_sha256=sha(args.suite), checkpoint_sha256=sha(path),
                partition=args.partition, selected=len(rows), external_tests_loaded=False,
                monitoring='Provided by project launcher; not included in quality score', protocol=suite['protocol']))
    with (out/'results.jsonl').open('w', buffering=1) as f:
        for row in rows:
            if time.time() >= cutoff:
                break
            response = greedy_generate(model, tokenizer, row['prompt'], args.maximum, deadline=cutoff)
            metric = score_general(row, response['generated'], args.partition=='memorization')
            result = dict(source=row['source'], id=row['original_id'], family=SOURCE_FAMILY[row['source']],
                          expected=row['answer'], **response, **metric)
            results.append(result)
            f.write(json.dumps(result, ensure_ascii=False)+'\n')
    if args.partition == 'dev' and not args.skip_code:
        with (out/'code.jsonl').open('w', buffering=1) as f:
            for task in suite['code']:
                if time.time() >= cutoff:
                    break
                if not any(score(ref, task)['status']=='passed' for ref in task['references']):
                    excluded['reference_failed'] += 1
                    continue
                response = greedy_generate(model, tokenizer, task['prompt'], 512, deadline=cutoff)
                result = dict(source=task['source'], id=task['id'], coverage=task['coverage'],
                              **response, **score(response['generated'], task))
                result['stronger_test_pass'] = result['status']=='passed' and task['coverage']!='single_original_case_only'
                code_results.append(result)
                f.write(json.dumps(result, ensure_ascii=False)+'\n')
    by_source = {}
    for source in sorted({r['source'] for r in results}):
        subset = [r for r in results if r['source']==source]
        scored = [r for r in subset if 'correct' in r and r.get('reference_parseable', True)]
        by_source[source] = dict(family=SOURCE_FAMILY[source], generated=len(subset), scored=len(scored),
                                 correct=sum(r['correct'] for r in scored), metric=subset[0]['metric'],
                                 context_exceeded=sum(r['stop_reason']=='context_exceeded' for r in subset))
    family_scores = defaultdict(list)
    for source, data in by_source.items():
        if data['scored']:
            family_scores[data['family']].append(data['correct']/data['scored'])
    by_family = {family:sum(values)/len(values) for family,values in family_scores.items()}
    summary = dict(completed=datetime.now().astimezone().isoformat(), partition=args.partition,
                   selected_general=len(rows), evaluated_general=len(results), by_source=by_source,
                   mean_source_accuracy_by_family=by_family, code_evaluated=len(code_results),
                   code_statuses=dict(Counter(r['status'] for r in code_results)),
                   code_passes_with_stronger_tests=sum(r['stronger_test_pass'] for r in code_results),
                   code_exclusions=dict(excluded), deadline_reached=time.time()>=cutoff,
                   interpretation='Internal development proxies, not comparable across metric types or official benchmarks. Narrative and SQL functional quality remain unscored. No family-transfer claim.')
    atomic_json(out/'summary.json', summary)
    lines = ['# Broad development evaluation', '', summary['interpretation'], '', '| Source | Metric | Correct / scored |', '| --- | --- | --- |']
    lines += [f"| {source} | {row['metric']} | {row['correct']} / {row['scored']} |" for source,row in by_source.items()]
    lines += ['', 'Code outcomes: '+json.dumps(summary['code_statuses']), 'Passes with stronger test coverage: '+str(summary['code_passes_with_stronger_tests'])]
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    main()
