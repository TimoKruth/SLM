"""Actual original training/checkpoint/resume path, exclusively on a tiny CPU model."""
import json
import sys
import types
from datetime import datetime,timezone,timedelta
from pathlib import Path

import mlx.core as mx
import numpy as np
import pytest
from slm_perf.instrument import ROOT,transformed
from slm_perf.runtime import Monitor


@pytest.mark.parametrize('mode',['light','detail'])
def test_monitored_training_and_resume_match_original_on_cpu(tmp_path,monkeypatch,mode):
    import slm.train as original
    previous=mx.default_device()
    mx.set_default_device(mx.cpu)
    try:
        with monkeypatch.context() as patch:
            patch.setattr(mx,'set_default_device',lambda _:None)
            patch.setattr(mx,'set_memory_limit',lambda _:None)
            patch.setattr(mx,'set_cache_limit',lambda _:None)
            patch.setattr(mx,'device_info',lambda:{'device_name':'CPU test'})
            # Fix wall-clock LR scheduling to isolate instrumentation semantics.
            fixed=datetime(2026,9,7,tzinfo=timezone.utc)
            patch.setattr(original.time,'time',lambda:fixed.timestamp())
            data=tmp_path/'data';data.mkdir()
            for split in ['train','dev']:
                np.array([1,2,3,4,5,6,7],dtype=np.uint16).tofile(data/f'toy.{split}.bin')
                np.array([0,0,1,1,0,0,1],dtype=np.uint8).tofile(data/f'toy.{split}.mask.bin')
                np.save(data/f'toy.{split}.index.npy',np.array([[0,4],[4,3]]))
            (data/'manifest.json').write_text(json.dumps({'tokenizer':{'vocab_size':64},'sources':{'toy':{}},'source_weights':{'toy':1},'evaluation_weights':{'toy':1}}))
            (data/'tokenizer.json').write_text('{}')
            monitor=Monitor(tmp_path/'perf',mode=mode,warmup_steps=1)
            monitor.start_detail()
            module=types.ModuleType('slm.monitored_test')
            module.__dict__.update(__file__=str(ROOT/'slm/train.py'),__package__='slm',_slm_perf=monitor)
            code,_=transformed((ROOT/'slm/train.py').read_text(),str(ROOT/'slm/train.py'),'slm.train')
            exec(code,module.__dict__)
            runs=[tmp_path/'original',tmp_path/'monitored']
            for steps,resume in [(2,False),(3,True)]:
                for mod,run in zip([original,module],runs):
                    argv=['train','--run',str(run),'--data',str(data),'--until',(fixed+timedelta(hours=1)).isoformat(),
                          '--steps',str(steps),'--context','16','--dim','16','--layers','1','--heads','2','--hidden','32','--batch-size','1','--skip-initial-eval']
                    if resume:argv.append('--resume')
                    patch.setattr(sys,'argv',argv)
                    mod.main()
                for suffix in ['model.safetensors','optimizer.npz','state.json']:
                    files=[]
                    for run in runs:
                        folder=json.loads((run/'latest.json').read_text())['checkpoint'];files.append(run/folder/suffix)
                    if suffix.endswith('.json'):
                        assert json.loads(files[0].read_text())==json.loads(files[1].read_text())
                    else:
                        a,b=[mx.load(str(f)) for f in files]
                        assert a.keys()==b.keys()
                        for key in a:np.testing.assert_array_equal(np.array(a[key]),np.array(b[key]))
            monitor.finish()
            phases=monitor.result('completed')['phases']
            assert any('checkpoint' in key for key in phases)
            assert any('device.execute_and_wait' in key for key in phases)
            assert monitor.steps==3
    finally:
        mx.set_default_device(previous)
