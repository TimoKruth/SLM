import json
import time
from contextlib import nullcontext
from pathlib import Path
import pytest
from benchmark_eval.settings import Settings
from benchmark_eval.tasks import prompt_for, extract, grade, load_tasks, validate_task
from benchmark_eval.prepare import prepare, sha
from benchmark_eval.runner import summarize
from benchmark_eval.backends import Ollama


def task(**changes):
    return dict(dict(id='1',source='synthetic',kind='choice',prompt='Choose the even number.',choices=['3','4'],reference='B'),**changes)


def test_16k_output_is_independent_of_context():
    s=Settings(backend='ollama',model='test',context_tokens=32768)
    assert s.allocation(100)['effective_output_tokens']==16384
    assert s.allocation(16385)['supported'] is False
    assert s.allocation(32768)['effective_output_tokens']==0


def test_slm_remaining_context_is_explicit():
    s=Settings(backend='slm',context_tokens=1024,context_policy='use_remaining')
    a=s.allocation(300)
    assert a['effective_output_tokens']==724 and a['output_reduced_by_context']
    assert not s.allocation(1000)['supported']
    with pytest.raises(ValueError):
        Settings(backend='slm',context_tokens=32768,thinking=True)


@pytest.mark.parametrize('change',[{'max_output_tokens':0},{'task_seconds':0},{'temperature':float('nan')},{'thinking':'false'},{'context_policy':'truncate'}])
def test_invalid_settings_rejected(change):
    with pytest.raises(ValueError):
        Settings(**dict(dict(backend='slm',context_tokens=1024),**change))


def test_prompt_and_extraction_do_not_depend_on_reference():
    a=task();b=task(reference='A')
    assert prompt_for(a)==prompt_for(b)
    text='An explanation involving A and B.\nFinal answer: B'
    assert grade(a,text)==dict(status='correct',correct=True)
    assert grade(b,text)==dict(status='incorrect',correct=False)
    assert grade(a,'The answer might be B or A.')['correct'] is False


@pytest.mark.parametrize('text',['Final answer: A\nFinal answer: B','Final answer: B\nMore prose','Reasoning\nwithout final answer','Final answer:'])
def test_ambiguous_or_missing_final_answer_not_repaired(text):
    assert grade(task(),text)['correct'] is False


def test_numeric_equivalence_without_eval():
    t=task(kind='number',reference='4')
    assert grade(t,'Reasoning\nFinal answer: 4.00')['correct']
    assert grade(t,'Final answer: 40')['correct'] is False
    assert grade(t,'Final answer: __import__("os")')['status']=='format_error'
    assert grade(t,'Final answer: 4 meters')['status']=='format_error'


def test_external_grader_is_never_claimed_correct():
    t=task(kind='external')
    assert prompt_for(t)==t['prompt']
    assert grade(t,'working code')['correct'] is None
    assert grade(t,'working code')['status']=='unscored_external_grader_required'


def test_legacy_answer_contract_with_explanation():
    row=dict(source='anli',original_id='x',prompt='Label the relation.',answer='contradiction')
    t=dict(id='x',source='anli',kind='legacy_proxy',prompt=row['prompt'],reference=row['answer'],legacy=row)
    assert grade(t,'The statements conflict.\nFinal answer: contradiction')['correct']
    assert not grade(t,'The statements conflict.\nFinal answer: neutral')['correct']


def test_legacy_math_format_adaptation():
    row=dict(source='gsm8k',original_id='x',prompt='Compute.',answer='Calculation.\n#### 21')
    t=dict(id='x',source='gsm8k',kind='legacy_proxy',prompt=row['prompt'],reference=row['answer'],legacy=row)
    assert grade(t,'Calculation\nFinal answer: 21')['correct']
    assert not grade(t,'Calculation\nFinal answer: 20')['correct']


def test_duplicate_and_tool_tasks_rejected(tmp_path):
    path=tmp_path/'suite.json';path.write_text(json.dumps([task(),task()]))
    with pytest.raises(ValueError,match='duplicate'):
        load_tasks(path)
    with pytest.raises(ValueError,match='text-only'):
        validate_task(task(requires_tools=True))


def test_partial_and_external_summary_has_no_fake_index():
    results=[dict(source='synthetic',stop_reason='output_limit',grade=dict(status='format_error',correct=False)),
             dict(source='code',stop_reason='eos',grade=dict(status='unscored_external_grader_required',correct=None))]
    s=summarize(dict(tasks=3),results,'incomplete')
    assert not s['generation_coverage_complete'] and s['full_suite_accuracy'] is None
    assert s['by_source']['synthetic']['format_errors']==1
    assert s['by_source']['code']['scored']==0
    assert not summarize(dict(tasks=1),[dict(source='s',stop_reason='unsupported_context',grade=dict(status='unscored_unsupported_context',correct=None))],'completed')['generation_coverage_complete']


def test_checkpoint_context_extension_is_rejected_before_loading(tmp_path):
    profile=tmp_path/'profile.json';profile.write_text(json.dumps(dict(backend='slm',context_tokens=32768)))
    suite=tmp_path/'suite.json';suite.write_text(json.dumps([task()]))
    model=tmp_path/'model';model.mkdir();(model/'config.json').write_text(json.dumps(dict(model=dict(context=1024))))
    with pytest.raises(ValueError,match='training configuration'):
        prepare(profile,suite,tmp_path/'out',model_dir=model,checkpoint=tmp_path/'missing')
    assert not (tmp_path/'out').exists()


def test_qwen_request_and_limits(tmp_path):
    class Lease:
        def child_options(self):return {'env':{}}
    p=dict(settings=Settings(backend='ollama',model='test',context_tokens=32768).to_dict(),prompt_overhead_bound=4096,model_manifest_sha256='digest')
    b=Ollama(p,tmp_path,Lease())
    calls=[]
    def api(endpoint,payload=None):
        if endpoint=='ps':return dict(models=[dict(name='test',context_length=32768,digest='digest')])
        calls.append(payload)
        return dict(done=True,done_reason='length',message=dict(content='unfinished'),prompt_eval_count=100,eval_count=16384)
    b.api=api
    answer=b.generate(task())
    assert calls[0]['options']['num_predict']==16384
    assert calls[0]['options']['num_ctx']==32768
    assert calls[0]['keep_alive']=='30m' and calls[0]['think'] is False
    assert answer['stop_reason']=='output_limit'
    b.api=lambda *_:dict(done=True,done_reason='stop',message=dict(content='B'),prompt_eval_count=32000,eval_count=1)
    with pytest.raises(ValueError,match='context admission'):
        b.generate(task())


def minimal_run(tmp_path):
    suite=tmp_path/'suite.json';suite.write_text(json.dumps([task()]))
    run=tmp_path/'run';run.mkdir()
    plan=dict(settings=Settings(backend='slm',context_tokens=1024,context_policy='use_remaining').to_dict(),suite=str(suite),tasks=1,inputs={str(suite):sha(suite)})
    (run/'plan.json').write_text(json.dumps(plan))
    return run,sha(run/'plan.json')


def test_budget_guard_cancels_blocked_backend_and_keeps_partial(tmp_path,monkeypatch):
    from benchmark_eval import runner
    run,digest=minimal_run(tmp_path)
    closed=[]
    class Backend:
        def __init__(self,*_):pass
        def start(self):pass
        def generate(self,_):
            until=time.monotonic()+3
            while not closed and time.monotonic()<until:time.sleep(.01)
            raise RuntimeError('connection closed')
        def close(self):closed.append(True)
    monkeypatch.setattr(runner,'SLM',Backend)
    monkeypatch.setattr(runner,'admission',lambda:None)
    monkeypatch.setattr(runner,'GPULease',lambda:nullcontext(None))
    monkeypatch.setattr(runner.subprocess,'check_output',lambda *_,**__: 'AC Power')
    start=time.monotonic()
    with pytest.raises(RuntimeError):runner.execute(run,digest,1)
    assert time.monotonic()-start<3 and closed
    assert json.loads((run/'status.json').read_text())['status']=='paused'
    assert (run/'STOP').exists()
    assert json.loads((run/'summary.json').read_text())['attempted']==0
    with pytest.raises(ValueError,match='Existing or stopped'):
        runner.execute(run,digest,1)


def test_completed_mock_evaluation_durable_results(tmp_path,monkeypatch):
    from benchmark_eval import runner
    run,digest=minimal_run(tmp_path)
    class Backend:
        def __init__(self,*_):pass
        def start(self):pass
        def generate(self,_):return dict(text='Explanation\nFinal answer: B',stop_reason='eos')
        def close(self):pass
    monkeypatch.setattr(runner,'SLM',Backend)
    monkeypatch.setattr(runner,'admission',lambda:None)
    monkeypatch.setattr(runner,'GPULease',lambda:nullcontext(None))
    monkeypatch.setattr(runner.subprocess,'check_output',lambda *_,**__: 'AC Power')
    runner.execute(run,digest,30)
    summary=json.loads((run/'summary.json').read_text())
    assert summary['generation_coverage_complete']
    assert summary['by_source']['synthetic']['correct']==1
    assert len((run/'responses.jsonl').read_text().splitlines())==1
    assert not (run/'STOP').exists()


def test_system_prompt_preserved_and_context_counted(tmp_path):
    from benchmark_eval.tasks import input_text
    t=task(system='Use only the supplied passage.')
    assert input_text(t).startswith('System instructions:\nUse only the supplied passage.')
    class Lease:
        def child_options(self):return {'env':{}}
    p=dict(settings=Settings(backend='ollama',model='test',context_tokens=32768).to_dict(),prompt_overhead_bound=4096,model_manifest_sha256='digest')
    b=Ollama(p,tmp_path,Lease())
    calls=[]
    def api(endpoint,payload=None):
        if endpoint=='ps':return dict(models=[dict(name='test',context_length=32768,digest='digest')])
        calls.append(payload)
        return dict(done=True,done_reason='stop',message=dict(content='B'),prompt_eval_count=100,eval_count=1)
    b.api=api
    result=b.generate(t)
    assert calls[0]['messages'][0]==dict(role='system',content=t['system'])
    assert result['allocation']['prompt_tokens']==len(input_text(t).encode())+4096


@pytest.mark.parametrize('name',['qwen36','qwen38'])
def test_reasoning_profile_preserves_non_reasoning_reference(name):
    profiles=Path(__file__).resolve().parents[2]/'benchmark_eval/profiles'
    reasoning=Settings.load(profiles/(name+'-reasoning.json'))
    reference=Settings.load(profiles/(name+'.json'))
    assert reasoning.model==reference.model
    assert reasoning.thinking and not reference.thinking
    assert reasoning.context_tokens==65536 and reasoning.max_output_tokens==32768
    assert reasoning.temperature==0.6 and reasoning.task_seconds==7200
    assert reference.context_tokens==32768 and reference.max_output_tokens==16384
    assert reasoning.allocation(4096)['supported']


@pytest.mark.parametrize('truncated',[False,True])
def test_reasoning_channel_is_saved_but_never_used_as_the_answer(tmp_path,truncated):
    class Lease:
        def child_options(self):return {'env':{}}
    s=Settings(backend='ollama',model='test',context_tokens=65536,max_output_tokens=32768,
               temperature=0.6,thinking=True,task_seconds=7200)
    plan=dict(settings=s.to_dict(),prompt_overhead_bound=4096,model_manifest_sha256='digest')
    b=Ollama(plan,tmp_path,Lease())
    calls=[]
    def api(endpoint,payload=None):
        if endpoint=='ps':return dict(models=[dict(name='test',context_length=65536,digest='digest')])
        calls.append(payload)
        return dict(done=True,done_reason='length' if truncated else 'stop',
                    message=dict(thinking='Final answer: B',content='' if truncated else 'Final answer: A'),
                    prompt_eval_count=100,eval_count=32768 if truncated else 100)
    b.api=api
    result=b.generate(task())
    assert calls[0]['think'] is True
    assert calls[0]['options']['num_predict']==32768
    assert calls[0]['options']['num_ctx']==65536
    assert calls[0]['options']['temperature']==0.6
    assert result['thinking']=='Final answer: B'
    assert not grade(task(),result['text'])['correct']
    assert result['stop_reason']==('output_limit' if truncated else 'eos')
    assert result['generated_tokens']==(32768 if truncated else 100)
