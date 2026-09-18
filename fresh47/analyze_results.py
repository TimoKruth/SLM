"""Produce aggregate-only evidence after both final fresh47 evaluations complete."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import statistics

from fresh47.prepare import sha


def read(path):
    return json.loads(path.read_text())


def analyze(run):
    state=read(run/'status.json');result=read(run/'RESULT.json')
    if state.get('status')!='completed' or state.get('phase')!='finished' or not result.get('inputs_unchanged'):
        raise ValueError('Both final evaluations and frozen-input verification must finish first')
    plan=read(run/'plan.json');training=result['training'];checkpoint=training['checkpoint']
    model_sha=sha(run/'model'/checkpoint/'model.safetensors')
    development=[];speeds=[];peaks=[];memory=[]
    for line in (run/'model/metrics.jsonl').open():
        row=json.loads(line)
        if row.get('event')=='development':
            development.append({k:row[k] for k in ['time','step','tokens','macro_answer_loss','best']})
        elif row.get('event')=='train':
            speeds.append(row['tokens_per_second']);peaks.append(row['mlx_peak_gb']);memory.append(row['system_available_gb'])
    evaluations={}
    for split in ['dev','confirmation']:
        folder=run/'evaluations'/f'final-{split}';summary=read(folder/'summary.json');protocol=read(folder/'protocol.json')
        suite_path=Path(plan['data'])/f'{split}-suite.json';suite=read(suite_path);expected=len(suite['general'])
        if (summary['evaluated_general']!=expected or summary['answer_loss']['examples']!=expected or summary['deadline_reached']
            or protocol['checkpoint_sha256']!=model_sha or protocol['suite_sha256']!=sha(suite_path)):
            raise ValueError(f'Incomplete or mismatched endpoint: {split}')
        rows=[json.loads(line) for line in (folder/'results.jsonl').open()]
        if len(rows)!=expected or any(r['stop_reason']=='context_exceeded' for r in rows):
            raise ValueError(f'Incomplete or context-exceeded responses: {split}')
        if [(r['source'],r['id']) for r in rows]!=[(r['source'],r['original_id']) for r in suite['general']]:
            raise ValueError(f'Task order mismatch: {split}')
        for source, values in summary['by_source'].items():
            source_rows=[r for r in rows if r['source']==source]
            scored_rows=[r for r in source_rows if 'correct' in r and r.get('reference_parseable',True)]
            assert values['generated']==len(source_rows) and values['scored']==len(scored_rows)
            assert values['correct']==sum(r['correct'] for r in scored_rows)
        label_diagnostics={}
        for source in ['boolq','wic','mrpc','qqp','snli','scitail','anli','multinli','cb']:
            selected=[r for r in rows if r['source']==source]
            predicted=Counter(' '.join(r['generated'].strip().casefold().split()) for r in selected)
            expected_labels=Counter(' '.join(r['expected'].strip().casefold().split()) for r in selected)
            if selected:
                label_diagnostics[source]=dict(count=len(selected),distinct_predictions=len(predicted),
                    most_frequent_prediction_count=predicted.most_common(1)[0][1],
                    most_frequent_reference_label_count=expected_labels.most_common(1)[0][1])
        families=defaultdict(lambda:dict(generated=0,scored=0,correct=0,sources=0))
        for source,s in summary['by_source'].items():
            f=families[s['family']];f['sources']+=1
            for key in ['generated','scored','correct']:f[key]+=s[key]
        for family,values in families.items():
            values['mean_source_accuracy']=summary['mean_source_accuracy_by_family'].get(family)
        scored=sum(v['scored'] for v in summary['by_source'].values());correct=sum(v['correct'] for v in summary['by_source'].values())
        proxies={}
        for metric in ['syntax_valid','text_match','nonempty']:
            selected=[r[metric] for r in rows if metric in r]
            proxies[metric]=dict(count=len(selected),positive=sum(selected))
        for source in ['samsum','go_emotions']:
            field='token_f1' if source=='samsum' else 'label_f1'
            values=[r[field] for r in rows if r['source']==source and field in r]
            proxies[source+'_'+field]=dict(count=len(values),mean=statistics.mean(values) if values else None)
        evaluations[split]=dict(summary=summary,protocol=protocol,families=dict(families),scored=scored,correct=correct,
             mixed_item_accuracy=correct/scored if scored else None,unscored=expected-scored,
             label_diagnostics=label_diagnostics,generation=dict(empty=sum(not r['generated'].strip() for r in rows),stop_reasons=dict(Counter(r['stop_reason'] for r in rows)),
                             generated_tokens=sum(r['generated_tokens'] for r in rows),
                             token_limits_by_source=dict(Counter(r['source'] for r in rows if r['stop_reason']=='token_limit'))),proxies=proxies)
    config=read(run/'model/config.json');best=min(development,key=lambda r:r['macro_answer_loss'])
    return dict(run=run.name,plan_sha256=sha(run/'plan.json'),checkpoint=checkpoint,checkpoint_sha256=model_sha,
                parameters=config['parameters'],training=training,training_end_reason=result.get('training_end_reason'),
                endpoint_amendment=result.get('endpoint_amendment'),best_development=best,final_development=development[-1],
                tokens_after_best=training['tokens']-best['tokens'],evaluations=evaluations,
                resources=dict(device=config.get('device',{}),peak_mlx_gb=max(peaks),minimum_sampled_available_gb=min(memory),
                               median_recorded_training_tokens_per_second=statistics.median(speeds),
                               active_controller_seconds_before_final_evaluation=read(run/'FINAL_EVAL_2026-09-18.prior-status.json')['active_controller_seconds']),
                frozen_inputs_verified=len(plan['inputs']))


def report(data):
    train=data['training'];dev=data['evaluations']['dev'];conf=data['evaluations']['confirmation']
    cs=conf['summary']['by_source'];labels=conf['label_diagnostics'];limits=conf['generation']['token_limits_by_source']
    label_notes=' '.join(f"{source}: {cs[source]['correct']}/{cs[source]['scored']} correct, versus {labels[source]['most_frequent_reference_label_count']}/{labels[source]['count']} for the most frequent reference label." for source in ['qqp','boolq','mrpc','multinli'])
    lines=['# Fresh 47-source / 97M — final evaluation', '',
           f"Training ended at the user's request, at **{train['step']:,} updates / {train['tokens']:,} tokens**. Final checkpoint: `{data['checkpoint']}` ({data['parameters']:,} parameters).",'',
           data['endpoint_amendment'].replace('confirmation remains uninspected before final evaluation','confirmation had not been inspected when the early endpoint was chosen'),'',
           f"The best periodic development loss was {data['best_development']['macro_answer_loss']:.6f} at {data['best_development']['tokens']:,} tokens. After {data['tokens_after_best']:,} more tokens, final periodic development loss was {data['final_development']['macro_answer_loss']:.6f}. This supports a plateau in this diagnostic, not proof that no further training could help.",'',
           '## Final task performance','',
           '| Suite | Generated tasks | Correct / scored | Mixed scored-item rate | Unscored tasks |',
           '| --- | ---: | ---: | ---: | ---: |']
    for label,e in [('Development',dev),('Confirmation (primary)',conf)]:
        lines.append(f"| {label} | {e['summary']['evaluated_general']:,} | {e['correct']} / {e['scored']} | {e['mixed_item_accuracy']:.1%} | {e['unscored']} |")
    lines += ['', 'The pooled rate is a descriptive mixture of task-specific internal scoring rules, not an official benchmark or a general intelligence score. Family accuracy below averages source accuracies equally; counts show the actual scored denominators.', '',
              '| Family | Dev mean source accuracy | Confirmation mean source accuracy | Confirmation correct / scored |',
              '| --- | ---: | ---: | ---: |']
    for name,f in conf['families'].items():
        d=dev['families'][name];fmt=lambda v:'unscored' if v is None else f'{v:.1%}'
        lines.append(f"| {name.replace('_',' ')} | {fmt(d['mean_source_accuracy'])} | {fmt(f['mean_source_accuracy'])} | {f['correct']} / {f['scored']} |")
    lines += ['', '## Confirmation source results', '', '| Source | Metric | Correct / scored | Generated |', '| --- | --- | ---: | ---: |']
    for source,s in conf['summary']['by_source'].items():
        lines.append(f"| {source} | {s['metric']} | {s['correct']} / {s['scored']} | {s['generated']} |")
    lines += ['', '## Closed-label concentration (confirmation)', '',
              'Post-hoc label-distribution diagnostic, not a pre-registered or training-derived baseline. A high repeated-label proportion warns that apparent accuracy may reflect class composition.', '',
              '| Source | Distinct predictions | Most common prediction count | Most common reference-label count | Total |',
              '| --- | ---: | ---: | ---: | ---: |']
    for source,values in conf['label_diagnostics'].items():
        lines.append(f"| {source} | {values['distinct_predictions']} | {values['most_frequent_prediction_count']} | {values['most_frequent_reference_label_count']} | {values['count']} |")
    lines += ['', '## Other diagnostics', '',
              f"Confirmation response stop reasons: `{json.dumps(conf['generation']['stop_reasons'],sort_keys=True)}`. Empty responses: {conf['generation']['empty']}.",
              f"Confirmation limited proxies: `{json.dumps(conf['proxies'],sort_keys=True)}`.",
              f"Teacher-forced answer loss on the fixed suites: dev {dev['summary']['answer_loss']['macro_source_answer_loss']:.6f}; confirmation {conf['summary']['answer_loss']['macro_source_answer_loss']:.6f}. These use their fixed suites; they are distinct from the periodic training diagnostic. Lower reference loss does not establish free-answer correctness.",'',
              '## Practical assessment of this run', '',
              'The evaluated model is stronger on short label-based language tasks than on broad free-answer capability. The results do not establish a reliable general-purpose assistant. Loss convergence alone overstated how much practical capability had been gained.',
              'Class composition matters. '+label_notes+' These post-hoc observations expose limitations of the small suite; they are not separately trained baselines or grounds for changing these reported scores.',
              f"GSM8K scored {cs['gsm8k']['correct']}/{cs['gsm8k']['scored']} and MATH {cs['math']['correct']}/{cs['math']['scored']} under this generation protocol. However, {limits.get('gsm8k',0)} GSM8K and {limits.get('math',0)} MATH responses reached the 256-token cap, so failure can include unfinished answers as well as reasoning/format errors. This evaluation does not isolate those causes or establish what a longer answer budget would achieve.",
              f"Code syntax passed for {conf['proxies']['syntax_valid']['positive']}/{conf['proxies']['syntax_valid']['count']} samples and SQL text matched for {conf['proxies']['text_match']['positive']}/{conf['proxies']['text_match']['count']}. Neither is a functional correctness result. Summary unigram F1 was {conf['proxies']['samsum_token_f1']['mean']:.3f} across {conf['proxies']['samsum_token_f1']['count']} samples; summary factuality was not evaluated.", '',
              '## Coverage and interpretation', '',
              '- All 47 sources trained the model; both evaluation suites cover 46 sources. HotpotQA has no safely separated direct holdout and is training-only.',
              '- Most sources have at most 32 questions; several have smaller quota deficits. Source percentages are coarse and uncertain. These are internal proxies, not official benchmark scores.',
              '- Code syntax validity is not functional code correctness; SQL text matching is not execution correctness; summary lexical overlap is not factuality. Open-generation narrative tasks lack correctness scoring.',
              '- Exact prompt-answer and group separation is enforced for this fresh run, not semantic independence. Some inherited holdout groups were used in older experiments; confirmation is held out from this model, not universally unseen research data.',
              '- Final checkpoint selection was chronological, but the early stopping time was chosen after inspecting development behavior. There is no best-checkpoint substitution.',
              '- Qwen has not been evaluated. No fresh-vs-legacy score or cross-tokenizer-loss comparison is valid; all older runs remain deprecated and ZIP-only.', '',
              '## Execution and provenance', '',
              f"Device: {data['resources']['device'].get('device_name')}; physical memory {data['resources']['device'].get('memory_size',0)/1024**3:.0f} GiB. FP32 training, light monitoring. Maximum sampled MLX peak: {data['resources']['peak_mlx_gb']:.3f} GB; minimum sampled available system RAM: {data['resources']['minimum_sampled_available_gb']:.2f} GB.",
              f"Median of recorded training-throughput samples: {data['resources']['median_recorded_training_tokens_per_second']:,.0f} tokens/s (not a time-weighted or end-to-end throughput). Cumulative controller time before final evaluation: {data['resources']['active_controller_seconds_before_final_evaluation']/3600:.2f} hours, including checks, checkpointing and periodic development evaluation; user/power pauses are recorded separately.",
              'Mains power, a free GPU lease, fresh PowerWatch observations and memory were checked before final evaluation. No numerical/data/scorer inputs were modified. Both evaluations use the same final-checkpoint hash and the original fixed suites, 256 maximum new tokens, greedy decoding, no functional code execution, and reference-answer loss.',
              f"Frozen inputs verified: {data['frozen_inputs_verified']}. Plan SHA256: `{data['plan_sha256']}`. Final model SHA256: `{data['checkpoint_sha256']}`.",
              'Aggregate evidence is in `aggregate.json`; raw responses, model/optimizer weights, data and process logs stay local.']
    return '\n'.join(lines)+'\n'


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    data=analyze(args.run);args.output.mkdir(parents=True,exist_ok=True)
    (args.output/'aggregate.json').write_text(json.dumps(data,indent=2,sort_keys=True)+'\n')
    (args.output/'REPORT.md').write_text(report(data))
    print(json.dumps({k:dict(correct=v['correct'],scored=v['scored'],generated=v['summary']['evaluated_general'],families=v['families'],proxies=v['proxies']) for k,v in data['evaluations'].items()},indent=2))


if __name__=='__main__':main()
