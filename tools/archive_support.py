#!/usr/bin/env python3
"""Add a consistent PowerWatch snapshot and code bundle to an existing local backup."""
import argparse
from contextlib import closing
import datetime as dt
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tarfile
import tempfile

from archive_project import archive_part, write_json


def main():
 p=argparse.ArgumentParser();p.add_argument('--backup',required=True,type=Path);p.add_argument('--code',required=True,type=Path);a=p.parse_args()
 folder=a.backup.expanduser().resolve();code=a.code.resolve();meta=json.loads((folder/'BACKUP.json').read_text())
 if any((folder/(n+'.zip')).exists() for n in ['code','powerwatch-support']):raise ValueError('Support archives already exist')
 with tempfile.TemporaryDirectory(prefix='slm-backup-support-',dir=folder.parent) as tmp:
  root=Path(tmp);support=root/'support';support.mkdir()
  app=Path.home()/'Library/Application Support/PowerWatch';pw=support/'PowerWatch';pw.mkdir();db=pw/'data/powerwatch.sqlite3';db.parent.mkdir()
  with closing(sqlite3.connect((app/'data/powerwatch.sqlite3').as_uri()+'?mode=ro',uri=True,timeout=5)) as source, closing(sqlite3.connect(db)) as dest:
   source.backup(dest,pages=256,sleep=.05)
   check=dest.execute('PRAGMA integrity_check').fetchall()
   if check!=[('ok',)]:raise ValueError('Invalid SQLite snapshot')
   stats=dest.execute('select count(*),min(ts),max(ts) from samples').fetchone()
  for name in ['powerwatch','slm_resource_report.py']:
   shutil.copy2(app/name,pw/name)
  agents=support/'LaunchAgents';agents.mkdir()
  for name in ['com.local.powerwatch.plist','com.local.powerwatch.slm-report.plist']:
   shutil.copy2(Path.home()/'Library/LaunchAgents'/name,agents/name)
  skill=Path.home()/'.codex/skills/read-system-resources'
  shutil.copytree(skill,support/'skills/read-system-resources',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
  write_json(support/'SQLITE_SNAPSHOT.json',dict(created_at=dt.datetime.now().astimezone().isoformat(),integrity_check='ok',samples=stats[0],first_timestamp=stats[1],last_timestamp=stats[2],source=str(app/'data/powerwatch.sqlite3')))
  record=archive_part(folder,'powerwatch-support',[(support,'support')]);meta['archives'].append(record);write_json(folder/'BACKUP.json',meta);print(json.dumps(record),flush=True)
  bundle_root=root/'code';bundle_root.mkdir()
  subprocess.run(['git','bundle','create',str(bundle_root/'repository.bundle'),'--branches','--tags'],cwd=code,check=True,capture_output=True)
  subprocess.run(['git','bundle','verify',str(bundle_root/'repository.bundle')],cwd=code,check=True,capture_output=True)
  revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=code,text=True).strip()
  archive=root/'source.tar';subprocess.run(['git','archive','-o',str(archive),revision],cwd=code,check=True)
  (bundle_root/'source').mkdir()
  with tarfile.open(archive) as t:t.extractall(bundle_root/'source',filter='data')
  raw=subprocess.check_output(['git','worktree','list','--porcelain'],cwd=code,text=True)
  write_json(bundle_root/'WORKTREES.json',{'git_worktree_porcelain':raw})
  write_json(bundle_root/'CODE_SNAPSHOT.json',{'commit':revision,'note':'All code at this commit; later commits may add only the backup verification inventory.'})
  record=archive_part(folder,'code',[(bundle_root,'code')]);meta['archives'].append(record);write_json(folder/'BACKUP.json',meta);print(json.dumps(record),flush=True)

if __name__=='__main__':main()
