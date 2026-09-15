"""CPU-only final report for the bounded nine-checkpoint diagnostic evaluation."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime
import json
import math
from pathlib import Path
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from experiments.analyze_parameters import bootstrap, diagnostics, digest, macro, scored, scorer
from experiments.run_expanded_diagnostic import read, write, validate_summary


def paired(a, b, tasks):
    groups = defaultdict(lambda: defaultdict(list))
    deltas = []
    transitions = Counter()
    for order in range(2):
        if a[order].keys() != b[order].keys() or a[order].keys() != tasks.keys():
            raise ValueError('Unpaired task coverage')
        deltas.append(macro(b[order])-macro(a[order]))
    for key, row in a[0].items():
        if not scored(row):
            continue
        values = []
        for order in range(2):
            left, right = a[order][key], b[order][key]
            assert scored(left) and scored(right)
            delta = int(right['correct'])-int(left['correct'])
            values.append(delta)
            transitions['gain' if delta>0 else 'loss' if delta<0 else 'unchanged'] += 1
        groups[row['family'],row['source']][tasks[key]['group']].append(values)
    uncertainty = bootstrap({k:[np.asarray(v,dtype=float) for v in g.values()] for k,g in groups.items()})
    assert math.isclose(statistics.mean(deltas),statistics.mean(v['delta'] for v in uncertainty['families'].values()),abs_tol=1e-12)
    return dict(per_order=deltas,mean=statistics.mean(deltas),transitions=dict(transitions),uncertainty=uncertainty)


def report(run, output):
    if output.exists():
        raise ValueError('Report output already exists')
    plan=read(run/'plan.json'); status=read(run/'status.json')
    assert status['status']=='completed' and status['completed_evaluations']==9 and status['frozen_inputs_unchanged']
    hashes={}
    def checked(path):
        hashes[str(path)]=digest(path); return read(path)
    checked(run/'plan.json');checked(run/'status.json')
    suite=checked(run/'diagnostic-suite.json')
    tasks={(r['source'],str(r['original_id'])):r for r in suite['general']}
    assert len(tasks)==len({r['group'] for r in tasks.values()})==1360
    frozen=Path('/Users/timokruth/Projekte/SLM-expanded-diagnostic/slm/broad_eval.py')
    hashes[str(frozen)]=digest(frozen); scoring=scorer(frozen)
    data={}; endpoints=[]
    for job in plan['jobs']:
        target=run/'evaluations'/job['id']; summary=checked(target/'summary.json');validate_summary(summary,1360)
        protocol=checked(target/'protocol.json')
        assert protocol['checkpoint_sha256']==job['checkpoint_sha256']
        assert protocol['suite_sha256']==digest(run/'diagnostic-suite.json')
        path=target/'results.jsonl';hashes[str(path)]=digest(path)
        rr=[json.loads(line) for line in path.read_text().splitlines()]
        rows={(r['source'],str(r['id'])):r for r in rr}
        assert len(rr)==len(rows)==1360 and rows.keys()==tasks.keys()
        counts=defaultdict(Counter);total=Counter();by_family=defaultdict(Counter)
        for key,row in rows.items():
            assert row['expected']==tasks[key]['answer']
            rescore=scoring['score_general'](tasks[key],row['generated'])
            for k,v in rescore.items():assert row[k]==v
            flags=diagnostics(row,scoring['final_answer'])
            c=Counter(evaluated=1,scored=int(scored(row)),correct=int(scored(row) and row['correct']))
            c.update({k:int(v) for k,v in flags.items()})
            c['incorrect_without_surface_flags']=int(scored(row) and not row['correct'] and not any(flags.values()))
            counts[row['source']].update(c);by_family[row['family']].update(c);total.update(c)
        for source,c in counts.items():
            expected=summary['by_source'][source]
            assert [c[k] for k in ['evaluated','scored','correct']]==[expected[k] for k in ['generated','scored','correct']]
        assert math.isclose(macro(rows),statistics.mean(summary['mean_source_accuracy_by_family'].values()),abs_tol=1e-12)
        data[job['condition'],job['order'],job['endpoint']]=rows
        endpoints.append(dict(id=job['id'],condition=job['condition'],order=job['order'],endpoint=job['endpoint'],
                              additional_tokens=job['additional_tokens'],accuracy=macro(rows),
                              answer_loss=summary['answer_loss']['macro_source_answer_loss'],
                              family_accuracy=summary['mean_source_accuracy_by_family'],sources=dict(counts),
                              family_diagnostics=dict(by_family),counts=dict(total)))
    comparisons={}
    parent=[data['parent',None,'parent']]*2
    for endpoint in ['50M','final']:
        a=[data['A',o,endpoint] for o in range(2)];d=[data['D',o,endpoint] for o in range(2)]
        comparisons['D-A-'+endpoint]=paired(a,d,tasks)
        comparisons['A-parent-'+endpoint]=paired(parent,a,tasks)
        comparisons['D-parent-'+endpoint]=paired(parent,d,tasks)
    for condition in 'AD':
        comparisons[condition+'-final-minus-50M']=paired([data[condition,o,'50M'] for o in range(2)],
                                                      [data[condition,o,'final'] for o in range(2)],tasks)
    for path,h in hashes.items():assert digest(Path(path))==h
    output.mkdir()
    result=dict(completed=datetime.now().astimezone().isoformat(),endpoints=endpoints,comparisons=comparisons,
                validated_evaluations=9,validated_generations=9*1360,automatic_adoption=False,
                interpretation='Already-opened diagnostic groups, exploratory evidence. Fixed parent and two data orders; not fresh confirmation, independent initializations or external transfer. Surface flags overlap; no causal attribution from flags alone.')
    write(output/'analysis.json',result)
    write(output/'provenance.json',dict(inputs=hashes,script_sha256=digest(Path(__file__)),
                                      helper_sha256=digest(Path(__file__).with_name('analyze_parameters.py'))))
    lines=['# Expanded checkpoint diagnostic results','',result['interpretation'],'',
           '| Checkpoint | Additional tokens | Accuracy (family macro) | Correct / scored | Answer loss |',
           '|---|---:|---:|---:|---:|']
    for row in endpoints:
        lines.append(f"| {row['id']} | {row['additional_tokens'] if row['additional_tokens'] is not None else 'parent'} | {100*row['accuracy']:.2f}% | {row['counts']['correct']} / {row['counts']['scored']} | {row['answer_loss']:.4f} |")
    lines += ['', '| Paired comparison | Order 0 (pp) | Order 1 (pp) | Mean (pp) | Exploratory 95% interval (pp) |',
              '|---|---:|---:|---:|---:|']
    for name,row in comparisons.items():
        lo,hi=row['uncertainty']['fixed_source_interval95']
        lines.append(f"| {name} | {100*row['per_order'][0]:+.2f} | {100*row['per_order'][1]:+.2f} | {100*row['mean']:+.2f} | {100*lo:+.2f} to {100*hi:+.2f} |")
    lines += ['','All nine evaluations and 12,240 saved generations validated with the frozen scorer. The 50M snapshots are nearest-update snapshots; final checkpoints contain unequal additional tokens.','',
              'Intervals use 5,000 paired group resamples within source, keeping both data orders paired and preserving source/family macro weights. Parent comparisons reuse the same parent responses across orders. No new acceptance threshold or automatic model adoption.','',
              'Per-source/family diagnostics, gains/losses, and source-composition sensitivity intervals are in analysis.json. This diagnostic does not repair the missing fresh-confirmation coverage.']
    (output/'REPORT.md').write_text('\n'.join(lines)+'\n')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);p.add_argument('--wait',action='store_true');a=p.parse_args()
    run=a.run.resolve();output=run/'analysis';statefile=run/'analysis-status.json'
    try:
        deadline=read(run/'plan.json')['deadline_unix']
        while True:
            status=read(run/'status.json')
            if status['status']=='completed':break
            if status['status'] in ['paused','failed','stopped']:
                raise RuntimeError('Evaluation did not complete; no complete comparison reported')
            if not a.wait or time.time()>=deadline:
                raise RuntimeError('Evaluation is not complete before report deadline')
            write(statefile,dict(status='waiting_for_evaluations',updated=datetime.now().astimezone().isoformat()))
            time.sleep(5)
        write(statefile,dict(status='analyzing',updated=datetime.now().astimezone().isoformat()))
        result=report(run,output)
        write(statefile,dict(status='completed',validated_evaluations=result['validated_evaluations'],
                             report=str(output/'REPORT.md'),finished=datetime.now().astimezone().isoformat()))
    except BaseException as exc:
        write(statefile,dict(status='failed',error=str(exc),finished=datetime.now().astimezone().isoformat()));raise


if __name__=='__main__':main()
