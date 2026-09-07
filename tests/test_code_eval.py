from pathlib import Path
import pytest
from slm.code_eval import run_python, same_output, score


def test_output_comparison():
    assert same_output('1  2.00000001\n', '1\n2')
    assert not same_output('2 1', '1 2')
    assert not same_output('nan', '1')
    assert not same_output('', '1')


def test_real_sandbox_and_limits(tmp_path):
    secret = tmp_path / 'private.txt'
    secret.write_text('canary')
    assert run_python('print(42)')['stdout'].strip() == '42'
    assert run_python(f'print(open({str(secret)!r}).read())')['returncode'] != 0
    assert run_python(f'open({str(secret)!r}, "w").write("changed")')['returncode'] != 0
    assert secret.read_text() == 'canary'
    assert run_python("import socket; socket.socket().connect(('1.1.1.1', 80))")['returncode'] != 0
    assert run_python('import os; os.fork()')['returncode'] != 0
    assert run_python('while True: pass', timeout=0.2)['timeout']


def test_positive_and_negative_programs():
    task = dict(source='apps', cases=[dict(input='2\n', output='4\n'), dict(input='3\n', output='6\n')])
    assert score('print(int(input())*2)', task)['status'] == 'passed'
    assert score('print(4)', task)['status'] == 'wrong_answer'
    assert score('raise ValueError()', task)['status'] == 'runtime_error'
    assert score('def bad(', task)['status'] == 'syntax_error'
    task = dict(source='mbpp', setup='', cases=[{'assertion':'assert double(3) == 6'}])
    assert score('def double(x): return x*2', task)['status'] == 'passed'
    assert score('def double(x): return x', task)['status'] == 'wrong_answer'


def test_early_exit_cannot_bypass_assertion():
    task = dict(source='mbpp', setup='', cases=[{'assertion':'assert double(3) == 6'}])
    assert score('import sys; sys.exit(0)', task)['status'] == 'wrong_answer'
