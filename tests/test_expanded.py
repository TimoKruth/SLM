import json
from slm.data import Sampler
from slm.prepare_v2 import reference_solutions, CodeOverlap, converted
from test_training import make_data


def test_only_parseable_unique_correct_references_are_selected():
    assert reference_solutions(['print(1)', 'print( 1 )', 'def bad(', 'print(2)'])==['print(1)','print(2)']
    r={'name':'example','description':'Sum two numbers','solutions':{'language':[1,3,2], 'solution':['print 1','print(1)','cout << 1;']}}
    assert converted('code_contests',r,{})[2]==['print(1)']


def test_near_code_duplicate_is_found_after_minor_rewording():
    text='Read the number n and calculate the sum of all the positive integers from one to n inclusive then output the result as a single integer.'
    detector=CodeOverlap();detector.add(text)
    assert detector.overlaps(text+' Thank you.')
    assert not detector.overlaps('Sort a list of words by their last character and return the first three words.')


def test_manifest_selects_train_and_dev_sources_separately(tmp_path):
    make_data(tmp_path)
    (tmp_path/'manifest.json').write_text(json.dumps({'source_weights':{'toy':1},'evaluation_weights':{'toy':2}}))
    assert Sampler(tmp_path,context=16).weights=={'toy':1}
    assert Sampler(tmp_path,split='dev',context=16).weights=={'toy':2}


def test_invalid_nli_labels_are_excluded():
    assert converted('snli',{'premise':'One','hypothesis':'Two','label':-1},{}) is None


def test_six_hour_restart_keeps_original_deadline(tmp_path,monkeypatch):
    import sys
    from datetime import datetime
    import slm.sixhour as launcher
    calls=[]
    monkeypatch.setattr(launcher,'supervise',lambda:calls.append(list(sys.argv)))
    arguments=['sixhour','--run',str(tmp_path/'run'),'--data',str(tmp_path/'data')]
    monkeypatch.setattr(sys,'argv',arguments.copy());launcher.main()
    schedule=json.loads((tmp_path/'run/schedule.json').read_text())
    assert (datetime.fromisoformat(schedule['training_until'])-datetime.fromisoformat(schedule['started_at'])).total_seconds()==21600
    monkeypatch.setattr(sys,'argv',arguments.copy());launcher.main()
    assert json.loads((tmp_path/'run/schedule.json').read_text())==schedule
    assert calls[0]==calls[1]
    assert '--code-eval' in calls[0]
