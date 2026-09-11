#!/usr/bin/env python3
"""Local ZIP64 archives with streaming SHA-256 verification and safe restoration."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import zipfile

CHUNK = 8 * 1024 * 1024
TEXT = {'.json', '.jsonl', '.md', '.txt', '.py', '.csv', '.html', '.log', '.yaml', '.yml'}


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(CHUNK), b''): h.update(b)
    return h.hexdigest()


def write_json(path, data):
    temp = path.with_suffix(path.suffix + '.partial')
    temp.write_text(json.dumps(data, indent=2) + '\n')
    temp.replace(path)


def entries(root):
    yield root
    if root.is_dir() and not root.is_symlink():
        for child in sorted(root.iterdir()): yield from entries(child)


def archive_part(destination, name, roots):
    """roots contains (source path, archive path) pairs; source links aren't followed."""
    output = destination / (name + '.zip')
    if output.exists(): raise ValueError('Archive already exists: ' + str(output))
    partial = output.with_suffix('.zip.partial')
    inventory = []
    with zipfile.ZipFile(partial, 'w', allowZip64=True) as z:
        for source, arcroot in roots:
            for p in entries(source):
                arc = (Path(arcroot) / p.relative_to(source)).as_posix()
                before = p.lstat()
                mode = before.st_mode
                if not (stat.S_ISREG(mode) or stat.S_ISDIR(mode) or stat.S_ISLNK(mode)):
                    raise ValueError('Unsupported file type: ' + str(p))
                if stat.S_ISDIR(mode): arc += '/'
                stamp = dt.datetime.fromtimestamp(before.st_mtime)
                info = zipfile.ZipInfo(arc, (max(1980, min(2107, stamp.year)), stamp.month, stamp.day,
                                            stamp.hour, stamp.minute, stamp.second))
                info.create_system = 3
                info.external_attr = mode << 16
                info.compress_type = zipfile.ZIP_DEFLATED if p.suffix in TEXT else zipfile.ZIP_STORED
                info._compresslevel = 1
                h = hashlib.sha256()
                if stat.S_ISLNK(mode):
                    raw = os.readlink(p).encode(); z.writestr(info, raw); h.update(raw)
                    kind, size = 'symlink', len(raw)
                elif stat.S_ISDIR(mode):
                    z.writestr(info, b''); kind, size = 'directory', 0
                else:
                    info.file_size = before.st_size
                    with p.open('rb') as src, z.open(info, 'w', force_zip64=True) as out:
                        for block in iter(lambda: src.read(CHUNK), b''):
                            h.update(block); out.write(block)
                    after = p.stat()
                    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                        raise ValueError('Source changed during archive: ' + str(p))
                    kind, size = 'file', before.st_size
                inventory.append(dict(path=arc, kind=kind, bytes=size, sha256=h.hexdigest()))
    partial.replace(output)
    record = dict(archive=output.name, archive_bytes=output.stat().st_size,
                  archive_sha256=digest(output), entries=inventory)
    write_json(destination / (name + '.manifest.json'), record)
    return {k: v for k, v in record.items() if k != 'entries'} | {'entries': len(inventory)}


def verify_part(folder, name):
    manifest = json.loads((folder / (name + '.manifest.json')).read_text())
    archive = folder / manifest['archive']
    if digest(archive) != manifest['archive_sha256']: raise ValueError('Archive SHA mismatch: ' + name)
    with zipfile.ZipFile(archive) as z:
        if z.namelist() != [r['path'] for r in manifest['entries']]: raise ValueError('Archive inventory mismatch')
        for row in manifest['entries']:
            h = hashlib.sha256(); size = 0
            with z.open(row['path']) as f:
                for b in iter(lambda: f.read(CHUNK), b''): h.update(b); size += len(b)
            if size != row['bytes'] or h.hexdigest() != row['sha256']:
                raise ValueError('Entry SHA mismatch: ' + row['path'])
    return manifest


def restore_parts(folder, output, names):
    """Never overwrite a destination; create links only after regular files are restored."""
    if output.exists(): raise ValueError('Restore destination must not exist')
    manifests = [verify_part(folder, name) for name in names]
    metadata = json.loads((folder / 'BACKUP.json').read_text())
    source_root = Path(metadata['source_project'])
    output.mkdir(parents=True, mode=0o700)
    links = []
    for manifest in manifests:
        with zipfile.ZipFile(folder / manifest['archive']) as z:
            for row in manifest['entries']:
                relative = Path(row['path'])
                if relative.is_absolute() or '..' in relative.parts: raise ValueError('Unsafe entry')
                target = output / relative
                if row['kind'] == 'directory': target.mkdir(parents=True, exist_ok=True); continue
                target.parent.mkdir(parents=True, exist_ok=True)
                if row['kind'] == 'symlink':
                    value = z.read(row['path']).decode()
                    original = Path(value)
                    if original.is_absolute():
                        if not original.is_relative_to(source_root): raise ValueError('External symlink')
                        value = os.path.relpath(output / 'project' / original.relative_to(source_root), target.parent)
                    resolved = (target.parent / value).resolve()
                    if not resolved.is_relative_to(output.resolve()): raise ValueError('Escaping symlink')
                    links.append((target, value)); continue
                with z.open(row['path']) as src, target.open('xb') as dest: shutil.copyfileobj(src, dest, CHUNK)
                target.chmod((z.getinfo(row['path']).external_attr >> 16) & 0o777)
    for target, value in links: target.symlink_to(value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['create', 'verify', 'restore'])
    parser.add_argument('--project', type=Path)
    parser.add_argument('--backup', required=True, type=Path)
    parser.add_argument('--destination', type=Path)
    parser.add_argument('--part', action='append')
    args = parser.parse_args()
    folder = args.backup.expanduser().resolve()
    if args.action == 'create':
        if args.project is None: parser.error('--project required')
        project = args.project.expanduser().resolve()
        if folder.is_relative_to(project): parser.error('Backup must be outside project')
        if folder.exists(): parser.error('Backup directory must not exist')
        folder.mkdir(parents=True, mode=0o700)
        metadata = dict(created_at=dt.datetime.now().astimezone().isoformat(), source_project=str(project),
                        verified=False, archives=[], note='Local archive; no external storage implied')
        write_json(folder / 'BACKUP.json', metadata)
        for category in ['data', 'runs']:
            base = project / category
            loose = []
            for p in sorted(base.iterdir()):
                if p.is_dir() and not p.is_symlink():
                    record = archive_part(folder, category + '--' + p.name, [(p, 'project/' + str(p.relative_to(project)))])
                    metadata['archives'].append(record); write_json(folder / 'BACKUP.json', metadata)
                    print(json.dumps(record), flush=True)
                else: loose.append((p, 'project/' + str(p.relative_to(project))))
            if loose:
                record = archive_part(folder, category + '--root', loose)
                metadata['archives'].append(record); write_json(folder / 'BACKUP.json', metadata)
                print(json.dumps(record), flush=True)
    else:
        names = args.part or [p.name.removesuffix('.manifest.json') for p in sorted(folder.glob('*.manifest.json'))]
        if not names: parser.error('No archive manifests found')
        if args.action == 'restore':
            if args.destination is None: parser.error('--destination required')
            restore_parts(folder, args.destination.expanduser().absolute(), names)
        else:
            for name in names:
                verify_part(folder, name); print('Verified ' + name, flush=True)
            write_json(folder / 'VERIFIED.json', dict(verified_at=dt.datetime.now().astimezone().isoformat(), parts=names))


if __name__ == '__main__': main()
