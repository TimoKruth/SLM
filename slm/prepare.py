"""Fetch pinned original train splits; build grouped holdouts and a train-only tokenizer."""
import ast
import hashlib
import json
import re
import zipfile
import warnings
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import urlopen

import numpy as np
import pyarrow.parquet as pq
from huggingface_hub import hf_hub_download
from tokenizers import Tokenizer, models, trainers, pre_tokenizers, decoders

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
SPECIAL = ['<pad>', '<bos>', '<eos>', '<question>', '<answer>']
SOURCES = {
    'apps': ('codeparrot/apps', ['train.jsonl']),
    'mbpp': ('google-research-datasets/mbpp', ['full/train-00000-of-00001.parquet']),
    'gsm8k': ('openai/gsm8k', ['main/train-00000-of-00001.parquet']),
    'math': ('EleutherAI/hendrycks_math', None),
    'squad': ('rajpurkar/squad', ['plain_text/train-00000-of-00001.parquet']),
    'boolq': ('google/boolq', ['data/train-00000-of-00001.parquet']),
    'hellaswag': ('Rowan/hellaswag', ['data/train-00000-of-00001.parquet']),
    'winogrande': ('allenai/winogrande', ['winogrande_xl/train-00000-of-00001.parquet']),
    'arc': ('allenai/ai2_arc', ['ARC-Easy/train-00000-of-00001.parquet', 'ARC-Challenge/train-00000-of-00001.parquet']),
}


def digest(s):
    return hashlib.sha256(s.encode() if isinstance(s, str) else s).hexdigest()


def normal(s):
    return re.sub(r'\s+', ' ', s).strip().lower()


def partition(group):
    return 'dev' if int(digest('pilot-v1:' + group)[:8], 16) % 100 < 5 else 'train'


def text_of(row):
    return '<bos><question>\n' + row['prompt'] + '\n<answer>\n' + row['answer'] + '<eos>\n'


def code_key(answer):
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', SyntaxWarning)
            return digest(ast.dump(ast.parse(answer), include_attributes=False))
    except (SyntaxError, ValueError, TypeError):
        return None


def exclude_shared_code_groups(rows):
    train_keys = {code_key(r['answer']) for r in rows if r['split'] == 'train' and r['source'] in ['apps', 'mbpp']}
    train_keys.discard(None)
    bad_groups = {r['group'] for r in rows if r['split'] == 'dev' and r['source'] in ['apps', 'mbpp'] and code_key(r['answer']) in train_keys}
    removed = [r for r in rows if r['split'] == 'dev' and r['group'] in bad_groups]
    kept = [r for r in rows if not (r['split'] == 'dev' and r['group'] in bad_groups)]
    return kept, {'excluded_development_groups': sorted(bad_groups), 'excluded_development_records': len(removed), 'reason': 'At least one reference solution has an identical Python AST in training. Entire development group excluded; training unchanged.'}


def fetch(name):
    repo, paths = SOURCES[name]
    meta = json.load(urlopen('https://huggingface.co/api/datasets/' + repo, timeout=60))
    rev = meta['sha']
    if paths is None:
        paths = sorted(f['rfilename'] for f in meta['siblings'] if '/train-' in f['rfilename'] and f['rfilename'].endswith('.parquet'))
    directory = DATA / 'raw' / name
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'metadata.json').write_text(json.dumps(meta, indent=2))
    rows, files = [], []
    for filename in paths:
        assert 'train' in filename and 'test' not in filename and 'validation' not in filename
        p = Path(hf_hub_download(repo_id=repo, filename=filename, repo_type='dataset', revision=rev, local_dir=directory))
        files.append({'path': filename, 'sha256': digest(p.read_bytes()), 'bytes': p.stat().st_size})
        if p.suffix == '.parquet':
            rows.extend(pq.read_table(p).to_pylist())
        else:
            rows.extend(json.loads(line) for line in p.open() if line.strip())
    print(f'Downloaded {name}: {len(rows)} original train rows', flush=True)
    return name, rows, {'repo': repo, 'revision': rev, 'original_split': 'train', 'license_metadata': meta.get('cardData', {}).get('license'), 'files': files}


def fetch_piqa():
    # Read only the two training members; never extract or parse development data.
    url = 'https://storage.googleapis.com/ai2-mosaic/public/physicaliqa/physicaliqa-train-dev.zip'
    p = DATA / 'raw' / 'piqa' / 'source.zip'
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.write_bytes(urlopen(url, timeout=120).read())
    with zipfile.ZipFile(p) as z:
        train = next(n for n in z.namelist() if n.endswith('/train.jsonl'))
        labels = next(n for n in z.namelist() if n.endswith('/train-labels.lst'))
        rr = z.read(train).decode().splitlines()
        ll = z.read(labels).decode().splitlines()
        assert len(rr) == len(ll)
        rows = [dict(json.loads(r), label=int(l)) for r, l in zip(rr, ll)]
    return 'piqa', rows, {'url': url, 'archive_sha256': digest(p.read_bytes()), 'original_split': 'train', 'read_members': [train, labels], 'license_metadata': 'Unspecified in HF card; original public research dataset. No redistribution configured.'}


def convert(name, rows):
    result, rejected = [], Counter()
    for i, r in enumerate(rows):
        answers = []
        source_id = str(r.get('problem_id', r.get('task_id', r.get('id', i))))
        if name == 'apps':
            prompt = 'Write a Python 3 program that solves this problem. Output code only.\n\n' + r['question']
            if r.get('starter_code'):
                prompt += '\n\nStarter code:\n' + r['starter_code']
            try:
                solutions = json.loads(r['solutions']) if isinstance(r['solutions'], str) else r['solutions']
            except (ValueError, TypeError):
                rejected['invalid_solution_json'] += 1
                continue
            seen_code = set()
            for solution in sorted(solutions or [], key=lambda s: (len(s), s)):
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter('ignore', SyntaxWarning)
                        tree = ast.parse(solution)
                    key = ast.dump(tree, include_attributes=False)
                except (SyntaxError, ValueError, TypeError):
                    rejected['not_python3_parseable'] += 1
                    continue
                if key not in seen_code:
                    seen_code.add(key)
                    answers.append(solution)
                if len(answers) == 8:
                    break
            group = 'code:' + normal(r['question'])
        elif name == 'mbpp':
            prompt = 'Write a Python 3 function for this task. Output code only.\n\n' + r['text']
            answers = [r['code']]
            group = 'code:' + normal(r['text'])
        elif name == 'gsm8k':
            prompt = 'Solve this math problem and explain your calculation.\n\n' + r['question']
            answers = [r['answer']]
            group = 'math:' + normal(r['question'])
        elif name == 'math':
            prompt = 'Solve this math problem and explain your calculation.\n\n' + r['problem']
            answers = [r['solution']]
            group = 'math:' + normal(r['problem'])
        elif name == 'squad':
            prompt = 'Answer the question using the passage.\n\nPassage: ' + r['context'] + '\n\nQuestion: ' + r['question']
            answers = list(dict.fromkeys(r['answers']['text']))[:1]
            group = 'article:' + r['title']
        elif name == 'boolq':
            prompt = 'Answer yes or no using the passage.\n\nPassage: ' + r['passage'] + '\n\nQuestion: ' + r['question']
            answers = ['yes' if r['answer'] else 'no']
            group = 'passage:' + normal(r['passage'])
        elif name == 'hellaswag':
            # Only original positive continuations. Generated negative endings are excluded.
            prompt = 'Continue this description of an activity.\n\n' + r['ctx']
            answers = [r['endings'][int(r['label'])]]
            group = 'hellaswag-source:' + r['source_id']
        elif name == 'piqa':
            prompt = 'Describe a way to accomplish this goal.\n\n' + r['goal']
            answers = [r['sol1'] if int(r['label']) == 0 else r['sol2']]
            group = 'goal:' + normal(r['goal'])
        elif name == 'winogrande':
            prompt = 'Fill in the blank with the correct option.\n\n' + r['sentence'] + '\nOptions: ' + r['option1'] + '; ' + r['option2']
            answers = [r['option' + str(r['answer'])]]
            # Group minimal sentence variants by their unordered content words.
            group = 'winogrande:' + ' '.join(sorted(re.findall(r'\w+', r['sentence'].lower())))
        elif name == 'arc':
            choices = r['choices']
            prompt = 'Answer this science question.\n\n' + r['question'] + '\n' + '\n'.join(f'{a}. {b}' for a, b in zip(choices['label'], choices['text']))
            answers = [choices['text'][choices['label'].index(r['answerKey'])]]
            group = 'science:' + normal(r['question'])
        else:
            raise ValueError(name)
        for j, answer in enumerate(answers):
            if not answer or not answer.strip():
                rejected['empty_answer'] += 1
                continue
            result.append({'source': name, 'original_id': source_id, 'variant': j, 'group': digest(group), 'split': partition(group), 'prompt': prompt, 'answer': answer, 'original_split': 'train'})
    return result, dict(rejected)


def build():
    DATA.mkdir(exist_ok=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(fetch, name) for name in SOURCES] + [pool.submit(fetch_piqa)]
        downloaded = [f.result() for f in futures]
    all_rows, manifest = [], {'version': 1, 'sources': {}, 'excluded_evaluation_families': ['LiveCodeBench', 'IFBench', 'IFEval', 'IF-RLVR', 'BIG-Bench', 'BBH', 'BBEH'], 'external_tests_loaded': False, 'decontamination_status': 'Original pre-2023 train sources only; exact normalized prompt duplicates removed; grouped development holdout. Full cross-benchmark semantic audit pending. Pilot scores are not transfer claims.'}
    seen = {}
    for name, rows, metadata in downloaded:
        converted, rejected = convert(name, rows)
        metadata['original_train_rows'] = len(rows)
        metadata['conversion_rejections'] = rejected
        kept = []
        for row in converted:
            key = digest(normal(row['prompt']))
            prior = seen.get(key)
            if prior and prior != (row['source'], row['original_id']):
                rejected['duplicate_prompt_other_task'] = rejected.get('duplicate_prompt_other_task', 0) + 1
                continue
            seen[key] = (row['source'], row['original_id'])
            kept.append(row)
        all_rows.extend(kept)
        manifest['sources'][name] = metadata
    rng = np.random.default_rng(20260906)
    rng.shuffle(all_rows)
    all_rows, manifest['code_overlap_filter'] = exclude_shared_code_groups(all_rows)
    train_rows = [r for r in all_rows if r['split'] == 'train']
    tok = Tokenizer(models.BPE())
    tok.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
    tok.decoder = decoders.ByteLevel()
    trainer = trainers.BpeTrainer(vocab_size=16384, min_frequency=2, special_tokens=SPECIAL, initial_alphabet=pre_tokenizers.ByteLevel.alphabet(), show_progress=True)
    print(f'Training tokenizer on {len(train_rows)} training records only', flush=True)
    tok.train_from_iterator((text_of(r) for r in train_rows), trainer=trainer, length=len(train_rows))
    tok.save(str(DATA / 'tokenizer.json'))
    token_arrays, mask_arrays, indices = defaultdict(list), defaultdict(list), defaultdict(list)
    counts = defaultdict(Counter)
    groups = defaultdict(set)
    with (DATA / 'records.jsonl').open('w') as f:
        for start in range(0, len(all_rows), 512):
            batch = all_rows[start:start + 512]
            encoded = tok.encode_batch([text_of(r) for r in batch])
            for row, enc in zip(batch, encoded):
                key = (row['source'], row['split'])
                # Keep each complete task within the 1024-token context. No truncation.
                if len(enc.ids) > 1024:
                    counts[key]['excluded_over_1024'] += 1
                    continue
                ids = enc.ids
                answer_start = ids.index(tok.token_to_id('<answer>')) + 1
                mask = [0] * answer_start + [1] * (len(ids) - answer_start)
                indices[key].append((len(token_arrays[key]), len(ids)))
                token_arrays[key].extend(ids)
                mask_arrays[key].extend(mask)
                counts[key]['records'] += 1
                counts[key]['tokens'] += len(ids)
                groups[key].add(row['group'])
                f.write(json.dumps(row, ensure_ascii=False) + '\n')
    for key, ids in token_arrays.items():
        name, split = key
        np.asarray(ids, dtype=np.uint16).tofile(DATA / f'{name}.{split}.bin')
        np.asarray(mask_arrays[key], dtype=np.uint8).tofile(DATA / f'{name}.{split}.mask.bin')
        np.save(DATA / f'{name}.{split}.index.npy', np.asarray(indices[key], dtype=np.int64))
    manifest['tokenizer'] = {'vocab_size': tok.get_vocab_size(), 'sha256': digest((DATA / 'tokenizer.json').read_bytes()), 'trained_on': 'original train rows after grouped holdout; includes long training records subsequently excluded from model training'}
    manifest['max_record_tokens'] = 1024
    manifest['derived_files_sha256'] = {p.name: digest(p.read_bytes()) for p in sorted(DATA.iterdir()) if p.suffix in ['.bin', '.npy']}
    manifest['counts'] = {'.'.join(k): dict(v, groups=len(groups[k])) for k, v in counts.items()}
    for name in manifest['sources']:
        assert groups[(name, 'train')].isdisjoint(groups[(name, 'dev')])
        assert counts[(name, 'train')]['tokens'] > 1025, name
        assert counts[(name, 'dev')]['tokens'] > 1025, name
    (DATA / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest['counts'], indent=2), flush=True)
    print('DATA_READY', flush=True)


if __name__ == '__main__':
    build()
