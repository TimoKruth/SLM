"""CPU-only final report for the bounded five-checkpoint 75M confirmation."""
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
from experiments.run_parameter_confirmation import read, write, validate_summary, validate_plan


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


def assess(comparisons, gates):
    baseline = comparisons['D-A-75M']; parent = comparisons['D-parent-75M']
    result = dict(
        gain_vs_A_in_both_orders=all(v >= gates['minimum_gain_vs_A_per_order']-1e-12 for v in baseline['per_order']),
        beats_parent_in_both_orders=all(v > 0 for v in parent['per_order']),
        family_regressions_within_limit=all(v['delta'] >= -gates['maximum_mean_family_regression_vs_each_reference']-1e-12
                                           for c in (baseline, parent) for v in c['uncertainty']['families'].values()))
    result['all_quality_gates_passed'] = all(result.values())
    result['decision'] = 'Supports further validation; no automatic adoption' if result['all_quality_gates_passed'] else 'No supported replacement; retain parent as reference'
    return result


def report(run, output):
    if output.exists():
        raise ValueError('Report output already exists')
    plan=read(run/'plan.json'); status=read(run/'evaluation-completion.json')
    validate_plan(plan)
    assert status['status']=='evaluations_completed' and status['completed_evaluations']==5 and status['frozen_inputs_unchanged']
    hashes={}
    def checked(path):
        hashes[str(path)]=digest(path); return read(path)
    checked(run/'plan.json');checked(run/'evaluation-completion.json')
    suite=checked(run/'confirmation-suite.json')
    tasks={(r['source'],str(r['original_id'])):r for r in suite['general']}
    assert len(tasks)==len({r['group'] for r in tasks.values()})==1360
    frozen=Path(__file__).resolve().parents[1]/'slm/broad_eval.py'
    hashes[str(frozen)]=digest(frozen); scoring=scorer(frozen)
    data={}; endpoints=[]
    for job in plan['jobs']:
        target=run/'evaluations'/job['id']; summary=checked(target/'summary.json');validate_summary(summary,1360)
        protocol=checked(target/'protocol.json')
        assert protocol['checkpoint_sha256']==job['checkpoint_sha256']
        assert protocol['suite_sha256']==digest(run/'confirmation-suite.json')
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
    for endpoint in ['75M']:
        a=[data['A',o,endpoint] for o in range(2)];d=[data['D',o,endpoint] for o in range(2)]
        comparisons['D-A-'+endpoint]=paired(a,d,tasks)
        comparisons['A-parent-'+endpoint]=paired(parent,a,tasks)
        comparisons['D-parent-'+endpoint]=paired(parent,d,tasks)
    gates = assess(comparisons, plan['gates'])
    for path,h in hashes.items():assert digest(Path(path))==h
    output.mkdir()
    result=dict(completed=datetime.now().astimezone().isoformat(),endpoints=endpoints,comparisons=comparisons,
                validated_evaluations=5,validated_generations=5*1360,gates=gates,automatic_adoption=False,
                interpretation='Fixed 75M comparison on previously unconsumed suite groups: 256 original-validation tasks and 1104 internal-dev tasks. Internal dev may have been exposed via development loss. Fixed parent and two data orders, not independent initializations or external transfer. Intervals remain exploratory; surface flags overlap.')
    write(output/'analysis.json',result)
    write(output/'provenance.json',dict(inputs=hashes,script_sha256=digest(Path(__file__)),
                                      helper_sha256=digest(Path(__file__).with_name('analyze_parameters.py'))))
    lines=['# Matched 75M parameter confirmation results','',result['interpretation'],'',
           '| Checkpoint | Additional tokens | Accuracy (family macro) | Correct / scored | Answer loss |',
           '|---|---:|---:|---:|---:|']
    for row in endpoints:
        lines.append(f"| {row['id']} | {row['additional_tokens'] if row['additional_tokens'] is not None else 'parent'} | {100*row['accuracy']:.2f}% | {row['counts']['correct']} / {row['counts']['scored']} | {row['answer_loss']:.4f} |")
    lines += ['', '| Paired comparison | Order 0 (pp) | Order 1 (pp) | Mean (pp) | Exploratory 95% interval (pp) |',
              '|---|---:|---:|---:|---:|']
    for name,row in comparisons.items():
        lo,hi=row['uncertainty']['fixed_source_interval95']
        lines.append(f"| {name} | {100*row['per_order'][0]:+.2f} | {100*row['per_order'][1]:+.2f} | {100*row['mean']:+.2f} | {100*lo:+.2f} to {100*hi:+.2f} |")
    lines += ['','All five evaluations and 6,800 saved generations validated with the frozen scorer. The 75M snapshots match tokens and updates exactly within each data order. No training or checkpoint selection after viewing these scores.','',
              'Intervals use 5,000 paired group resamples within source, keeping both data orders paired and preserving source/family macro weights. Parent comparisons reuse the same parent responses across orders. The predeclared decision gates below are applied without automatic model adoption.','',
              'Per-source/family diagnostics, gains/losses, and source-composition sensitivity intervals are in analysis.json. All 25 source quotas are complete; five sources remain outside correctness scoring.']
    lines += ['', '## Predeclared decision gates', '', *[f'- {name}: {value}' for name,value in gates.items()]]
    (output/'REPORT.md').write_text('\n'.join(lines)+'\n')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);p.add_argument('--wait',action='store_true');a=p.parse_args()
    run=a.run.resolve();output=run/'analysis';statefile=run/'analysis-status.json'
    try:
        deadline=read(run/'plan.json')['deadline_unix']
        while True:
            status=read(run/'status.json')
            if status['status']=='evaluations_completed':break
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
