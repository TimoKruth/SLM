import subprocess
import sys
import time

from slm.overnight import wait_until


def test_deadline_terminates_child(tmp_path):
    child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
    result = wait_until(child, time.time() + .1, tmp_path / 'heartbeat.json', tmp_path, 'test')
    assert result != 0
    assert child.poll() is not None
    assert (tmp_path / 'heartbeat.json').exists()


def test_stop_file_terminates_child(tmp_path):
    (tmp_path / 'STOP').touch()
    child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
    result = wait_until(child, time.time() + 60, tmp_path / 'heartbeat.json', tmp_path, 'test')
    assert result != 0
    assert child.poll() is not None
