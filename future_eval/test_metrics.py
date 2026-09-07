import json
from pathlib import Path
import pytest
from .metrics import arithmetic,error_tags,label_diagnostic,sql_compare,sql_result,wilson
from .prepare import retain,near_duplicates
from .queue import ready,validate

TABLE={'header':['name','value'],'types':['text','real'],'rows':[['a',1],['b',2],['b',2]]}

def test_sql_results_preserve_duplicates_and_allow_equivalent_queries():
    assert sql_compare('SELECT name FROM data WHERE value >= 2','SELECT name FROM data WHERE value > 1',TABLE)['status']=='match'
    assert sql_compare('SELECT DISTINCT name FROM data','SELECT name FROM data',TABLE)['status']=='mismatch'
    assert sql_compare('SELECT name FROM data ORDER BY value DESC','SELECT name FROM data ORDER BY value ASC',TABLE)['status']=='mismatch'

def test_sql_readonly_and_resource_limits():
    for query in ['DELETE FROM data','SELECT load_extension("bad")','SELECT * FROM data; DROP TABLE data','SELECT randomblob(1000000000)','WITH x AS (SELECT 1) DELETE FROM data']:
        assert sql_result(query,TABLE)['status']!='ok'
    assert sql_result('SELECT * FROM data',TABLE,max_rows=1)['status']=='row_limit'
    assert sql_compare('SELECT bad FROM data','SELECT absent FROM data',TABLE)['status']=='reference_failed'

def test_sql_empty_match_is_explicitly_weak():
    result=sql_compare('SELECT name FROM data WHERE value>100','SELECT name FROM data WHERE value>50',TABLE)
    assert result['status']=='match' and result['empty_reference_result']

def test_arithmetic_checks_only_explicit_equalities():
    assert arithmetic('(24-6)/3')==6
    for expr in ['__import__("os")','2**100000','a+2']:
        with pytest.raises(ValueError):arithmetic(expr)
    r=error_tags({'source':'gsm8k','generated':'<<24-1=21>> <<3*4=12>>','expected':'18','correct':False})
    assert r['arithmetic_equalities_checked']==2 and r['arithmetic_equalities_wrong']==1
    assert 'answer_mismatch_cause_unresolved' in r['tags']

def test_format_does_not_rescue_correct_label_inside_wrong_answer():
    assert label_diagnostic('boolq','Answer: Yes.')=='yes'
    assert label_diagnostic('boolq','No, but yes is also possible') is None
    assert wilson(4,6)[0]<.31 and wilson(4,6)[1]>.90

def test_sample_is_order_independent_and_groups_unique():
    rows=[dict(source='s',group=str(i),original_id=str(i),prompt='x') for i in range(10)]
    a={};b={}
    for r in rows:retain(a,r,3)
    for r in reversed(rows):retain(b,r,3)
    assert a==b and len(a)==3

def test_sample_overlap_is_verified():
    text=' '.join('word'+str(i) for i in range(80))
    train=[dict(source='a',original_id='1',prompt=text)]
    dev=[dict(source='b',original_id='2',prompt=text+' end')]
    assert near_duplicates(train,dev)[0]['jaccard']>.98
    assert near_duplicates(train,[dict(source='b',original_id='3',prompt=' '.join('other'+str(i) for i in range(80)))])==[]

def test_queue_never_starts_before_completed_campaign(tmp_path,monkeypatch):
    from slm_perf import __main__ as cli
    monkeypatch.setattr(cli,'active_jobs',lambda:[])
    assert not ready(tmp_path)
    (tmp_path/'status.json').write_text('{"status":"running"}')
    assert not ready(tmp_path)
    (tmp_path/'status.json').write_text('{"status":"completed"}')
    assert ready(tmp_path)
    monkeypatch.setattr(cli,'active_jobs',lambda:[123])
    assert not ready(tmp_path)
    with pytest.raises(RuntimeError):validate({'sha256':{str(tmp_path/'status.json'):'wrong'}})

def test_offline_analysis_launcher_keeps_monitoring():
    from run_slm import command
    args=command(['--module','future_eval.analyze','--run','runs/example'])
    assert args[args.index('--mode')+1]=='light'

def test_idle_preparation_end_to_end_with_tiny_original_train_fixture(tmp_path):
    import hashlib,time
    import pyarrow as pa
    import pyarrow.parquet as pq
    from tokenizers import Tokenizer,models,pre_tokenizers
    from .prepare import prepare
    pa.set_cpu_count(1)
    base=tmp_path/'data/v3-broad';base.mkdir(parents=True)
    tok=Tokenizer(models.WordLevel({'[UNK]':0},unk_token='[UNK]'));tok.pre_tokenizer=pre_tokenizers.Whitespace()
    tok.save(str(base/'tokenizer.json'));(base/'manifest.json').write_text('{}')
    raw={'table':dict(TABLE,rows=[[str(v) for v in row] for row in TABLE['rows']]),'question':'names over one'}
    uid=hashlib.sha256(json.dumps(raw,sort_keys=True).encode()).hexdigest()
    sql=dict(source='wikisql',original_id=uid,group='sql-dev',split='dev',original_split='train',prompt='SQL names over one',answer='SELECT name FROM data WHERE value>1')
    rows=[sql]+[dict(source='boolq',original_id=str(i),group='g'+str(i),split='train' if i<3 else 'dev',original_split='train',prompt='question '+str(i),answer='yes' if i<2 else 'no') for i in range(4)]
    (base/'records.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    stage=base.parent/'candidates-wave3-2026-09-07';path=stage/'raw/wikisql/train/tiny.parquet';path.parent.mkdir(parents=True)
    pq.write_table(pa.Table.from_pylist([raw]),path)
    (stage/'manifest.json').write_text(json.dumps({'sources':{'wikisql':{'original_split':'train','files':[{'path':'train/tiny.parquet','sha256':hashlib.sha256(path.read_bytes()).hexdigest()}]}}}))
    suite=tmp_path/'suite.json';suite.write_text(json.dumps({'general':[sql],'code':[],'tokenizer_sha256':hashlib.sha256((base/'tokenizer.json').read_bytes()).hexdigest()}))
    out=tmp_path/'out';out.mkdir();prepare(base,out,suite,time.time()+10,per_source=2)
    result=json.loads((out/'audit.json').read_text())
    assert result['majority']['boolq']=='yes'
    assert result['label_counts']['boolq']=={'yes':2,'no':1}
    assert set(result['selected_per_source'])=={'boolq','wikisql'}
    assert uid in json.loads((out/'wikisql-tables.json').read_text())

def test_only_lightweight_modules_can_bypass_gpu_admission(monkeypatch):
    from types import SimpleNamespace
    from slm_perf import __main__ as cli
    monkeypatch.setattr(cli,'active_jobs',lambda:[123])
    monkeypatch.setattr(cli,'launch_workload',lambda a:'called')
    assert cli.launch(SimpleNamespace(module='future_eval.analyze',mode='light'))=='called'
    with pytest.raises(RuntimeError):cli.launch(SimpleNamespace(module='future_eval.prepare',mode='light'))
