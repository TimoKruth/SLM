"""Download only explicitly listed train files and provenance documents."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def fetch(lock, output):
    spec = json.loads(lock.read_text())
    output.mkdir(parents=True, exist_ok=True)
    for source, meta in spec['sources'].items():
        if meta['original_split'] != 'train':
            raise ValueError('Only original training splits allowed')
        for entry in meta['files']:
            path = output / source / entry['path']
            if not path.resolve().is_relative_to(output.resolve()):
                raise ValueError('Path escapes staging directory')
            if entry.get('role') == 'original_train' or path.suffix in {'.json', '.jsonl', '.parquet', '.csv'}:
                if 'train' not in entry['url'].rsplit('/', 1)[-1] or path.stem != 'train':
                    raise ValueError('Data file must be an explicit original train file')
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                tmp = path.with_suffix(path.suffix + '.partial')
                with urlopen(entry['url'], timeout=120) as response, tmp.open('wb') as out:
                    while block := response.read(1024 * 1024):
                        out.write(block)
                if entry.get('sha256') and sha(tmp) != entry['sha256']:
                    raise ValueError(f'Download hash mismatch: {source}/{entry["path"]}')
                tmp.rename(path)
            digest = sha(path)
            if entry.get('sha256') and digest != entry['sha256']:
                raise ValueError(f'Changed staged input: {path}')
            entry.update(sha256=digest, bytes=path.stat().st_size)
        print('staged', source, flush=True)
    (output / 'manifest.json').write_text(json.dumps(spec, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--lock', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    fetch(args.lock, args.output)


if __name__ == '__main__':
    main()
