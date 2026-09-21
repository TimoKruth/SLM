"""Persistent local backends. Only explicitly started runner imports device code."""
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
import urllib.request
import psutil
from .settings import Settings
from .tasks import prompt_for, input_text


def stop_process(process, known_children=()):
    if process is None:
        return
    descendants = {p.pid:p for p in known_children}
    if process.poll() is None:
        try:
            descendants.update({p.pid:p for p in psutil.Process(process.pid).children(recursive=True)})
        except psutil.NoSuchProcess:
            pass
    descendants = list(descendants.values())
    for child in descendants:
        try:
            child.terminate()
        except psutil.NoSuchProcess:
            pass
    if process.poll() is None:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    _, alive = psutil.wait_procs(descendants, timeout=2)
    for child in alive:
        try:
            child.kill()
        except psutil.NoSuchProcess:
            pass
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=2)


class OwnedBackend:
    def observe(self):
        if self.process is not None and self.process.poll() is None:
            try:
                self.children.update({p.pid:p for p in psutil.Process(self.process.pid).children(recursive=True)})
            except psutil.NoSuchProcess:
                pass

    def close(self):
        self.observe()
        stop_process(self.process, list(self.children.copy().values()))


class Ollama(OwnedBackend):
    def __init__(self, plan, run, lease):
        self.plan, self.run = plan, run
        self.settings = Settings(**plan['settings'])
        self.process = None
        self.children = {}
        self.options = lease.child_options()
        self.url = 'http://127.0.0.1:11440'
        self.residency_checked = False

    def api(self, endpoint, payload=None):
        data = None if payload is None else json.dumps(payload).encode()
        req = urllib.request.Request(self.url+'/api/'+endpoint, data=data, headers={'Content-Type':'application/json'})
        # The independent runner watchdog enforces absolute task/run deadlines and kills owned inference.
        with urllib.request.urlopen(req, timeout=self.settings.task_seconds+30) as response:
            return json.load(response)

    def start(self):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',11440))
        self.options['env'].update(OLLAMA_HOST='127.0.0.1:11440', OLLAMA_MODELS=self.plan['ollama_models'],
            OLLAMA_CONTEXT_LENGTH=str(self.settings.context_tokens), OLLAMA_NUM_PARALLEL='1',
            OLLAMA_MAX_LOADED_MODELS='1', OLLAMA_NO_CLOUD='1')
        with (self.run/'ollama.log').open('x') as log:
            self.process = subprocess.Popen([self.plan['ollama_binary'],'serve'], stdin=subprocess.DEVNULL,
                stdout=log, stderr=subprocess.STDOUT, start_new_session=True, **self.options)
        until = time.monotonic()+60
        while time.monotonic()<until:
            if self.process.poll() is not None:
                raise RuntimeError('Owned Ollama server exited')
            try:
                self.api('version')
                break
            except OSError:
                time.sleep(.1)
        else:
            raise TimeoutError('Ollama did not become ready')
        tags = self.api('tags')['models']
        matches = [m for m in tags if m['name']==self.settings.model and m['digest']==self.plan['model_manifest_sha256']]
        if len(matches)!=1:
            raise ValueError('Runtime model tag/digest mismatch')
        meta = self.api('show',dict(model=self.settings.model))
        old = json.loads(Path(self.plan['metadata']).read_text())
        for key in ['model_info','template','system','parameters','capabilities']:
            if meta.get(key)!=old.get(key):
                raise ValueError('Runtime metadata changed: '+key)

    def generate(self, task):
        s = self.settings
        prompt = prompt_for(task)
        allocation = s.allocation(len(input_text(task).encode())+self.plan['prompt_overhead_bound'])
        if not allocation['supported']:
            return dict(text='', stop_reason='unsupported_context', allocation=allocation)
        messages = ([dict(role='system',content=task['system'])] if task.get('system') else []) + [dict(role='user',content=prompt)]
        payload = dict(model=s.model, messages=messages, stream=False,
                       think=s.thinking, keep_alive='30m',
                       options=dict(num_ctx=s.context_tokens, num_predict=allocation['effective_output_tokens'],
                                    temperature=s.temperature, seed=s.seed))
        raw = self.api('chat',payload)
        if not raw.get('done') or raw.get('error') or raw.get('done_reason') not in {'stop','length'}:
            raise ValueError('Incomplete or invalid Ollama response')
        message = raw.get('message',{})
        if not isinstance(message.get('content'),str) or message.get('tool_calls'):
            raise ValueError('Unsupported tool response or missing content')
        if not s.thinking and (message.get('thinking') or '<think>' in message['content']):
            raise ValueError('Model ignored non-reasoning setting')
        count = raw.get('prompt_eval_count')
        generated = raw.get('eval_count')
        if type(count) is not int or count<=0 or type(generated) is not int or not 0<=generated<=allocation['effective_output_tokens']:
            raise ValueError('Invalid token accounting')
        if count > allocation['prompt_tokens'] or count+allocation['effective_output_tokens']>s.context_tokens:
            raise ValueError('Runtime input exceeded conservative context admission; results invalid')
        if not self.residency_checked:
            residency = self.api('ps')
            resident = [m for m in residency.get('models',[]) if m['name']==s.model]
            if len(resident)!=1 or resident[0].get('context_length')!=s.context_tokens:
                raise ValueError('Runtime context allocation does not match the profile')
            if resident[0].get('digest')!=self.plan['model_manifest_sha256']:
                raise ValueError('Resident model digest mismatch')
            (self.run/'residency.json').write_text(json.dumps(residency,indent=2)+'\n')
            self.residency_checked = True
        return dict(text=message['content'], thinking=message.get('thinking',''),
                    stop_reason='output_limit' if raw['done_reason']=='length' else 'eos',
                    allocation=allocation, actual_prompt_tokens=count, generated_tokens=generated,
                    raw=raw)


class SLM(OwnedBackend):
    def __init__(self, plan, run, lease):
        self.plan, self.run = plan, run
        self.options = lease.child_options()
        self.process = None
        self.children = {}

    def start(self):
        with (self.run/'worker.log').open('x') as log:
            self.process = subprocess.Popen([sys.executable,'-m','benchmark_eval.backends',str(self.run/'plan.json')],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log, text=True, bufsize=1,
                start_new_session=True, **self.options)

    def generate(self, task):
        self.process.stdin.write(json.dumps(dict(prompt=input_text(task)))+'\n')
        self.process.stdin.flush()
        line = self.process.stdout.readline()
        if not line:
            raise RuntimeError('SLM worker exited; inspect local worker.log')
        result = json.loads(line)
        if 'error' in result:
            raise RuntimeError(result['error'])
        return result


def slm_worker(path):
    plan = json.loads(Path(path).read_text())
    s = Settings(**plan['settings'])
    # No MLX/device imports in preparation, scoring, or report code.
    import mlx.core as mx
    from tokenizers import Tokenizer
    from slm.model import LanguageModel, ModelConfig
    from slm.inference import greedy_generate
    config = json.loads((Path(plan['model_dir'])/'config.json').read_text())['model']
    if config['context'] != s.context_tokens:
        raise ValueError('Checkpoint context cannot be overridden')
    mx.set_default_device(mx.gpu)
    mx.set_memory_limit(12*1024**3)
    mx.set_cache_limit(512*1024**2)
    model = LanguageModel(ModelConfig(**config))
    model.load_weights(plan['checkpoint'])
    model.eval()
    tok = Tokenizer.from_file(str(Path(plan['model_dir'])/'tokenizer.json'))
    for line in sys.stdin:
        prompt = json.loads(line)['prompt']
        count = len(tok.encode('<bos><question>\n'+prompt+'\n<answer>\n').ids)
        allocation = s.allocation(count)
        if not allocation['supported']:
            result = dict(text='',stop_reason='unsupported_context',allocation=allocation)
        else:
            raw = greedy_generate(model,tok,prompt,allocation['effective_output_tokens'])
            reason = raw['stop_reason']
            if reason == 'token_limit':
                reason = 'context_limit' if allocation['output_reduced_by_context'] else 'output_limit'
            elif reason == 'special_token':
                reason = 'eos'
            result = dict(text=raw['generated'], stop_reason=reason, allocation=allocation,
                          actual_prompt_tokens=count, generated_tokens=raw['generated_tokens'])
        print(json.dumps(result),flush=True)


if __name__ == '__main__':
    slm_worker(sys.argv[1])
