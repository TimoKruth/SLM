"""Scientific validity gates: masks, grouped splits, fixed work and selection."""
import copy
import numpy as np
import pytest
from research.common import weighted_mask, quality, contrast
from research.prepare import select
from research.campaign import matched


def test_weighting_preserves_baseline_and_excludes_padding():
    real, answer = np.array([[1., 1., 0.]]), np.array([[0., 1., 1.]])
    np.testing.assert_array_equal(weighted_mask(real, answer, 1), real)
    np.testing.assert_array_equal(weighted_mask(real, answer, 4), [[1, 4, 0]])
    # One prompt CE=2, one answer CE=8: correct weighted normalized objective.
    weights = weighted_mask(real, answer, 4)
    assert float((weights * [[2, 8, 999]]).sum() / weights.sum()) == 6.8


def test_group_selection_deterministic_and_disjoint():
    rows = [dict(source='s', group=str(i // 2), original_id=str(i)) for i in range(20)]
    a = select(rows, 4, 'search')
    assert a == select(list(reversed(rows)), 4, 'search')
    b = select(rows, 4, 'confirm', [r['group'] for r in a])
    assert len({r['group'] for r in a + b}) == 8


def test_work_gate_detects_same_count_different_examples():
    r = dict(status='completed', additional_tokens=3000001, additional_steps=1600,
             source_tokens={'a': 3000001}, batches_sha256='one', initial_sampler={}, final_sampler={})
    matched([r, copy.deepcopy(r)])
    bad = dict(r, batches_sha256='two')
    with pytest.raises(ValueError, match='exposure'):
        matched([r, bad])
    with pytest.raises(ValueError, match='Incomplete'):
        matched([dict(r, status='incomplete')])


def test_selection_rejects_partial_and_one_repeat_only_gain():
    with pytest.raises(ValueError, match='Incomplete'):
        quality(dict(evaluated_general=2, selected_general=3, deadline_reached=False))
    base = dict(accuracy=.25, families={'language': .25, 'math': .25}, answer_loss=1.5)
    better = dict(accuracy=.30, families={'language': .30, 'math': .30}, answer_loss=1.4)
    assert contrast([base, base], [better, better])['passes_screen']
    assert not contrast([base, base], [better, base])['passes_screen']
    regressed = dict(better, families={'language': .45, 'math': .15})
    assert not contrast([base, base], [regressed, regressed])['passes_screen']
