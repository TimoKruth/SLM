"""Prepare a new immutable evaluation plan without loading a model or starting inference."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
from .settings import Settings
from .tasks import load_tasks, input_text

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(8*1024**2), b''):
            h.update(block)
    return h.hexdigest()


def write(path, value):
    path = Path(path)
    temp = path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')
    temp.replace(path)


def prepare(profile, suite, output, model_dir=None, checkpoint=None, metadata=None,
            ollama_binary='/Applications/Ollama.app/Contents/Resources/ollama',
            ollama_models=None):
    settings = Settings.load(profile)
    tasks = load_tasks(suite)
    output = Path(output).resolve()
    if output.exists():
        raise ValueError('Use a new plan directory; historical results are immutable')
    inputs = {str(Path(x).resolve()):sha(x) for x in [profile, suite]}
    for folder in ['benchmark_eval', 'slm', 'slm_perf', 'benchmark_expansion']:
        for path in (ROOT/folder).glob('*.py'):
            inputs[str(path)] = sha(path)
    inputs[str(ROOT/'run_defaults.json')] = sha(ROOT/'run_defaults.json')
    plan = dict(version=1, created=datetime.now().astimezone().isoformat(), settings=settings.to_dict(),
                suite=str(Path(suite).resolve()), inputs=inputs, tasks=len(tasks),
                official_artificial_analysis_score=False, started=False,
                note='Changed answer contracts; results are a new protocol, not comparable to historical scores.')
    if settings.backend == 'slm':
        if model_dir is None or checkpoint is None:
            raise ValueError('SLM requires explicit --model-dir and --checkpoint')
        model_dir = Path(model_dir).resolve()
        config_path = model_dir/'config.json'
        config = json.loads(config_path.read_text())
        if settings.context_tokens != config['model']['context']:
            raise ValueError('Context must equal the checkpoint training configuration; no inference-only context extension')
        checkpoint = Path(checkpoint).resolve()
        tokenizer_path = model_dir/'tokenizer.json'
        for path in [config_path, tokenizer_path, checkpoint]:
            inputs[str(path)] = sha(path)
        from tokenizers import Tokenizer
        tok = Tokenizer.from_file(str(tokenizer_path))
        allocations = [settings.allocation(len(tok.encode('<bos><question>\n'+input_text(t)+'\n<answer>\n').ids)) for t in tasks]
        plan.update(model_dir=str(model_dir), checkpoint=str(checkpoint),
                    preflight=dict(token_count_method='exact SLM tokenizer including contract/wrapper',
                        supported=sum(a['supported'] for a in allocations),
                        rejected=sum(not a['supported'] for a in allocations),
                        output_reduced=sum(a['output_reduced_by_context'] for a in allocations),
                        minimum_output_tokens=min(a['effective_output_tokens'] for a in allocations),
                        maximum_output_tokens=max(a['effective_output_tokens'] for a in allocations)))
    else:
        if metadata is None:
            raise ValueError('Ollama requires captured --metadata from /api/show (no model loading needed)')
        meta = json.loads(Path(metadata).read_text())
        contexts = [v for k,v in meta['model_info'].items() if k.endswith('.context_length')]
        if not contexts or settings.context_tokens > min(contexts):
            raise ValueError('Requested context exceeds local model metadata')
        # Byte-fallback tokenizers: conservative input allowance, with template safety margin.
        # Unsupported models must get a dedicated exact-tokenizer adapter.
        if meta.get('details', {}).get('family') != 'qwen35':
            raise ValueError('Only the audited local qwen35 tokenizer/template family is supported')
        overhead = len(meta.get('template','').encode()) + len(meta.get('system','').encode()) + 4096
        allocations = [settings.allocation(len(input_text(t).encode())+overhead) for t in tasks]
        home = Path(ollama_models or Path.home()/'.ollama/models').resolve()
        tag = settings.model
        namespace, name = tag.rsplit('/',1) if '/' in tag else ('library',tag)
        name, version = name.rsplit(':',1) if ':' in name else (name,'latest')
        manifest = home/'manifests/registry.ollama.ai'/namespace/name/version
        manifest = manifest.resolve()
        if not manifest.is_relative_to(home):
            raise ValueError('Model path outside Ollama model directory')
        inventory = json.loads(manifest.read_text())
        blobs = {}
        for layer in [inventory['config'], *inventory['layers']]:
            digest = layer['digest']
            if not digest.startswith('sha256:') or len(digest)!=71:
                raise ValueError('Invalid model blob digest')
            blobs[str(home/'blobs'/digest.replace(':','-'))] = digest[7:]
        binary = Path(ollama_binary).resolve()
        for path in [Path(metadata).resolve(), manifest, binary]:
            inputs[str(path)] = sha(path)
        plan.update(ollama_binary=str(binary), ollama_models=str(home), model_blobs=blobs,
                    model_manifest_sha256=sha(manifest), metadata=str(Path(metadata).resolve()),
                    prompt_overhead_bound=overhead,
                    preflight=dict(token_count_method='conservative UTF-8 byte bound plus template and 4096-token reserve; checked against runtime counts',
                        supported=sum(a['supported'] for a in allocations), rejected=sum(not a['supported'] for a in allocations),
                        output_reduced=sum(a['output_reduced_by_context'] for a in allocations)))
    output.mkdir(parents=True)
    write(output/'plan.json',plan)
    (output/'PREPARED.txt').write_text('Preparation only. Explicit --start, plan hash and wall budget required. No inference started.\n')
    return dict(plan_sha256=sha(output/'plan.json'), **plan['preflight'], tasks=len(tasks), started=False)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['profile','suite','output']:
        p.add_argument('--'+name,required=True)
    for name in ['model-dir','checkpoint','metadata','ollama-binary','ollama-models']:
        p.add_argument('--'+name)
    a = vars(p.parse_args())
    if a['ollama_binary'] is None:
        del a['ollama_binary']
    print(json.dumps(prepare(**a), indent=2))


if __name__ == '__main__':
    main()
