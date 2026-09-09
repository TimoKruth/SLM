"""Finite 24h supervisor. Failed experimental cells are recorded, never silently retried."""
import argparse
from datetime import datetime
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from research.common import read,write,sha,quality,contrast,parent_guard
from slm_perf.after_idle import stop_process
from .report import report,collect,effects
from .design import BASE
from .safety import RecoverableStop,failure_kind,archive_failed_output,retry_seconds

ROOT=Path(__file__).resolve().parents[1]


class StudyStop(RuntimeError):pass


def exposure_key(job):
    p=job['parameters']
    return tuple(str(v) for v in [job['phase'],job['repetition'],job['target_tokens'],p['microbatch']*p['accumulation'],
                                 p['train_context'],p['eligibility'],p['mixture'],p['boost_family']])


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',required=True);args=parser.parse_args()
    run=Path(args.run).resolve();plan=read(run/'plan.json')
    if (run/'STOP').exists():raise ValueError('Start blocked by STOP; no work launched')
    if (run/'status.json').exists():raise ValueError('One-shot campaign; budget cannot reset')
    started=time.time();cutoff=time.monotonic()+plan['budget_seconds']-15
    state=dict(status='running',phase='preparation',pid=os.getpid(),started=datetime.now().astimezone().isoformat(),
               deadline=datetime.fromtimestamp(started+plan['budget_seconds']).astimezone().isoformat(),stages=[])
    write(run/'status.json',state)
    stop=[]
    for sig in [signal.SIGINT,signal.SIGTERM]:signal.signal(sig,lambda n,f:stop.append(n))
    caffeine=subprocess.Popen(['/usr/bin/caffeinate','-is','-w',str(os.getpid())])
    frozen=read(run/'initial-inputs.json'); stamps={}
    def verify(full=False):
        for p,digest in frozen.items():
            if full and sha(p)!=digest:raise StudyStop('Frozen input changed: '+p)
            stamp=(Path(p).stat().st_size,Path(p).stat().st_mtime_ns)
            if p in stamps and stamps[p]!=stamp:raise StudyStop('Input changed during study: '+p)
            stamps[p]=stamp
    def run_attempt(name,module,model_run,args,seconds,cpu=False):
        if stop or (run/'STOP').exists():raise StudyStop('Requested stop')
        if time.monotonic()+seconds>cutoff:raise StudyStop('Global budget exhausted before complete next stage')
        verify()
        stage=dict(name=name,status='running',started=datetime.now().astimezone().isoformat(),timeout_seconds=seconds)
        state['phase']=name;state['stages'].append(stage);write(run/'status.json',state)
        if cpu:
            command=[sys.executable,'-u','-m',module,'--run',str(model_run),*args]
        else:
            command=[sys.executable,'-u',str(ROOT/'run_slm.py'),'--module',module,'--run',str(model_run),*args]
        process=None;begin=time.monotonic();success=False
        try:
            with (run/(name+'.log')).open('w') as log:
                process=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
                stage['pid']=process.pid;write(run/'status.json',state)
                while process.poll() is None:
                    if stop or (run/'STOP').exists():raise StudyStop('Requested stop')
                    if time.monotonic()>=cutoff:raise StudyStop('Global deadline reached')
                    if time.monotonic()-begin>=seconds:
                        stage['error']='Stage timeout';break
                    time.sleep(1)
                success=process.poll()==0
                stage['exit_code']=process.poll()
        finally:
            stop_process(process);stage['status']='completed' if success else 'failed'
            stage['cleanup_exit_code']=process.returncode if process is not None else None
            stage['elapsed_seconds']=time.monotonic()-begin;write(run/'status.json',state)
        if not success:
            stage['failure_kind']=failure_kind((run/(name+'.log')).read_text()[-131072:])
            write(run/'status.json',state)
        return success,stage
    consecutive_failures=0
    module_failures={}
    def run_job(name,module,model_run,args,seconds,cpu=False):
        nonlocal consecutive_failures
        begin=time.monotonic()
        success,stage=run_attempt(name,module,model_run,args,seconds,cpu)
        if success:
            consecutive_failures=0
            module_failures[module]=0
            return True
        kind=stage['failure_kind']
        if kind=='memory':raise RecoverableStop('Memory unavailable; remaining work retained')
        if kind=='gpu_service':
            # Fresh health process reopens Metal's connection; do not kill shared macOS services.
            attempts=state.get('gpu_recovery_attempts',0)
            if attempts>=2:raise RecoverableStop('Repeated GPU infrastructure failure; automatic recovery limit reached')
            state['gpu_recovery_attempts']=attempts+1
            available=retry_seconds(seconds,time.monotonic()-begin,cutoff-time.monotonic())
            if available<25:raise RecoverableStop('Insufficient remaining stage budget for GPU recovery')
            time.sleep(2)
            probe=run/'health-recovery'/str(attempts+1)
            healthy,_=run_attempt(name+'-health','study.health',probe,['--seconds','2'],20)
            if not healthy:raise RecoverableStop('GPU health check failed; no further trials started')
            archive_failed_output(run,module,model_run,args,name)
            remaining=retry_seconds(seconds,time.monotonic()-begin,cutoff-time.monotonic())
            if remaining<1:raise RecoverableStop('Stage budget exhausted during recovery')
            retry_args=list(args)
            if module=='study.trial':
                retry_args+=['--wall-seconds',str(remaining)]
            success,stage=run_attempt(name+'-retry1',module,model_run,retry_args,remaining,cpu)
            if not success and stage['failure_kind'] in ['gpu_service','memory']:
                raise RecoverableStop('GPU recovery did not remain stable; remaining work retained')
            if success:
                consecutive_failures=0
                module_failures[module]=0
                return True
        consecutive_failures+=1
        module_failures[module]=module_failures.get(module,0)+1
        if consecutive_failures>=3 or module_failures[module]>=3:
            raise RecoverableStop('Three consecutive failures overall or in one stage type; stopped for diagnosis')
        return False
    def evaluate(model_run,label,suite='search'):
        seconds=plan[suite+'_seconds'];process_seconds=plan[suite+'_process_seconds']
        output=run/('parent-'+suite) if model_run==Path(plan['parent']) else model_run/suite
        if plan.get('reuse_completed') and (output/'summary.json').exists():
            from .recovery import valid_evaluation
            if not valid_evaluation(output,model_run,run/(suite+'-suite.json')):
                raise StudyStop('Imported evaluation failed provenance check: '+str(output))
            state.setdefault('reused_evaluations',[]).append(label);write(run/'status.json',state)
            return quality(read(output/'summary.json'))
        ok=run_job(label,'slm.broad_eval',model_run,
              ['--suite',str(run/(suite+'-suite.json')),'--output',str(output),'--checkpoint','latest',
               '--maximum','256','--max-seconds',str(seconds),'--skip-code','--answer-loss'],process_seconds)
        if not ok:return None
        try:return quality(read(output/'summary.json'))
        except (ValueError,KeyError,OSError):return None
    known_exposure={}
    def train(job):
        jobfile=run/'jobs'/(job['id']+'.json');trial=run/'trials'/job['id']
        saved=plan.get('reuse_completed') and (trial/'result.json').exists()
        if saved:
            from .recovery import valid_trial
            if not valid_trial(trial,job):raise StudyStop('Imported training failed validation: '+job['id'])
            state.setdefault('reused_training',[]).append(job['id']);write(run/'status.json',state)
        elif not run_job(job['id'],'study.trial',trial,['--plan',str(run/'plan.json'),'--job',str(jobfile)],job['train_seconds']):return False
        r=read(trial/'result.json')
        if r['status']!='completed':return False
        key=exposure_key(job);signature=[r[k] for k in ['additional_tokens','additional_steps','source_tokens','batches_sha256','initial_sampler','final_sampler']]
        if key in known_exposure and known_exposure[key]!=signature:raise StudyStop('Matched exposure verification failed: '+job['id'])
        known_exposure[key]=signature
        evaluate(trial,job['id']+'-search');report(run,state)
        return True
    try:
        verify(full=True)
        if not plan.get('reuse_completed'):
            if not run_job('prepare-suites','study.prepare',run,['--suites-only'],plan['preparation_seconds'],cpu=True):raise StudyStop('Preparation failed')
        frozen=read(run/'frozen-inputs.json');verify(full=True)
        if not run_job('health-start','study.health',run/'health-start',['--seconds','3'],20):raise RecoverableStop('GPU preflight failed')
        if not run_job('controls','study.trial',run/'controls',['--plan',str(run/'plan.json'),'--control-only'],plan['control_seconds']):raise StudyStop('GPU control failed')
        if not read(run/'controls/control.json')['passed']:raise StudyStop('Control not passed')
        parent=evaluate(Path(plan['parent']),'parent-search')
        if parent is None:raise StudyStop('Parent evaluation incomplete')
        write(run/'parent-quality.json',parent)
        for identifier in plan['jobs']:train(read(run/'jobs'/(identifier+'.json')))
        rows=collect(run);contrasts=effects(rows,parent)
        eligible={k:v for k,v in contrasts.items() if v['phase']=='adaptation' and v['block']=='adaptation'}
        if not eligible:raise StudyStop('No complete paired adaptation comparison available')
        chosen=max(eligible,key=lambda k:(eligible[k]['passes_screen'],eligible[k]['mean_accuracy_delta'],-eligible[k]['mean_answer_loss_delta']))
        contender=chosen.split(':',1)[1]
        candidate=next(v['job']['parameters'] for v in rows.values() if v['job']['phase']=='adaptation' and v['job']['name']==contender)
        write(run/'selection.json',dict(contender=contender,search_passed=eligible[chosen]['passes_screen'],contrast=eligible[chosen],
                                        criterion=plan['selection'],selected_before_confirmation=True))
        for repetition in range(2):
            for name,parameters in [('baseline',BASE),(contender,candidate)]:
                job=dict(id=f'long-r{repetition}-{name}',name=name,phase='long',block='long',parameters=parameters,
                         repetition=repetition,data_seed=202609501+repetition,model_seed=202609701+repetition,
                         target_tokens=plan['long_target_tokens'],train_seconds=plan['long_train_seconds'],snapshot_tokens=[1500000])
                write(run/'jobs'/(job['id']+'.json'),job)
                if train(job):
                    snapshot=run/'trials'/job['id']/'token-001500000'
                    if snapshot.exists():evaluate(snapshot,job['id']+'-snapshot-search')
        parent_confirmation=evaluate(Path(plan['parent']),'parent-confirmation','confirmation')
        if parent_confirmation is None:raise StudyStop('Parent confirmation incomplete')
        confirmation={}
        for repetition in range(2):
            for name in ['baseline',contender]:
                trial=run/'trials'/f'long-r{repetition}-{name}'
                if not (trial/'result.json').exists() or read(trial/'result.json')['status']!='completed':raise StudyStop('Long trial incomplete')
                q=evaluate(trial,trial.name+'-confirmation','confirmation')
                if q is None:raise StudyStop('Long confirmation incomplete')
                confirmation[repetition,name]=q
        result=contrast([confirmation[r,'baseline'] for r in range(2)],[confirmation[r,contender] for r in range(2)])
        result['parent_guard']=parent_guard(parent_confirmation,[confirmation[r,contender] for r in range(2)])
        result['confirmed_candidate']=eligible[chosen]['passes_screen'] and result['passes_screen'] and result['parent_guard']['passed']
        result['contender']=contender
        write(run/'confirmation.json',result)
        state.update(status='completed' if all(s['status']=='completed' for s in state['stages']) else 'completed_with_failures',phase='finished')
    except RecoverableStop as exc:
        state.update(status='paused_infrastructure',error=repr(exc))
        (run/'STOP').write_text('Infrastructure pause; explicit resume required.\n')
        write(run/'PAUSE.json',dict(reason=str(exc),automatic_restart=False))
    except BaseException as exc:state.update(status='stopped',error=repr(exc))
    finally:
        stop_process(caffeine)
        state.update(finished=datetime.now().astimezone().isoformat(),elapsed_seconds=time.time()-started)
        state['total_budget_spent_seconds']=plan.get('previous_budget_spent_seconds',0)+state['elapsed_seconds']
        try:verify(full=True);state['frozen_inputs_unchanged']=True
        except BaseException as exc:state.update(status='invalid',error=repr(exc),frozen_inputs_unchanged=False)
        write(run/'status.json',state);report(run,state)
    if state['status'] not in ['completed','completed_with_failures']:raise SystemExit(1)


if __name__=='__main__':main()
