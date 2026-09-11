import copy
import pytest

from research.common import read, write
from study.design import BASE
from long_study.protocol import learning_rate, signature
from long_study.report import report


def test_cosine_uses_additional_tokens_and_survives_restoration():
    job = dict(parameters=dict(BASE, schedule='cosine'), schedule_tokens=100_000_000)
    state = dict(tokens=245_000_000, long_base_tokens=245_000_000,
                 step=135000, long_base_step=135000)
    assert learning_rate(job, state) == pytest.approx(3e-5)
    state['tokens'] += 50_000_000
    assert learning_rate(job, state) == pytest.approx(1.65e-5)
    restored = copy.deepcopy(state)
    assert learning_rate(job, restored) == learning_rate(job, state)
    for tokens in [345_000_000, 400_000_000]:
        state['tokens'] = tokens
        assert learning_rate(job, state) == pytest.approx(3e-6)
    p = dict(data_manifest_sha256='data', parent_checkpoint='parent', parent_weights_sha256='weights')
    assert signature(p, job) != signature(p, dict(job, schedule_tokens=50_000_000))


def test_constant_is_unchanged_and_invalid_schedule_is_rejected():
    state = dict(tokens=400_000_000, long_base_tokens=245_000_000,
                 step=230000, long_base_step=135000)
    assert learning_rate(dict(parameters=BASE), state) == BASE['lr']
    for horizon in [0, -1, float('nan'), float('inf')]:
        with pytest.raises(ValueError):
            learning_rate(dict(parameters=dict(BASE, schedule='cosine'), schedule_tokens=horizon), state)
    with pytest.raises(ValueError):
        learning_rate(dict(parameters=dict(BASE, schedule='unknown')), state)


def test_round2_reports_only_preregistered_control_comparisons(tmp_path):
    jobs = []
    for repetition in range(2):
        for condition, accuracy in zip('ABCD', [.2, .3, .4, .5]):
            name = f'{repetition}-{condition}'
            jobs.append(name)
            write(tmp_path/'jobs'/(name+'.json'), dict(repetition=repetition, condition=condition))
            summary = dict(selected_general=2, evaluated_general=2, deadline_reached=False,
                           answer_loss=dict(examples=2, macro_source_answer_loss=1),
                           mean_source_accuracy_by_family={'science': accuracy})
            write(tmp_path/'trials'/name/'confirmation/summary.json', summary)
    write(tmp_path/'parent-confirmation/summary.json', summary)
    write(tmp_path/'plan.json', dict(jobs=jobs, contrasts=[['A','B'],['A','C'],['A','D']],
                                    factorial_interaction=False, report_title='Runde 2'))
    report(tmp_path, dict(status='running'))
    result = read(tmp_path/'contrasts.json')
    assert set(result) == {f'{endpoint}:{contrast}' for endpoint in
                          ['15M','50M','final_search','final_confirmation'] for contrast in ['B-A','C-A','D-A']}
    assert result['final_confirmation:D-A'][0]['accuracy'] == pytest.approx(.3)
    assert set(read(tmp_path/'assessment.json')) == {'B-A','C-A','D-A'}
    assert (tmp_path/'REPORT.md').read_text().startswith('# Runde 2')
