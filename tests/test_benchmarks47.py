import copy
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from tokenizers import Tokenizer, models, pre_tokenizers

from benchmark_expansion.fetch import sha
from benchmark_expansion.prepare import group_rows, key, prepare
from benchmark_expansion.scoring47 import score_wave6
from benchmark_expansion.wave6 import convert, RejectedRecord, original_rows, dialogue_key
from slm.breadth import BENCHMARK47_FAMILIES, EXPANSION_FAMILIES, FAMILIES, sampling_weights
from slm.prepare import text_of


def test_47_distinct_sources_without_recounting_old_configurations():
    names = [s for sources in BENCHMARK47_FAMILIES.values() for s in sources]
    assert len(names) == len(set(names)) == 47
    assert sum(map(len, FAMILIES.values())) == 32
    assert sum(map(len, EXPANSION_FAMILIES.values())) == 35
    assert 'wnli' not in names and 'logiqa_nli' not in names and 'tatqa' not in names
    weights = sampling_weights(names, families=BENCHMARK47_FAMILIES)
    assert sum(weights.values()) == pytest.approx(1)
    for sources in BENCHMARK47_FAMILIES.values():
        assert sum(weights[s] for s in sources) == pytest.approx(1/13)


def test_entailment_label_orders_differ():
    raw = dict(premise='Birds fly.', hypothesis='Birds move.', label=1, idx=1,
               pairID='1n', promptID=1, genre='fiction')
    assert convert('multinli', raw)['answer'] == 'neutral'
    assert convert('cb', raw)['answer'] == 'contradiction'
    raw['label'] = -1
    with pytest.raises(RejectedRecord):
        convert('cb', raw)


def test_shared_paraphrase_sentence_connects_whole_pairs():
    rows = [convert('qqp', dict(question1='A?', question2='B?', idx=1, label=1)),
            convert('qqp', dict(question1='B?', question2='C?', idx=2, label=0))]
    group_rows(rows)
    assert rows[0]['group'] == rows[1]['group']
    assert rows[0]['split'] == rows[1]['split']
    assert rows[1]['answer'] == 'no'


def test_copa_keeps_cause_and_effect_explicit():
    raw = dict(premise='The ground is wet.', choice1='It rained.', choice2='The sun shone.',
               idx=1, label=0, question='cause')
    assert 'cause' in convert('copa', raw)['prompt']
    assert convert('copa', raw)['answer'] == 'It rained.'
    raw['question'] = 'effect'
    assert 'effect' in convert('copa', raw)['prompt']
    raw['question'] = 'other'
    with pytest.raises(ValueError):
        convert('copa', raw)


def test_multirc_keeps_negative_answers_and_passage_groups():
    raw = dict(paragraph='A passage.', question='A question?', answer='Wrong option',
               idx=dict(paragraph=1, question=1, answer=0), label=0)
    a = convert('multirc', raw)
    raw['idx']['answer'] = 1
    raw['label'] = 1
    raw['answer'] = 'Correct option'
    b = convert('multirc', raw)
    assert a['answer'] == 'no' and b['answer'] == 'yes'
    group_rows([a, b])
    assert a['group'] == b['group']


def test_wic_marks_the_supplied_occurrence():
    raw = dict(word='bank', sentence1='The bank is open.', sentence2='A bank by the river.',
               start1=4, end1=8, start2=2, end2=6, idx=1, label=0)
    row = convert('wic', raw)
    assert row['prompt'].count('[TARGET]bank[/TARGET]') == 2
    assert row['answer'] == 'no'


def test_emotions_are_multilabel_not_arbitrary_first_label():
    row = convert('go_emotions', dict(text='Thanks! I am happy.', id='1', labels=[17, 15]))
    assert row['answer'] == 'gratitude; joy'
    assert score_wave6(row, 'joy; gratitude')['correct']
    assert not score_wave6(row, 'joy')['correct']
    assert score_wave6(row, 'joy')['label_f1'] == pytest.approx(2/3)
    assert not score_wave6(row, 'gratitude; joy; invented')['correct']


def test_medqa_checks_original_option_key_and_ignores_derived_phrases():
    raw = dict(question='Which option?', options={'A':'one','B':'two','C':'three','D':'four'},
               answer='two', answer_idx='B', metamap_phrases=['do not train this field'])
    row = convert('medqa', raw, '1')
    assert row['answer'] == 'two'
    assert 'do not train' not in text_of(row)
    assert score_wave6(row, 'B')['correct']
    raw['answer_idx'] = 'A'
    with pytest.raises(RejectedRecord):
        convert('medqa', raw, '1')


def test_logiqa_original_answer_and_source_count():
    raw = dict(text='A rule.', question='Which follows?', options=['a','b','c','d'], answer=2, id=1)
    row = convert('logiqa', raw)
    assert row['answer'] == 'c' and row['human_translated']


def test_summary_metric_does_not_claim_correctness_or_factuality():
    row = convert('samsum', dict(dialogue='A: Hello.\nB: Hi.', summary='Two people greet each other.', id='1'))
    result = score_wave6(row, row['answer'])
    assert result['token_f1'] == 1
    assert 'correct' not in result
    assert not result['official_benchmark_score']
    assert dialogue_key('A: Hello.\nB: Hi.') == dialogue_key('Other: Hello.\nPerson: Hi.')


def test_wave6_protects_parent_confirmation_and_keeps_parent_arrays(tmp_path):
    base, stage, output = [tmp_path/x for x in ('base', 'stage', 'out')]
    base.mkdir(); (stage/'toy').mkdir(parents=True)
    tok = Tokenizer(models.WordLevel({'<unk>':0, 'parent':1, 'yes':2}, unk_token='<unk>'))
    tok.pre_tokenizer = pre_tokenizers.Whitespace()
    tok.add_special_tokens(['<bos>', '<eos>', '<question>', '<answer>', '<pad>'])
    tok.save(str(base/'tokenizer.json'))
    inherited = dict(source='parent', original_split='train', original_id='p', group='p',
                     split='train', prompt='Parent task', answer='yes')
    reserved = dict(inherited, group='reserved', split='confirmation',
                    prompt='Read.\n\nPassage: secret context\n\nQuestion: hidden?')
    (base/'records.jsonl').write_text(json.dumps(inherited)+'\n')
    (base/'confirmation.jsonl').write_text(json.dumps(reserved)+'\n')
    (base/'train.bin').write_bytes(b'original parent bytes')
    manifest = dict(version=5, sources={'parent':{}}, counts={}, tokenizer={'sha256':sha(base/'tokenizer.json')},
                    records_sha256=sha(base/'records.jsonl'), confirmation_sha256=sha(base/'confirmation.jsonl'),
                    derived_files_sha256={'train.bin':sha(base/'train.bin')})
    (base/'manifest.json').write_text(json.dumps(manifest))
    (stage/'toy/train.txt').write_text('toy data')
    (stage/'manifest.json').write_text(json.dumps(dict(sources={'toy': dict(original_split='train', files=[dict(path='train.txt', sha256=sha(stage/'toy/train.txt'))])})))
    def reader(*args):
        for i in range(200):
            context = 'secret context' if i == 0 else str(i)
            yield str(i), dict(source='toy', original_id=str(i), original_split='train', variant=0,
                               prompt='Toy ' + str(i), answer='yes', language='english', original_labels=['yes'],
                               _identities=[key('context',context)], _checks=[key('context',context)])
    profile = SimpleNamespace(ADMITTED=('toy',), convert=lambda s,r,u: copy.deepcopy(r), original_rows=reader,
                              FAMILIES={'family':['parent','toy']}, PARENT_VERSION=5, PARENT_SOURCES=1,
                              VERSION=6, RejectedRecord=RejectedRecord, extra_old_keys=lambda r: [])
    prepare(base, stage, output, profile=profile)
    audit = json.loads((output/'audit.json').read_text())
    assert audit['rejections']['toy.overlap_group'] == 1
    assert output.joinpath('train.bin').is_symlink()
    assert output.joinpath('train.bin').read_bytes() == b'original parent bytes'
    assert (output/'confirmation.jsonl').read_text().startswith(json.dumps(reserved)+'\n')
    assert sum(v['records'] for v in audit['new_counts'].values()) == 199
    with pytest.raises(ValueError, match='overwrite'):
        prepare(base, stage, output, profile=profile)


def test_small_holdouts_gain_missing_class_without_group_leakage():
    from benchmark_expansion.wave6 import balance_small_holdouts
    rows = [dict(source='cb', group=str(i//2), split='train', original_labels=['neutral']) for i in range(10)]
    changes = balance_small_holdouts(rows, set())
    assert len(changes) == 2
    assert {r['split'] for r in rows} == {'train','dev','confirmation'}
    for group in {r['group'] for r in rows}:
        assert len({r['split'] for r in rows if r['group'] == group}) == 1
