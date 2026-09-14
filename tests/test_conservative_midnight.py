"""No GPU or scheduled job is started by these timing/ordering checks."""
from experiments.conservative_midnight import eligible


def test_midnight_gate_and_current_training_protection():
    c={'not_before_unix':100,'latest_start_unix':200}
    assert eligible(99,c,'completed',True,False)=='waiting_for_midnight'
    assert eligible(100,c,'running',True,False)=='waiting_for_current_run'
    assert eligible(100,c,'completed',False,False)=='waiting_for_ac_power'
    assert eligible(100,c,'completed',True,True)=='waiting_for_gpu'
    assert eligible(100,c,'completed',True,False)=='ready'
    assert eligible(200,c,'completed',True,False)=='expired'
    assert eligible(101,c,'paused',True,False)=='predecessor_not_completed'
