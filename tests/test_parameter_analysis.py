import numpy as np
from experiments.analyze_parameters import bootstrap, diagnostics, scorer
from pathlib import Path


def test_opposite_orders_remain_paired():
    groups = [np.array([[1., -1.]]), np.array([[-1., 1.]])]
    result = bootstrap({('f', 's'): groups}, draws=1000)
    assert result['fixed_source_interval95'] == [0., 0.]
    assert result['per_order_interval95'][0] == [-1., 1.]


def test_macro_weights_sources_not_number_of_tasks():
    result = bootstrap({('f','small'): [np.ones((1, 2))],
                        ('f','large'): [np.zeros((10, 2)) for _ in range(10)]}, draws=1000)
    assert result['families']['f']['delta'] == .5
    assert result['fixed_source_interval95'] == [.5, .5]


def test_cluster_sampling_preserves_all_tasks_in_a_group():
    result = bootstrap({('f','s'): [np.array([[1.,1.],[-1.,-1.]])]}, draws=1000)
    assert result['fixed_source_interval95'] == [0., 0.]


def test_flags_overlap_without_asserting_reasoning_correctness():
    final = scorer(Path('slm/broad_eval.py'))['final_answer']
    row = dict(source='gsm8k', generated='the answer repeats ' * 20,
               generated_tokens=256, token_budget=256, stop_reason='token_limit')
    flags = diagnostics(row, final)
    assert flags['repetition_flag'] and flags['token_limit_flag'] and flags['required_answer_unparseable']
    assert not flags['reference_unparseable']


def test_selection_is_grouped_order_invariant_and_honors_exclusions():
    from experiments.prepare_parameter_evaluation import select_groups
    rows = [dict(source='s',group=g,original_id=str(i),variant=i) for i,g in enumerate(['a','a','b','c'])]
    selected = select_groups(rows, 4, 'fixed', {'c'})
    assert selected == select_groups(list(reversed(rows)), 4, 'fixed', {'c'})
    assert len(selected) == 2
    assert {r['group'] for r in selected} == {'a','b'}
