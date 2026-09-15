"""Analyze saved conservative study outputs on CPU; never imports a training backend."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import statistics as stats


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def scored(row):return 'correct' in row and row.get('reference_parseable',True)


def accuracy(rows):
    sources=defaultdict(list);families=defaultdict(list)
    for r in rows.values():
        if scored(r):sources[(r['family'],r['source'])].append(float(r['correct']))
    for (family,source),values in sources.items():families[family].append(stats.mean(values))
    by={f:stats.mean(v) for f,v in families.items()}
    return stats.mean(by.values()),by


def compare(a,b):
    assert a.keys()==b.keys()
    flips=Counter();sources=defaultdict(Counter);changes=[]
    for k,x in a.items():
        y=b[k]
        assert (x['expected'],x['metric'],x['family'])==(y['expected'],y['metric'],y['family'])
        assert scored(x)==scored(y)
        different=x['generated']!=y['generated']
        tag=('gain' if y['correct'] else 'loss') if scored(x) and x['correct']!=y['correct'] else None
        flips['evaluated']+=1;flips['generated_changed']+=different
        if scored(x):
            flips['scored']+=1;sources[x['source']]['scored']+=1
            flips['baseline_correct']+=x['correct'];flips['candidate_correct']+=y['correct']
            if tag:flips[tag]+=1;sources[x['source']][tag]+=1
        if different or tag:
            changes.append(dict(source=k[0],id=k[1],family=x['family'],transition=tag,
                expected=x['expected'],baseline=x['generated'],candidate=y['generated']))
    aa,af=accuracy(a);bb,bf=accuracy(b)
    return dict(counts=dict(flips),macro_accuracy_delta=bb-aa,
                family_deltas={f:bf[f]-af[f] for f in af},sources={k:dict(v) for k,v in sources.items()}),changes


def analyze(run,output):
    run=run.resolve();output=output.resolve()
    assert not output.is_relative_to(run),'Keep historical study unchanged'
    hashes={}
    def read(p):
        hashes[str(p)]=digest(p);return json.loads(p.read_text())
    def rows(p):
        hashes[str(p)]=digest(p)
        data=[json.loads(x) for x in p.read_text().splitlines()]
        result={(r['source'],str(r['id'])):r for r in data}
        assert len(data)==len(result),'Duplicate tasks'
        return result
    status=read(run/'status.json');assert status['status']=='completed'
    original=read(run/'quality-summary.json');plan=read(run/'plan.json')
    read(run/'RUN_CONDITIONS.json')
    data={};summaries={};trials={};conditions={};details=[];suites={}
    for name in ('search','confirmation'):suites[name]=read(run/f'{name}-suite.json')
    for suite in ('search','confirmation'):
        key=('parent',0,'parent',suite)
        folder=run/'evaluations'/f'parent-{suite}'
        data[key]=rows(folder/'results.jsonl');summaries[key]=read(folder/'summary.json')
    for role in ('baseline','deferred4'):
        for order in range(3):
            folder=run/'trials'/f'r{order}-{role}'
            trials[role,order]=read(folder/'result.json')
            conditions[role,order]=read(folder/'RUN_CONDITIONS.json')
            read(folder/'RESOURCE_INTERVAL.json')
            for exposure in ('matched','wall'):
                for suite in ('search','confirmation'):
                    key=(role,order,exposure,suite)
                    folder=run/'evaluations'/f'r{order}-{role}-{exposure}-{suite}'
                    data[key]=rows(folder/'results.jsonl');summaries[key]=read(folder/'summary.json')
    for key,summary in summaries.items():
        assert summary['evaluated_general']==len(data[key])==summary['selected_general']
        assert not summary['deadline_reached']
        assert summary['answer_loss']['examples']==len(data[key])
        for source,reported in summary['by_source'].items():
            rr=[r for r in data[key].values() if r['source']==source]
            ss=[r for r in rr if scored(r)]
            assert reported['generated']==len(rr) and reported['scored']==len(ss)
            assert reported['correct']==sum(r['correct'] for r in ss)
        _,family=accuracy(data[key])
        for f,value in family.items():assert math.isclose(value,summary['mean_source_accuracy_by_family'][f],abs_tol=1e-12)
    out=dict(run=str(run),computed_at=datetime.now(timezone.utc).isoformat(),endpoints={},trajectories=[],timing=[],coverage={})
    for exposure in ('matched','wall'):
        for suite in ('search','confirmation'):
            name=exposure+'-'+suite;per_order=[];source_total=defaultdict(Counter);task_transitions=defaultdict(list)
            for order in range(3):
                a=data['baseline',order,exposure,suite];b=data['deferred4',order,exposure,suite]
                comparison,changed=compare(a,b);comparison['order']=order
                per_order.append(comparison)
                for item in changed:
                    details.append(dict(endpoint=name,order=order,**item))
                    if item['transition']:task_transitions[item['source'],item['id']].append((order,item['transition']))
                for source,counts in comparison['sources'].items():source_total[source].update(counts)
            mean=stats.mean(x['macro_accuracy_delta'] for x in per_order)
            assert math.isclose(mean,original['endpoints'][name]['macro_family_accuracy_delta'],abs_tol=1e-12)
            for comparison,reported in zip(per_order,original['endpoints'][name]['per_order']):
                assert math.isclose(comparison['macro_accuracy_delta'],reported['accuracy_delta'],abs_tol=1e-12)
            same_scored=[r for r in data['baseline',0,exposure,suite].values() if scored(r)]
            by_family=Counter(r['family'] for r in same_scored)
            for source,c in source_total.items():
                family=next(r['family'] for r in same_scored if r['source']==source)
                c['net']=c['gain']-c['loss'];c['family']=family
                c['delta_pp']=100*c['net']/c['scored']
                # Equal task counts within source; equal sources within family; equal families.
                c['overall_contribution_pp']=100*c['net']/(3*by_family[family]*len(by_family))
            assert math.isclose(sum(c['overall_contribution_pp'] for c in source_total.values()),100*mean,abs_tol=1e-12)
            totals=Counter()
            for v in per_order:totals.update(v['counts'])
            repeat_counts=Counter();repeat_details=[]
            for (source,taskid),transitions in task_transitions.items():
                counts=Counter(t for _,t in transitions)
                for tag in ('gain','loss'):
                    if counts[tag]:repeat_counts[f'{tag}_in_{counts[tag]}_orders']+=1
                if counts['loss']>=2 or counts['gain']>=2:
                    repeat_details.append(dict(source=source,id=taskid,transitions=transitions))
            out['endpoints'][name]=dict(counts=dict(totals),per_order=per_order,sources=dict(source_total),
                repeated_task_transitions=dict(repeat_counts),repeat_details=repeat_details,
                original=original['endpoints'][name])
    for suite in ('search','confirmation'):
        sample=data['baseline',0,'matched',suite]
        out['coverage'][suite]=dict(total=len(sample),scored=sum(scored(r) for r in sample.values()),
            unscored_sources=sorted({r['source'] for r in sample.values() if not scored(r)}),
            scored_by_family=dict(Counter(r['family'] for r in sample.values() if scored(r))))
        for order in range(3):
            row=dict(suite=suite,order=order,parent_accuracy=accuracy(data['parent',0,'parent',suite])[0])
            for role in ('baseline','deferred4'):
                matched=data[role,order,'matched',suite];wall=data[role,order,'wall',suite]
                comparison,_=compare(matched,wall)
                row[role]=dict(matched_accuracy=accuracy(matched)[0],wall_accuracy=accuracy(wall)[0],
                    matched_to_wall=comparison,
                    loss_change_relative=summaries[role,order,'wall',suite]['answer_loss']['macro_source_answer_loss']/summaries[role,order,'matched',suite]['answer_loss']['macro_source_answer_loss']-1)
            out['trajectories'].append(row)
    for order in range(3):
        a,b=[trials[role,order] for role in ('baseline','deferred4')]
        assert a['train_allowance_seconds']==b['train_allowance_seconds']==2100
        for key in ('additional_steps','additional_tokens','exposure_sha256'):
            assert a['matched'][key]==b['matched'][key]
        assert a['matched']['additional_steps']==plan['matched_steps']==8192
        out['timing'].append(dict(order=order,baseline_steps=a['additional_steps'],candidate_steps=b['additional_steps'],
            extra_steps=b['additional_steps']-a['additional_steps'],extra_tokens=b['additional_tokens']-a['additional_tokens'],
            wall_token_speedup=b['useful_tokens_per_budget_second']/a['useful_tokens_per_budget_second'],
            matched_time_speedup=a['matched']['elapsed_seconds']/b['matched']['elapsed_seconds'],
            matched_seconds_saved=a['matched']['elapsed_seconds']-b['matched']['elapsed_seconds'],
            resource_comparison=original['pairs'][order]))
    out['generation_diagnostics']={}
    for exposure in ('matched','wall'):
        for suite in ('search','confirmation'):
            for role in ('baseline','deferred4'):
                rr=[r for order in range(3) for r in data[role,order,exposure,suite].values()]
                f1=[r['token_f1'] for r in rr if 'token_f1' in r]
                out['generation_diagnostics'][f'{role}-{exposure}-{suite}']=dict(
                    stop_reasons=dict(Counter(r['stop_reason'] for r in rr)),
                    mean_generated_tokens=stats.mean(r['generated_tokens'] for r in rr),
                    qa_token_f1=stats.mean(f1) if f1 else None,
                    unparseable_references=sum(r.get('reference_parseable') is False for r in rr))
    out['conditions']=dict(all_ac=all('AC Power' in c['power_source'] for c in conditions.values()),
        settings_constant=len({c['power_settings'] for c in conditions.values()})==1,
        minimum_available_gib=min(c['memory_available_bytes'] for c in conditions.values())/1024**3,
        interpretation='Swap counters are system-wide; small nonzero swap-ins do not establish training-induced memory pressure or explain the speed difference.')
    # Hash after reading too, detecting changes during this analysis.
    for path,h in hashes.items():assert digest(Path(path))==h
    output.mkdir(parents=True,exist_ok=False)
    (output/'analysis.json').write_text(json.dumps(out,indent=2)+'\n')
    cases=[]
    for case in out['endpoints']['wall-confirmation']['repeat_details']:
        if sum(tag=='loss' for _,tag in case['transitions'])!=3:continue
        key=(case['source'],case['id'])
        task=next(t for t in suites['confirmation']['general'] if (t['source'],str(t['original_id']))==key)
        observations=[]
        for order in range(3):
            for role in ('baseline','deferred4'):
                for exposure in ('matched','wall'):
                    observations.append(dict(order=order,role=role,exposure=exposure,
                        result=data[role,order,exposure,'confirmation'][key]))
        cases.append(dict(task=task,observations=observations))
    (output/'repeated_case_review.json').write_text(json.dumps(cases,indent=2)+'\n')
    (output/'task_changes.json').write_text(json.dumps(details,indent=2)+'\n')
    (output/'provenance.json').write_text(json.dumps(dict(inputs=hashes,script_sha256=digest(Path(__file__)),
        checks='All 26 evaluation summaries reconstructed; all four reported endpoint and per-order deltas reproduced; source contributions sum exactly; paired exposure hashes equal; inputs unchanged during analysis.'),indent=2)+'\n')
    print(json.dumps(dict(output=str(output),hashed_inputs=len(hashes),evaluations_checked=len(summaries),endpoints={k:v['counts'] for k,v in out['endpoints'].items()}),indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();analyze(a.run,a.output)
