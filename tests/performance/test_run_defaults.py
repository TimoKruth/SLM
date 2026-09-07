from pathlib import Path

from run_slm import ROOT, command


def test_project_default_enables_light_and_forwards_training_arguments():
    """The project starter must preserve both the chosen workload and monitoring defaults."""
    args = command(['--run', 'runs/future', '--data', 'data/v2'], session='test-session')
    assert args[args.index('--mode')+1] == 'light'
    assert args[args.index('--warmup-steps')+1] == '10'
    assert args[args.index('--flush-seconds')+1] == '60'
    assert args[args.index('--detail-seconds')+1] == '30'
    assert args[args.index('--output')+1] == str(ROOT / 'runs/future/performance/test-session')
    assert args[args.index('--module'):] == ['--module', 'slm.sixhour', '--', '--run', 'runs/future', '--data', 'data/v2']


def test_explicit_off_keeps_no_monitoring_output_argument():
    """Explicitly disabling monitoring must avoid allocating a measurement destination."""
    args = command(['--run', 'runs/future', '--monitoring', 'off'])
    assert args[args.index('--mode')+1] == 'off'
    assert '--output' not in args


def test_resume_uses_separate_measurement_directories():
    """Repeated starts keep resume semantics while selecting distinct measurement paths."""
    argv = ['--run', 'runs/future', '--module', 'slm.train', '--resume']
    a, b = command(argv), command(argv)
    assert a[a.index('--output')+1] != b[b.index('--output')+1]
    assert a[-1] == '--resume'
    assert a[a.index('--module')+1] == 'slm.train'
