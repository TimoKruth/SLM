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


def test_broad_evaluation_fingerprints_selected_checkpoint(tmp_path):
    import hashlib
    import json
    from slm_perf.__main__ import workload
    (tmp_path/'best.safetensors').write_bytes(b'best')
    (tmp_path/'checkpoint-0000010').mkdir()
    (tmp_path/'checkpoint-0000010/model.safetensors').write_bytes(b'latest')
    (tmp_path/'latest.json').write_text(json.dumps({'checkpoint':'checkpoint-0000010'}))
    args=['--run',str(tmp_path)]
    assert workload('slm.broad_eval',args)['checkpoint_sha256']==hashlib.sha256(b'best').hexdigest()
    assert workload('slm.broad_eval',args+['--checkpoint','latest'])['checkpoint_sha256']==hashlib.sha256(b'latest').hexdigest()
