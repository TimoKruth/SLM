import json
from pathlib import Path
import threading
import time
from functools import partial
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import pytest
from training_dashboard.server import history, snapshot, Handler


def put(path, data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data))


def test_resume_gap_and_rollback_preserved_with_partial_tail(tmp_path):
    p=tmp_path/'metrics.jsonl'
    rows=[
        dict(event='start',time='2026-09-16T10:00:00+02:00',step=0,tokens=0),
        dict(event='train',time='2026-09-16T10:00:10+02:00',step=10,tokens=100,tokens_per_second=10),
        dict(event='train',time='2026-09-16T10:00:20+02:00',step=20,tokens=200,tokens_per_second=30),
        dict(event='development',time='2026-09-16T10:00:25+02:00',step=20,macro_answer_loss=1.25),
        dict(event='finished',time='2026-09-16T10:00:30+02:00'),
        dict(event='start',time='2026-09-18T10:00:00+02:00',step=10,tokens=100,resumed=True),
        dict(event='train',time='2026-09-18T10:00:10+02:00',step=15,tokens=150,tokens_per_second=15),
    ]
    p.write_text('\n'.join(json.dumps(row) for row in rows)+'\n{"event":')
    before=p.read_bytes();h=history(p)
    assert len(h['segments'])==2
    assert h['segments'][0][-1]['tokens']==200
    assert h['segments'][0][-1]['speed']==20
    assert h['segments'][1][0]['tokens']==100
    assert h['segments'][1][-1]['tokens']==150 # Do not hide recovered-checkpoint rollback.
    assert len(h['development'])==1
    assert h['sessions'][0]['end']-h['sessions'][0]['time']==30
    assert h['incomplete_lines']==1 and p.read_bytes()==before


def test_paused_status_uses_checkpoint_instead_of_stale_running_sample(tmp_path):
    put(tmp_path/'status.json',dict(status='paused',phase='training'))
    put(tmp_path/'model/status.json',dict(status='running',step=109,tokens=1090,tokens_per_second=123))
    put(tmp_path/'model/latest.json',dict(checkpoint='checkpoint-100'))
    put(tmp_path/'model/checkpoint-100/state.json',dict(step=100,tokens=1000))
    s=snapshot(tmp_path)
    assert not s['live'] and s['recoverable']
    assert s['steps']==100 and s['tokens']==1000 and s['speed'] is None


def test_stale_heartbeat_never_claims_live_training(tmp_path,monkeypatch):
    put(tmp_path/'status.json',dict(status='running',phase='training',pid=123,heartbeat='2020-01-01T00:00:00+00:00'))
    put(tmp_path/'model/status.json',dict(status='running',step=10,tokens=100,tokens_per_second=123))
    monkeypatch.setattr('training_dashboard.server.process_present',lambda _:True)
    s=snapshot(tmp_path)
    assert not s['live'] and s['speed'] is None and s['heartbeat_age']>90


def test_partial_evaluation_is_not_complete(tmp_path):
    put(tmp_path/'model/config.json',dict(data=str(tmp_path/'data')))
    put(tmp_path/'data/confirmation-suite.json',dict(general=[{},{}]))
    put(tmp_path/'evaluations/final-confirmation/summary.json',dict(evaluated_general=1,answer_loss=dict(examples=1),deadline_reached=False))
    assert not snapshot(tmp_path)['evaluations'][1]['completed']
    put(tmp_path/'evaluations/final-confirmation/summary.json',dict(evaluated_general=2,answer_loss=dict(examples=2),deadline_reached=False))
    assert snapshot(tmp_path)['evaluations'][1]['completed']


def test_http_only_serves_whitelisted_assets_and_readonly_aggregate(tmp_path):
    put(tmp_path/'status.json',dict(status='paused',phase='training'))
    put(tmp_path/'AUTHORIZATION.json',dict(secret='do not serve'))
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,run=tmp_path))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f'http://127.0.0.1:{server.server_port}'
    try:
        with urlopen(base+'/api/status') as response:
            assert response.headers['Cache-Control']=='no-store'
            data=json.load(response);assert data['status']=='paused' and 'secret' not in data
        with urlopen(base+'/time_axis.js') as response:assert b'trainingElapsed' in response.read()
        for path in ['/AUTHORIZATION.json','/../AGENTS.md']:
            with pytest.raises(HTTPError) as e:urlopen(base+path)
            assert e.value.code==404
        with pytest.raises(HTTPError) as e:urlopen(Request(base+'/api/status',headers={'Host':'external.example'}))
        assert e.value.code==403
        with pytest.raises(HTTPError) as e:urlopen(Request(base+'/api/status',method='POST'))
        assert e.value.code==501
    finally:
        server.shutdown();server.server_close();thread.join()
