from copy import deepcopy

import pytest

from experiments.prepare_fresh_parameter_confirmation import content_keys, validation_record
from experiments.prepare_broad import converted as broad_convert
from slm.prepare import convert
from slm.prepare_v2 import converted as expanded_convert
from slm.prepare import digest, normal

PROVENANCE = dict(path='config/validation/0000.parquet', repo='test', revision='0'*40, sha256='1'*64)


def test_arc_validation_keeps_training_group_identity_but_separates_ids():
    raw = dict(id='1', question='Which material conducts electricity?',
               choices=dict(label=['A','B'], text=['copper','rubber']), answerKey='A')
    old = convert('arc', [raw])[0][0]
    new = validation_record('arc', raw, '1', PROVENANCE)
    assert new['group'] == old['group']
    assert new['original_id'] != old['original_id']
    assert new['split'] == 'confirmation' and new['original_split'] == 'validation'
    assert new['answer'] == 'copper'


def test_quarel_rejects_negative_label_and_keeps_group():
    raw = dict(id='q', question='Who is faster? (A) Jim (B) Kim', answer_index=1)
    row = validation_record('quarel', raw, 'q', PROVENANCE)
    assert row['group'] == digest('quarel:'+normal(expanded_convert('quarel',raw,{})[3]))
    assert row['answer'] == 'B'
    with pytest.raises(AssertionError):
        validation_record('quarel', dict(raw, answer_index=-1), 'q', PROVENANCE)


def test_dream_entire_dialogue_is_same_group_across_questions():
    raw = dict(id='1', dialogue_id='dialogue1', dialogue=['Hello.', 'Good morning.'],
               question='When?', choice=['Morning','Night'], answer='Morning')
    a = validation_record('dream', raw, '1', PROVENANCE)
    b = validation_record('dream', dict(raw, id='2', question='What time?'), '2', PROVENANCE)
    assert a['group'] == b['group'] == broad_convert('dream',raw,'1')['group']
    assert content_keys(a) & content_keys(b)


def test_quoref_checks_all_reference_spans_and_article_alias():
    raw = dict(id='1', context='Alice met Bob.', question='Who met Bob?', title='Alice story',
               url='https://example.org/Alice_story', answers=dict(text=['Alice'], answer_start=[0]))
    row = validation_record('quoref', raw, '1', PROVENANCE)
    assert digest('article:Alice_story') in row['overlap_group_aliases']
    invalid = deepcopy(raw); invalid['answers']['answer_start'] = [1]
    with pytest.raises(AssertionError): validation_record('quoref', invalid, '1', PROVENANCE)


def test_context_overlap_is_source_independent_and_normalizes_punctuation():
    first = dict(source='squad', prompt='Passage: Alice met Bob.\n\nQuestion: Who?')
    second = dict(source='cosmos_qa', prompt='Context: ALICE  met Bob!\n\nQuestion: When?')
    assert content_keys(first) & content_keys(second)
    third = dict(source='cosmos_qa', prompt='Context: Carol met Bob.\n\nQuestion: Who?')
    assert not content_keys(first) & content_keys(third)


def test_question_overlap_survives_different_instruction_and_options():
    a = dict(source='arc', prompt='Science.\n\nWhich is hot?\nA. fire\nB. ice')
    b = dict(source='openbookqa', prompt='Choose.\n\nWhich is hot?\nA. ice\nB. fire')
    assert content_keys(a) & content_keys(b)
