from copy import deepcopy
import pytest
from experiments.run_parameter_confirmation import validate_plan, validate_summary
from experiments.report_parameter_confirmation import assess, paired

GATES = dict(minimum_gain_vs_A_per_order=.02, strictly_positive_vs_parent_per_order=True,
             maximum_mean_family_regression_vs_each_reference=.05, automatic_adoption=False)

def plan():
    return dict(mode='evaluation_only', total_budget_seconds=5400, deadline_unix=6000, budget_origin_unix=600,
                gates=GATES, jobs=[dict(condition='parent',order=None,endpoint='parent')]+
                [dict(condition=c,order=o,endpoint='75M',additional_tokens=75000100+o,step=100+o) for o in (0,1) for c in 'AD'])

def test_requires_matched_tokens_and_updates_and_original_cap():
    validate_plan(plan())
    for key,value in [('additional_tokens',75001000),('step',999)]:
        p=plan();p['jobs'][1][key]=value
        with pytest.raises(AssertionError):validate_plan(p)
    p=plan();p['deadline_unix']+=1
    with pytest.raises(AssertionError):validate_plan(p)

def comparison(per_order, family):
    return dict(per_order=per_order,uncertainty={'families':{'f':{'delta':family}}})

def test_gates_cannot_hide_one_order_or_parent_or_family_failure():
    good={'D-A-75M':comparison([.02,.03],-.05),'D-parent-75M':comparison([.01,.01],0)}
    assert assess(good,GATES)['all_quality_gates_passed']
    for name,field,value in [('D-A-75M','per_order',[.01,.20]),('D-parent-75M','per_order',[0,.01])]:
        c=deepcopy(good);c[name][field]=value
        assert not assess(c,GATES)['all_quality_gates_passed']
    c=deepcopy(good);c['D-parent-75M']['uncertainty']['families']['f']['delta']=-.051
    assert not assess(c,GATES)['all_quality_gates_passed']

def test_summary_rejects_missing_reference_loss():
    s=dict(selected_general=1360,evaluated_general=1360,answer_loss={'examples':1359},deadline_reached=False,
           by_source={'s':{'scored':1280,'context_exceeded':0}})
    with pytest.raises(ValueError):validate_summary(s,1360)

def test_pairing_preserves_data_order_dependence():
    def rows(v):return {('s',str(i)):dict(source='s',family='f',correct=bool(x)) for i,x in enumerate(v)}
    tasks={('s',str(i)):{'group':str(i)} for i in range(2)}
    r=paired([rows([0,1]),rows([1,0])],[rows([1,0]),rows([0,1])],tasks)
    assert r['mean']==0 and r['uncertainty']['fixed_source_interval95']==[0,0]
