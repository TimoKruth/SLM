import copy

import pytest

from benchmark_expansion.prepare import convert, group_rows, key, old_keys
from slm.breadth import EXPANSION_FAMILIES, FAMILIES, sampling_weights


def trivia(question='Who wrote this book?', uid='a', answer='Alice'):
    return dict(question=question, question_id=uid, question_source='original-site',
                answer=dict(value=answer, aliases=['Alice', 'noisy unrelated alias']))


def tydi(uid='english-a', title='Article', context='Alice wrote it.', question='Who wrote it?'):
    return dict(id=uid, title=title, context=context, question=question,
                answers=dict(text=['Alice'], answer_start=[0]))


def tab(**updates):
    row = dict(split='train', question='How many?', table='Item | Count\nA | 5',
               table_title='Counts', answer='5', unit='kg', choices=None,
               ans_type='integer_number', grade=2, solution='Count the blue cells.')
    row.update(updates)
    return row


def test_canonical_answer_only_and_original_aliases_retained():
    row = convert('triviaqa', trivia())
    assert row['answer'] == 'Alice'
    assert 'noisy unrelated alias' in row['aliases']
    assert 'noisy unrelated alias' not in row['prompt']


@pytest.mark.parametrize('starts', [[-1], [], [0, 0]])
def test_bad_original_spans_fail_closed(starts):
    raw = tydi()
    raw['answers']['answer_start'] = starts
    with pytest.raises(ValueError):
        convert('tydiqa', raw)


def test_offset_mismatch_is_flagged_without_rewriting_original():
    raw = tydi()
    raw['answers']['answer_start'] = [1]
    row = convert('tydiqa', raw)
    assert row['answer_starts'] == [1]
    assert row['original_answer_offsets_match'] is False
    assert row['answer_text_verified'] is True


def test_answer_absent_from_context_is_rejected():
    raw = tydi()
    raw['answers']['text'] = ['Bob']
    with pytest.raises(ValueError):
        convert('tydiqa', raw)


def test_unicode_span_uses_character_offsets():
    raw = tydi(uid='arabic-a', context='كتب علي', question='من؟')
    raw['answers'] = dict(text=['علي'], answer_start=[4])
    assert convert('tydiqa', raw)['answer'] == 'علي'


def test_tabmwp_unit_and_visual_solution():
    row = convert('tabmwp', tab(), '1')
    assert row['answer'] == '5 kg'
    assert row['original_solution'] == 'Count the blue cells.'
    assert 'blue' not in row['prompt']
    assert 'Unit: kg' in row['prompt']


@pytest.mark.parametrize('changes', [dict(split='test'), dict(choices=['4', '6']), dict(table='')])
def test_tabmwp_invalid_training_rows_fail_closed(changes):
    with pytest.raises(ValueError):
        convert('tabmwp', tab(**changes), '1')


def test_transitive_article_and_context_groups_and_order_independence():
    rows = [convert('tydiqa', tydi()),
            convert('tydiqa', tydi(uid='english-b', title='Article', context='Alice read it.')),
            convert('tydiqa', tydi(uid='english-c', title='Different', context='Alice read it.'))]
    reverse = copy.deepcopy(rows[::-1])
    group_rows(rows)
    group_rows(reverse)
    assert len({r['group'] for r in rows}) == 1
    assert len({r['split'] for r in rows}) == 1
    assert {(r['original_id'], r['group'], r['split']) for r in rows} == {
        (r['original_id'], r['group'], r['split']) for r in reverse}


def test_trivia_web_wiki_copies_stay_together():
    rows = [convert('triviaqa', trivia(uid='a')), convert('triviaqa', trivia(uid='b'))]
    group_rows(rows)
    assert rows[0]['group'] == rows[1]['group']


def test_table_content_groups_ignore_title_and_question_changes():
    rows = [convert('tabmwp', tab(), '1'),
            convert('tabmwp', tab(table_title='Other', question='What is the count?'), '2')]
    group_rows(rows)
    assert rows[0]['group'] == rows[1]['group']


def test_context_overlap_ignores_instruction_wording():
    row = dict(group='x', prompt='Old instruction.\n\nPassage: Alice wrote it.\n\nQuestion: Who wrote it?')
    assert key('context', 'Alice wrote it.') in set(old_keys(row))
    assert key('question', 'Who wrote it?') in set(old_keys(row))


def test_expanded_families_are_explicit_and_balanced():
    assert sum(map(len, FAMILIES.values())) == 32
    sources = {s for group in EXPANSION_FAMILIES.values() for s in group}
    assert len(sources) == 35
    with pytest.raises(ValueError):
        sampling_weights(sources)
    weights = sampling_weights(sources, families=EXPANSION_FAMILIES)
    for group in EXPANSION_FAMILIES.values():
        assert sum(weights[s] for s in group) == pytest.approx(1 / 9)


def test_scoring_keeps_noisy_aliases_out_and_does_not_claim_official_scores():
    from benchmark_expansion.scoring import score_prepared
    row = convert('triviaqa', trivia())
    assert score_prepared(row, ' ALICE ')['correct']
    assert not score_prepared(row, 'noisy unrelated alias')['correct']
    assert score_prepared(row, 'Alice')['official_benchmark_score'] is False


def test_multilingual_scoring_preserves_non_latin_answers():
    from benchmark_expansion.scoring import score_prepared
    row = dict(source='tydiqa', answer='علي', answers=['علي'])
    assert score_prepared(row, 'علي')['correct']
    assert not score_prepared(row, 'كتب')['correct']


def test_tabmwp_scoring_checks_unit():
    from benchmark_expansion.scoring import score_prepared
    row = convert('tabmwp', tab(), '1')
    assert score_prepared(row, '5 kg')['correct']
    assert not score_prepared(row, '5 lb')['correct']


def test_existing_evaluator_routes_new_sources_and_families():
    from slm.broad_eval import SOURCE_FAMILY, score_general
    assert SOURCE_FAMILY['tydiqa'] == 'multilingual_reading'
    row = convert('triviaqa', trivia())
    assert score_general(row, 'Alice')['metric'] == 'original_answer_exact_proxy'
    assert score_general(row, 'Alice', memorization=True)['metric'] == 'training_answer_recall'


@pytest.mark.parametrize('path,url', [('../outside.json', 'https://example.org/train.json'),
                                    ('train.parquet', 'https://example.org/test.parquet')])
def test_fetch_rejects_escape_or_nontrain_before_download(tmp_path, path, url):
    import json
    from benchmark_expansion.fetch import fetch
    lock = tmp_path/'lock.json'
    # The traversal must escape the entire staging root, not just the source folder.
    if path.startswith('../'):
        path = '../' + path
    lock.write_text(json.dumps({'sources': {'source': {'original_split': 'train',
                                                     'files': [{'path': path, 'url': url}]}}}))
    with pytest.raises(ValueError):
        fetch(lock, tmp_path/'stage')
