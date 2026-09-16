"""Deletion is permitted only while source and verified archive still match."""
import json
from pathlib import Path
import sys
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from retire_legacy_results import prune
from archive_project import archive_part, verify_part


def fixture(tmp_path):
    project=tmp_path/'project';source=project/'runs'/'legacy';source.mkdir(parents=True)
    (source/'report.txt').write_text('historical evidence')
    backup=tmp_path/'backup';backup.mkdir();notice=backup/'DEPRECATED.md';notice.write_text('Deprecated')
    root='worktrees/project/runs/legacy'
    record=archive_part(backup,'legacy',[(notice,'DEPRECATED.md'),(source,root)])
    verify_part(backup,'legacy');record.update(source=str(source),archive_root=root,verified=True)
    (backup/'BACKUP.json').write_text(json.dumps(dict(status='verified',archives=[record])))
    return project,backup,source


@pytest.mark.parametrize('mutation',['changed','new_file','corrupt_zip'])
def test_prune_preserves_unverified_source(tmp_path,mutation):
    project,backup,source=fixture(tmp_path)
    if mutation=='changed':(source/'report.txt').write_text('new evidence')
    elif mutation=='new_file':(source/'extra.txt').write_text('not archived')
    else:
        with (backup/'legacy.zip').open('ab') as f:f.write(b'corrupted')
    with pytest.raises((AssertionError,KeyError)):prune(project,backup)
    assert source.exists() and (source/'report.txt').exists()


def test_prune_only_deletes_verified_legacy_leaves_live_monitor(tmp_path):
    project,backup,source=fixture(tmp_path)
    monitor=project/'runs'/'system-resources';monitor.mkdir();(monitor/'current').write_text('live')
    assert prune(project,backup)==[str(source)]
    assert not source.exists() and (monitor/'current').read_text()=='live'
