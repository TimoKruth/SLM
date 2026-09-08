import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace
import pytest
from resource_monitor.report import chart,live_document,process_name


def test_chart_breaks_at_gaps_and_missing_values():
    rows=[{'ts':0,'v':0},{'ts':15,'v':100},{'ts':90,'v':20},{'ts':105,'v':None},{'ts':120,'v':10}]
    result=chart(rows,'v','CPU','red')
    assert result.count('<polyline')==3
    assert '147.5,30.0' in result  # Actual peak retained, not averaged away.
    assert chart([], 'v','CPU','red')==''


def test_freshness_refresh_and_missing_not_zero():
    result=live_document('<meta charset="utf-8"><div class="cards">',{'ts':0,'cpu_idle':None,'gpu_device':None})
    assert 'CPU n/a' in result and 'GPU n/a' in result
    assert 'http-equiv="refresh"' in result and 'seconds>90' in result


def test_process_arguments_not_published():
    assert process_name('/usr/bin/python3 script.py --token hidden')=='python3'
    assert process_name('/Applications/Example.app/Contents/MacOS/Example --key hidden')=='Example.app'
    assert process_name('"broken')=='unbekannt'


def test_read_only_snapshot_and_failed_publish_preserves_old_report(tmp_path,monkeypatch):
    import resource_monitor.report as module
    db_path=tmp_path/'samples.db'
    with sqlite3.connect(db_path) as db:
        db.execute('create table samples(n integer)');db.execute('insert into samples values (1)')
    def payload(db,hours):
        with pytest.raises(sqlite3.OperationalError):db.execute('delete from samples')
        return {'rows':[{'ts':1,'iso':'1970-01-01','cpu_idle':90,'gpu_device':80,'mem_used':1,'mem_compressed':0}],
            'hardware':{'memory':64*1024**3},'cpu_avg':10,'gpu_avg':80}
    def write(payload,destination):destination.write_text('<meta charset="utf-8"><div class="cards">')
    backend=SimpleNamespace(DB_PATH=db_path,report_payload=payload,write_html_report=write,format_bytes=lambda value: str(value))
    monkeypatch.setattr(module,'load_powerwatch',lambda _:backend)
    out=tmp_path/'report';result=module.render(tmp_path,out)
    assert result['database_modified_by_reporter'] is False
    previous=(out/'latest.html').read_bytes()
    def fail(payload,destination):destination.write_text('partial');raise ValueError('fixture failure')
    backend.write_html_report=fail
    with pytest.raises(ValueError):module.render(tmp_path,out)
    assert (out/'latest.html').read_bytes()==previous
    assert not (out/'latest.tmp.html').exists()
    with sqlite3.connect(db_path) as db:assert db.execute('select count(*) from samples').fetchone()[0]==1
