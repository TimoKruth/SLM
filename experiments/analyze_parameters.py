"""CPU-only paired analysis of saved parameter-study answers; no model imports."""
import argparse
import ast
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import string

import numpy as np


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def scored(row):
    return 'correct' in row and row.get('reference_parseable', True)


def scorer(path):
    """Load only the frozen pure scoring functions, without importing its GPU module."""
    tree = ast.parse(path.read_text())
    names = {'normalize', 'final_answer', 'score_general'}
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    assert {n.name for n in nodes} == names
    scope = dict(re=re, string=string, Counter=Counter,
                 NARRATIVE={'hellaswag', 'piqa'}, CODE={'apps', 'mbpp', 'code_contests'},
                 QA={'squad', 'quoref', 'ropes', 'drop', 'hotpotqa'})
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), scope)
    return scope


def diagnostics(row, final_answer):
    words = re.findall(r'\w+', row['generated'].casefold())
    grams = Counter(tuple(words[i:i+3]) for i in range(max(0, len(words)-2)))
    repeated = (len(words) >= 12 and max(grams.values(), default=0) >= 3
                and sum(n-1 for n in grams.values()) / max(1, sum(grams.values())) >= .30)
    limited = row.get('generated_tokens', 0) >= row.get('token_budget', math.inf) or row.get('stop_reason') in {'token_limit', 'token_budget', 'max_tokens', 'context_limit'}
    missing = (row['source'] in {'gsm8k', 'math', 'aqua_rat', 'qasc'}
               and final_answer(row['generated'], row['source']) is None)
    return dict(empty=not row['generated'].strip(), repetition_flag=repeated,
                token_limit_flag=limited, required_answer_unparseable=missing,
                reference_unparseable=row.get('reference_parseable') is False)


def macro(rows):
    source = defaultdict(list)
    for row in rows.values():
        if scored(row):
            source[row['family'], row['source']].append(float(row['correct']))
    family = defaultdict(list)
    for (f, _), values in source.items():
        family[f].append(statistics.mean(values))
    return statistics.mean(statistics.mean(v) for v in family.values())


def interval(values):
    return [float(x) for x in np.quantile(values, [.025, .975])]


def bootstrap(differences, draws=5000, seed=20260915):
    """Paired group bootstrap within source, then equal source/family macro.

    Each value is a list of groups; group arrays are [task, fixed data order].
    Same group weights for both orders. Sources fixed in primary interval.
    Secondary interval resamples sources within each fixed family as sensitivity.
    """
    rng = np.random.default_rng(seed)
    by_family = defaultdict(list)
    by_order = None
    observed_family = {}
    for (family, source), groups in sorted(differences.items()):
        totals = np.asarray([g.sum(axis=0) for g in groups])
        sizes = np.asarray([len(g) for g in groups])
        weights = rng.multinomial(len(groups), np.full(len(groups), 1/len(groups)), size=draws)
        samples = (weights @ totals) / (weights @ sizes)[:, None]
        by_family[family].append((source, samples, totals.sum(axis=0)/sizes.sum()))
    fixed, hierarchical = [], []
    for family, sources in sorted(by_family.items()):
        samples = np.stack([x[1] for x in sources], axis=1)
        fixed.append(samples.mean(axis=1))
        source_weights = rng.multinomial(len(sources), np.full(len(sources), 1/len(sources)), size=draws)
        hierarchical.append((samples * source_weights[:, :, None]).sum(axis=1)/len(sources))
        point = np.stack([x[2] for x in sources]).mean(axis=0)
        observed_family[family] = dict(delta=float(point.mean()), per_order=point.tolist(),
                                      interval95=interval(fixed[-1].mean(axis=1)))
    by_order = np.stack(fixed).mean(axis=0)
    return dict(draws=draws, seed=seed, fixed_source_interval95=interval(by_order.mean(axis=1)),
                per_order_interval95=[interval(by_order[:, i]) for i in range(by_order.shape[1])],
                source_resampling_sensitivity_interval95=interval(np.stack(hierarchical).mean(axis=(0, 2))),
                families=observed_family,
                interpretation='Exploratory percentile intervals conditional on these two data orders and fixed parent. Groups paired across orders; no independent-seed inference, multiplicity adjustment, or new acceptance decision. Secondary source resampling changes the target to source composition within fixed families.')


def analyze(run, output, frozen_scorer, reviews=None):
    run, output = run.resolve(), output.resolve()
    assert not output.is_relative_to(run)
    hashes = {}
    def read(path):
        hashes[str(path)] = digest(path)
        return json.loads(path.read_text())
    def jsonl(path):
        hashes[str(path)] = digest(path)
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        result = {(r['source'], str(r['id'])): r for r in rows}
        assert len(result) == len(rows)
        return result
    status = read(run/'status.json'); assert status['status'] == 'completed'
    read(run/'RUN_CONDITIONS.json')
    hashes[str(frozen_scorer)] = digest(frozen_scorer)
    scoring = scorer(frozen_scorer)
    suite = {name: read(run/f'{name}-suite.json') for name in ('search', 'confirmation')}
    tasks = {name: {(r['source'], str(r['original_id'])): r for r in s['general']} for name, s in suite.items()}
    endpoints = {'15M': 'token-015000000/search', '50M': 'token-050000000/search', 'final_search': 'search', 'final_confirmation': 'confirmation'}
    data, summaries, diag, local_cases = {}, {}, [], []
    reported = read(run/'quality.json')
    manual = read(reviews) if reviews else []
    option_cases = []
    for condition, order in [(c, o) for c in 'ABCD' for o in range(2)] + [('parent', 0)]:
        if condition != 'parent':
            read(run/f'trials/long-round2-r{order}-{condition}/RUN_CONDITIONS.json')
        for endpoint, suffix in endpoints.items():
            if condition == 'parent' and endpoint != 'final_confirmation':
                continue
            folder = run/'parent-confirmation' if condition == 'parent' else run/f'trials/long-round2-r{order}-{condition}'/suffix
            rr = jsonl(folder/'results.jsonl'); s = read(folder/'summary.json')
            name = 'confirmation' if endpoint == 'final_confirmation' else 'search'
            assert rr.keys() == tasks[name].keys()
            assert s['selected_general'] == s['evaluated_general'] == s['answer_loss']['examples'] == len(rr)
            assert not s['deadline_reached']
            assert len({r['group'] for r in tasks[name].values()}) == len(rr), 'Historical suite is not one task per group'
            source_counts = defaultdict(Counter); family_counts = defaultdict(Counter)
            for key, row in rr.items():
                task = tasks[name][key]
                assert row['expected'] == task['answer']
                rescore = scoring['score_general'](task, row['generated'])
                for metric, value in rescore.items():
                    assert row[metric] == value, (condition, order, endpoint, key, metric)
                if row['source'] == 'aqua_rat' and row.get('correct') is False:
                    expected = scoring['final_answer'](row['expected'], 'aqua_rat')
                    label = re.search(r'(?:Answer\s*:|answer\s+is)\s*([A-Ea-e])(?:[).\s].*)?\s*$', row['generated'])
                    if label and expected and re.match(r'^[a-e][).]', expected) and label[1].casefold() == expected[0]:
                        option_cases.append(dict(condition=condition, order=order, endpoint=endpoint, source=row['source'], id=str(row['id']), expected=row['expected'], generated=row['generated'], interpretation='Same option letter despite strict mismatch; manual review required, never an automatic correction.'))
                flags = diagnostics(row, scoring['final_answer'])
                counts = Counter(evaluated=1, scored=int(scored(row)), correct=int(scored(row) and row['correct']))
                counts.update({k: int(v) for k, v in flags.items()})
                counts['incorrect_without_surface_flags'] = int(scored(row) and not row['correct'] and not any(flags.values()))
                counts['incorrect_with_surface_flags'] = int(scored(row) and not row['correct'] and any(flags.values()))
                source_counts[row['source']].update(counts); family_counts[row['family']].update(counts)
            for source, counts in source_counts.items():
                assert (counts['evaluated'], counts['scored'], counts['correct']) == tuple(s['by_source'][source][k] for k in ['generated', 'scored', 'correct'])
            assert math.isclose(macro(rr), statistics.mean(s['mean_source_accuracy_by_family'].values()), abs_tol=1e-12)
            if condition != 'parent':
                q = next(q for q in reported if (q['condition'], q['repetition'], q['endpoint']) == (condition, order, endpoint))
                assert math.isclose(q['accuracy'], macro(rr), abs_tol=1e-12)
            data[condition, order, endpoint] = rr; summaries[condition, order, endpoint] = s
            diag.append(dict(condition=condition, order=order, endpoint=endpoint,
                             sources=dict(source_counts), families=dict(family_counts),
                             totals=dict(sum(source_counts.values(), Counter())),
                             stop_reasons=dict(Counter(r['stop_reason'] for r in rr.values()))))
    coverage = {}
    for name, tt in tasks.items():
        rr = data['A', 0, 'final_'+name]
        source_family = {r['source']: r['family'] for r in rr.values()}
        scored_sources = {r['source'] for r in rr.values() if scored(r)}
        family_sources = Counter(source_family[s] for s in scored_sources)
        coverage[name] = []
        for source in sorted(source_family):
            records = [r for r in rr.values() if r['source'] == source]
            n = sum(scored(r) for r in records); family = source_family[source]
            coverage[name].append(dict(source=source, family=family, generated=len(records), scored=n,
                                      groups=len({tt[(r['source'], str(r['id']))]['group'] for r in records}),
                                      single_answer_overall_pp=100/(len(family_sources)*family_sources[family]*n) if n else None))
    comparisons, trajectories = [], []
    for endpoint in endpoints:
        name = 'confirmation' if endpoint == 'final_confirmation' else 'search'
        for condition in 'BCD':
            groups = defaultdict(lambda: defaultdict(list)); transitions = Counter(); source_changes = defaultdict(Counter)
            per_order = []; losses = []; source_loss = defaultdict(list)
            for order in range(2):
                a, b = data['A', order, endpoint], data[condition, order, endpoint]
                per_order.append(macro(b)-macro(a))
                sa, sb = summaries['A', order, endpoint], summaries[condition, order, endpoint]
                losses.append(sb['answer_loss']['macro_source_answer_loss']-sa['answer_loss']['macro_source_answer_loss'])
                for source in sa['answer_loss']['source_answer_loss']:
                    source_loss[source].append(sb['answer_loss']['source_answer_loss'][source]-sa['answer_loss']['source_answer_loss'][source])
            a0 = data['A', 0, endpoint]
            for key, a in a0.items():
                if not scored(a):
                    continue
                values = []
                task = tasks[name][key]
                for order in range(2):
                    aa, bb = data['A', order, endpoint][key], data[condition, order, endpoint][key]
                    assert scored(bb) and (aa['family'], aa['metric']) == (bb['family'], bb['metric'])
                    delta = int(bb['correct'])-int(aa['correct']); values.append(delta)
                    tag = 'gain' if delta > 0 else 'loss' if delta < 0 else 'both_correct' if aa['correct'] else 'both_wrong'
                    transitions[tag] += 1; source_changes[a['source']][tag] += 1
                    if delta or (not aa['correct'] and diagnostics(aa, scoring['final_answer'])['required_answer_unparseable']):
                        local_cases.append(dict(condition=condition, order=order, endpoint=endpoint, source=key[0], id=key[1],
                                                transition=tag, task=task, baseline=aa, candidate=bb))
                groups[a['family'], a['source']][task['group']].append(values)
            differences = {k: [np.asarray(v, dtype=float) for v in g.values()] for k, g in groups.items()}
            uncertainty = bootstrap(differences)
            mean_delta = statistics.mean(per_order)
            assert math.isclose(mean_delta, statistics.mean(f['delta'] for f in uncertainty['families'].values()), abs_tol=1e-12)
            source_details = {}
            for source, counts in source_changes.items():
                delta = (counts['gain']-counts['loss'])/sum(counts.values())
                source_details[source] = dict(counts, accuracy_delta=delta, answer_loss_delta=statistics.mean(source_loss[source]),
                                              loss_improves_accuracy_declines=statistics.mean(source_loss[source]) < 0 and delta < 0)
            comparisons.append(dict(condition=condition, endpoint=endpoint, accuracy_deltas=per_order, mean_delta=mean_delta,
                                    answer_loss_deltas=losses, transitions=dict(transitions), sources=source_details, uncertainty=uncertainty))
    for condition in 'ABCD':
        for order in range(2):
            for before, after in [('15M','50M'),('50M','final_search')]:
                a, b = data[condition, order, before], data[condition, order, after]
                flips = Counter('gain' if b[k]['correct'] and not r['correct'] else 'loss' if r['correct'] and not b[k]['correct'] else 'unchanged' for k,r in a.items() if scored(r))
                trajectories.append(dict(condition=condition, order=order, before=before, after=after, accuracy_delta=macro(b)-macro(a), transitions=dict(flips)))
    loss_decomposition = {}
    for condition in 'BCD':
        parts = defaultdict(list)
        for order in range(2):
            a, b = summaries['A', order, 'final_confirmation'], summaries[condition, order, 'final_confirmation']
            sources_scored = {r['source'] for r in data['A', order, 'final_confirmation'].values() if scored(r)}
            for source, value in a['answer_loss']['source_answer_loss'].items():
                parts['scored' if source in sources_scored else 'unscored'].append(b['answer_loss']['source_answer_loss'][source]-value)
        count = sum(len(v) for v in parts.values())
        loss_decomposition[condition] = {k:dict(mean_source_delta=statistics.mean(v), contribution_to_overall_delta=sum(v)/count) for k,v in parts.items()}
    exclusions = {(r['source'],str(r['id'])) for r in manual if r['category'].startswith('reference_')}
    sensitivity = []
    for endpoint in endpoints:
        for order in range(2):
            subsets = {c:{k:r for k,r in data[c,order,endpoint].items() if k not in exclusions} for c in 'ABCD'}
            sensitivity.append(dict(endpoint=endpoint, order=order, excluded_count=len(data['A',order,endpoint])-len(subsets['A']),
                                    macro_accuracy={c:macro(r) for c,r in subsets.items()},
                                    delta_vs_A={c:macro(subsets[c])-macro(subsets['A']) for c in 'BCD'}))
    output.mkdir(parents=True, exist_ok=False)
    result = dict(reference_exclusion_sensitivity=sensitivity, loss_decomposition=loss_decomposition, option_letter_disagreement_cases=[{k:r[k] for k in ['condition','order','endpoint','source','id']} for r in option_cases], coverage=coverage, diagnostics=diag, comparisons=comparisons, trajectories=trajectories,
                  checked_evaluations=len(data), checked_generated_answers=sum(len(r) for r in data.values()),
                  diagnostic_limits='Surface flags overlap and are not causal labels. An unparseable final answer may also contain incorrect reasoning; no historical score is changed. Per-source teacher-forced loss cannot be assigned to individual answers.')
    (output/'analysis.json').write_text(json.dumps(result, indent=2)+'\n')
    (output/'option-letter-review.json').write_text(json.dumps(option_cases, indent=2)+'\n')
    (output/'case-review.json').write_text(json.dumps(local_cases, indent=2)+'\n')
    for path, checksum in hashes.items():
        assert digest(Path(path)) == checksum
    (output/'provenance.json').write_text(json.dumps(dict(inputs=hashes, script_sha256=digest(Path(__file__)), verified_at=datetime.now(timezone.utc).isoformat()), indent=2)+'\n')
    print(json.dumps({'output':str(output), 'evaluations':len(data),'answers':result['checked_generated_answers'],
                      'confirmation':[{k:c[k] for k in ['condition','mean_delta','transitions','uncertainty']} for c in comparisons if c['endpoint']=='final_confirmation']}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--frozen-scorer', type=Path, required=True)
    parser.add_argument('--reviews', type=Path)
    args = parser.parse_args()
    analyze(args.run, args.output, args.frozen_scorer, args.reviews)
