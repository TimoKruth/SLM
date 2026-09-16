"""Recheck frozen fresh data and pure scoring on CPU, without importing MLX."""
import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path

from fresh47.prepare import sha, write


def verify(data):
    manifest=json.loads((data/'manifest.json').read_text())
    expected={**manifest['derived_files_sha256'],'records.jsonl':manifest['records_sha256'],
              'confirmation.jsonl':manifest['confirmation_sha256'],'tokenizer.json':manifest['tokenizer']['sha256']}
    for name,digest in expected.items():assert sha(data/name)==digest,name
    path=Path(__file__).resolve().parents[1]/'slm/broad_eval.py'
    code=ast.parse(path.read_text())
    code.body=[n for n in code.body if not (isinstance(n,ast.ImportFrom) and n.module=='train')]
    namespace={'__name__':'slm.scorer_cpu_check','__package__':'slm'}
    exec(compile(code,str(path),'exec'),namespace)
    counts=Counter();refs=Counter();held={};membership={};seen=set();metrics={}
    # Original dataset IDs (notably MultiNLI) are not guaranteed unique.
    # Match the actual prepared content as well as its source metadata.
    def identity(row):return row['source'],str(row['original_id']),row.get('variant'),content(row)
    def content(row):return hashlib.sha256((row['prompt']+'\0'+row['answer']).encode()).hexdigest()
    for split in ['dev','confirmation']:
        suite=json.loads((data/f'{split}-suite.json').read_text())
        assert suite['tokenizer_sha256']==manifest['tokenizer']['sha256']
        for row in suite['general']:
            key=identity(row);assert key not in membership
            membership[key]=(split,content(row))
            metric=namespace['score_general'](row,row['answer'])
            assert metric.get('reference_parseable',True)
            if 'correct' in metric:
                assert metric['correct'],key
                refs[split]+=1
            metrics[row['source']]=dict(metric=metric['metric'],correctness_scored='correct' in metric)
            counts['suite_'+split]+=1
    for name in ['records.jsonl','confirmation.jsonl']:
        with (data/name).open() as source:
            for line in source:
                row=json.loads(line);assert row['original_split']=='train';counts[row['split']]+=1
                key=identity(row)
                if key in membership:
                    assert (row['split'],content(row))==membership[key]
                    seen.add(key)
                if row['split']!='train':
                    digest=content(row)
                    if digest in held:assert held[digest]==row['split'],'Dev/confirmation exact overlap'
                    held[digest]=row['split']
    assert seen==membership.keys(),'Suite row missing from its declared partition'
    with (data/'records.jsonl').open() as source:
        for line in source:
            row=json.loads(line)
            if row['split']=='train':assert content(row) not in held,'Training/holdout exact overlap'
    return dict(status='passed',model_initialized=False,gpu_work_started=False,record_counts=dict(counts),
                reference_self_scores_passed=dict(refs),exact_prompt_answer_overlap=0,
                all_derived_hashes_verified=len(manifest['derived_files_sha256']),
                all_holdout_original_splits='train',no_external_test_loaded=True,
                suite_sources=len(metrics),scored_sources=sum(m['correctness_scored'] for m in metrics.values()),
                metrics=metrics,script_sha256=sha(Path(__file__)))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--data',type=Path,required=True)
    args=parser.parse_args();result=verify(args.data)
    write(args.data/'INDEPENDENT_CHECKS.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='metrics'},indent=2))
