import pytest
from experiments.report_expanded_diagnostic import paired


def rows(values):
    return {('s',str(i)):dict(source='s',family='f',correct=bool(v)) for i,v in enumerate(values)}


def test_opposite_data_orders_do_not_become_independent_tasks():
    tasks={('s',str(i)):{'group':str(i)} for i in range(2)}
    result=paired([rows([0,1]),rows([1,0])],[rows([1,0]),rows([0,1])],tasks)
    assert result['mean']==0
    assert result['uncertainty']['fixed_source_interval95']==[0,0]
    assert result['transitions']['gain']==result['transitions']['loss']==2


def test_rejects_missing_task_in_pair():
    with pytest.raises(ValueError):paired([rows([0]),rows([0])],[rows([1,0]),rows([1,0])],{('s','0'):{'group':'0'}})
