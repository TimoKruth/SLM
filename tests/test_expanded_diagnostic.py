import pytest
from experiments.run_expanded_diagnostic import validate_summary


def summary():
    return dict(selected_general=1360,evaluated_general=1360,answer_loss={'examples':1360},
                deadline_reached=False,by_source={'one':{'scored':1280,'context_exceeded':0}})


def test_accepts_complete_coverage():
    validate_summary(summary(),1360)


@pytest.mark.parametrize('field,value',[('evaluated_general',1359),('deadline_reached',True)])
def test_rejects_partial_evaluations(field,value):
    s=summary();s[field]=value
    with pytest.raises(ValueError):validate_summary(s,1360)


def test_rejects_missing_reference_loss_and_context_failure():
    s=summary();s['answer_loss']['examples']=1359
    with pytest.raises(ValueError):validate_summary(s,1360)
    s=summary();s['by_source']['one']['context_exceeded']=1
    with pytest.raises(ValueError):validate_summary(s,1360)
