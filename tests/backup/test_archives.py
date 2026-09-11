import json
from pathlib import Path
import pytest
from tools.archive_project import archive_part, verify_part, restore_parts, write_json


def test_archive_restore_and_corruption(tmp_path):
    source = tmp_path/'source'; (source/'data').mkdir(parents=True)
    payload = b'\x00\x01\xff'*10000
    (source/'data'/'sample.bin').write_bytes(payload)
    (source/'data'/'alias.bin').symlink_to(source/'data'/'sample.bin')
    backup = tmp_path/'backup';backup.mkdir()
    write_json(backup/'BACKUP.json',{'source_project':str(source)})
    archive_part(backup,'data',[(source/'data','project/data')])
    verify_part(backup,'data')
    restored = tmp_path/'restore';restore_parts(backup,restored,['data'])
    assert (restored/'project/data/sample.bin').read_bytes()==payload
    assert (restored/'project/data/alias.bin').is_symlink()
    assert (restored/'project/data/alias.bin').resolve()==restored/'project/data/sample.bin'
    with pytest.raises(ValueError):restore_parts(backup,restored,['data'])
    with (backup/'data.zip').open('r+b') as f:f.seek(100);f.write(b'broken')
    with pytest.raises(ValueError):verify_part(backup,'data')
