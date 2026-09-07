"""Broad sampling, data contracts and diagnostic scoring regressions."""
import json
import sqlite3
from collections import defaultdict
from pathlib import Path
import pytest
from slm.breadth import sampling_weights, SOURCE_FAMILY, FAMILIES
from slm.broad_eval import score_general, final_answer
from slm.code_eval import same_output, score
from experiments.prepare_broad import converted, sql_query, context_key
from experiments.prepare_checks import EXTRA_CASES


def test_equal_families_keeps_all_32_sources_without_code_priority():
    weights = sampling_weights(SOURCE_FAMILY)
    mass = defaultdict(float)
    for source, weight in weights.items():
        mass[SOURCE_FAMILY[source]] += weight
    assert len(weights) == 32
    assert all(abs(v-1/7)<1e-12 for v in mass.values())
    assert sum(weights.values()) == pytest.approx(1)
    assert set(sampling_weights(SOURCE_FAMILY,'sources').values()) == {1/32}


def test_entailment_and_dialogue_labels_and_groups():
    a = converted('anli', {'premise':'same premise','hypothesis':'first','label':0,'uid':'a'}, 'a')
    b = converted('anli', {'premise':'same premise','hypothesis':'second','label':2,'uid':'b'}, 'b')
    assert a['answer']=='entailment' and b['answer']=='contradiction'
    assert a['group']==b['group'] and a['split']==b['split']
    d = converted('dream', {'dialogue':['hello'],'dialogue_id':'x','question':'why','choice':['a','b'],'answer':'b'}, 'x')
    assert d['answer']=='b' and d['choices']==['a','b']
    assert context_key(a['prompt']) == context_key(b['prompt'])


def test_sql_serialization_executes_original_structure_and_quotes():
    raw = {'table':{'header':['value','owner']},'sql':{'sel':0,'agg':4,'conds':{'column_index':[1],'operator_index':[0],'condition':["O'Reilly"]}}}
    query = sql_query(raw)
    with sqlite3.connect(':memory:') as db:
        db.execute('CREATE TABLE data(value REAL, owner TEXT)')
        db.executemany('INSERT INTO data VALUES (?,?)',[(3,"O'Reilly"),(7,"O'Reilly"),(99,'other')])
        assert db.execute(query).fetchall()==[(10.0,)]


def test_diagnostic_metrics_do_not_call_syntax_or_narrative_correct():
    assert 'correct' not in score_general({'source':'apps','answer':'print(2)'},'print(1)')
    assert 'correct' not in score_general({'source':'hellaswag','answer':'story'},'story')
    assert score_general({'source':'gsm8k','answer':'Calculation\n#### 6'},'Incorrect math\n#### 84')['correct'] is False
    assert final_answer('text \\boxed{\\frac{1}{2}}','math')=='\\frac{1}{2}'
    assert score_general({'source':'snli','answer':'neutral'},'neutral')['correct']


def test_large_integer_comparison_and_false_sample_pass():
    assert not same_output('1000000000001','1000000000000')
    assert same_output('001','1')
    task = {'source':'apps','cases':EXTRA_CASES['1409']}
    assert score('for _ in range(int(input())): print(int(input())//2)',task)['status']=='wrong_answer'
    assert score('for _ in range(int(input())): print(int(input()).bit_count())',task)['status']=='passed'


def test_frozen_suite_keeps_learning_control_out_of_development():
    path = Path('data/broad-checks-2026-09-07/suite.json')
    if not path.exists():
        pytest.skip('Local data not available')
    suite = json.loads(path.read_text())
    train, dev = suite['memorization'],suite['general']
    assert len(train)==128 and len({r['source'] for r in train})==32
    assert {r['group'] for r in train}.isdisjoint(r['group'] for r in dev)
    assert all(r['original_split']=='train' for r in train+dev)
