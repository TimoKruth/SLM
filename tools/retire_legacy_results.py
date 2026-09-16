"""Create and verify private legacy ZIP64s; explicit prune removes only verified sources."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from archive_project import archive_part, verify_part, entries, digest, write_json


def create(project, backup, inventory):
    assert not backup.exists(), 'New archive directory required'
    backup.mkdir(parents=True, mode=0o700)
    notice=backup/'DEPRECATED.md'
    notice.write_text('# DEPRECATED — legacy SLM experiments\n\nRetired on 2026-09-16 by user request. All reports, scores, plans and model artifacts in this archive are historical reference only. They are not the current baseline or evidence for the fresh 47-source training. Original payloads are preserved byte-for-byte; this notice supersedes historical current-status language. Restore only into an explicit temporary reference directory, then remove the unpacked copy after use. Do not resume old controllers.\n')
    parts=json.loads(inventory.read_text())
    meta=dict(created=datetime.now().astimezone().isoformat(),status='archiving',deprecated=True,
              source_project=str(project),archives=[],policy='Private local ZIP64s; no raw datasets, weights or process logs uploaded to GitHub.')
    write_json(backup/'BACKUP.json',meta)
    for part in parts:
        source=Path(part['path']);assert source.exists() or source.is_symlink()
        workspace=source.parent.parent
        assert source.parent.name=='runs' and workspace.parent==project.parent and source.name!='system-resources'
        name=workspace.name+'--runs--'+source.name
        arc='worktrees/'+workspace.name+'/runs/'+source.name
        record=archive_part(backup,name,[(notice,'DEPRECATED.md'),(source,arc)])
        verify_part(backup,name)
        record.update(source=str(source),archive_root=arc,verified=True)
        meta['archives'].append(record);write_json(backup/'BACKUP.json',meta)
        print('VERIFIED',name,record['archive_bytes'],flush=True)
    # Preserve every named branch and each checked-out tracked source tree before retirement.
    with tempfile.TemporaryDirectory(prefix='slm-code-archive-') as temp:
        tmp=Path(temp);bundle=tmp/'repository.bundle'
        subprocess.run(['git','bundle','create',str(bundle),'--branches','--tags'],cwd=project,check=True)
        subprocess.run(['git','bundle','verify',str(bundle)],cwd=project,check=True,stdout=subprocess.DEVNULL)
        roots=[(notice,'DEPRECATED.md'),(bundle,'code/repository.bundle')];worktrees=[]
        raw=subprocess.check_output(['git','worktree','list','--porcelain'],cwd=project,text=True)
        for block in raw.strip().split('\n\n'):
            lines=block.splitlines();work=Path(lines[0].removeprefix('worktree '))
            assert not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=work,text=True),work
            worktrees.append(dict(path=str(work),head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=work,text=True).strip()))
            for name in subprocess.check_output(['git','ls-files'],cwd=work,text=True).splitlines():
                roots.append((work/name,'worktrees/'+work.name+'/'+name))
        write_json(tmp/'WORKTREES.json',worktrees);roots.append((tmp/'WORKTREES.json','code/WORKTREES.json'))
        record=archive_part(backup,'legacy-code-and-branches',roots);verify_part(backup,'legacy-code-and-branches')
        record.update(verified=True);meta['archives'].append(record);meta['worktrees']=worktrees
    meta.update(status='verified',finished=datetime.now().astimezone().isoformat())
    write_json(backup/'BACKUP.json',meta)
    print('ALL_VERIFIED',len(meta['archives']),flush=True)


def prune(project,backup):
    meta=json.loads((backup/'BACKUP.json').read_text());assert meta['status']=='verified'
    removed=[]
    for part in meta['archives']:
        if 'source' not in part:continue
        source=Path(part['source']);assert source.parent.name=='runs' and source.parent.parent.parent==project.parent
        assert source.name!='system-resources'
        manifest=json.loads((backup/(part['archive'].removesuffix('.zip')+'.manifest.json')).read_text())
        assert part['verified'] and digest(backup/part['archive'])==part['archive_sha256']
        expected={r['path']:r for r in manifest['entries'] if r['path']!='DEPRECATED.md'}
        actual=set()
        for p in entries(source):
            key=(Path(part['archive_root'])/p.relative_to(source)).as_posix()
            if p.is_dir() and not p.is_symlink():key+='/'
            actual.add(key);row=expected[key]
            if p.is_symlink():assert hashlib.sha256(os.readlink(p).encode()).hexdigest()==row['sha256']
            elif p.is_file():assert digest(p)==row['sha256']
            else:assert row['kind']=='directory'
        assert actual==expected.keys(),'Source inventory changed'
        if source.is_symlink() or source.is_file():source.unlink()
        else:shutil.rmtree(source)
        removed.append(str(source));write_json(backup/'PRUNED.json',dict(removed=removed,checked_against_verified_zip=True))
        print('PRUNED',source,flush=True)
    return removed


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['create','prune'])
    p.add_argument('--project',type=Path,required=True);p.add_argument('--backup',type=Path,required=True);p.add_argument('--inventory',type=Path)
    a=p.parse_args();os.nice(10)
    if a.action=='create':create(a.project.resolve(),a.backup.resolve(),a.inventory)
    else:prune(a.project.resolve(),a.backup.resolve())
