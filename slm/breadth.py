"""Capability groups shared by sampling and evaluation; no coding-first aggregate."""
FAMILIES = {
    'programming_and_queries': ['apps', 'mbpp', 'code_contests', 'spider', 'wikisql'],
    'mathematics': ['gsm8k', 'math', 'aqua_rat'],
    'reading_and_extraction': ['squad', 'boolq', 'ropes', 'drop', 'hotpotqa', 'quoref', 'race'],
    'commonsense_and_social': ['hellaswag', 'winogrande', 'piqa', 'commonsenseqa', 'social_i_qa', 'cosmos_qa'],
    'science_and_causality': ['arc', 'sciq', 'openbookqa', 'qasc', 'quartz', 'quarel', 'wiqa'],
    'entailment': ['snli', 'anli', 'scitail'],
    'dialogue': ['dream'],
}
SOURCE_FAMILY = {source: family for family, sources in FAMILIES.items() for source in sources}

# Explicit opt-in for a new data version; historical 32-source defaults stay fixed.
EXPANSION_FAMILIES = {name: list(sources) for name, sources in FAMILIES.items()}
EXPANSION_FAMILIES['mathematics'].append('tabmwp')
EXPANSION_FAMILIES['factual_knowledge'] = ['triviaqa']
EXPANSION_FAMILIES['multilingual_reading'] = ['tydiqa']
BENCHMARK47_FAMILIES = {name: list(sources) for name, sources in EXPANSION_FAMILIES.items()}
BENCHMARK47_FAMILIES['entailment'] += ['multinli', 'cb']
BENCHMARK47_FAMILIES['science_and_causality'].append('copa')
BENCHMARK47_FAMILIES['reading_and_extraction'].append('multirc')
BENCHMARK47_FAMILIES['commonsense_and_social'] += ['wsc', 'go_emotions']
BENCHMARK47_FAMILIES['language_meaning'] = ['mrpc', 'qqp', 'wic']
BENCHMARK47_FAMILIES['logical_reasoning'] = ['logiqa']
BENCHMARK47_FAMILIES['medical_knowledge'] = ['medqa']
BENCHMARK47_FAMILIES['summarization'] = ['samsum']
EVALUATION_SOURCE_FAMILY = {
    source: family for family, sources in BENCHMARK47_FAMILIES.items() for source in sources
}


def sampling_weights(sources, mode='families', *, families=None):
    """Choose equal family mass or equal source mass, retaining every available source."""
    sources = set(sources)
    families = FAMILIES if families is None else families
    mapped = {source for members in families.values() for source in members}
    unknown = sources - mapped
    if unknown:
        raise ValueError(f'Unmapped sources: {unknown}')
    if mode == 'sources':
        return {source: 1 / len(sources) for source in sorted(sources)}
    if mode != 'families':
        raise ValueError(mode)
    groups = {key: sorted(set(values) & sources) for key, values in families.items()}
    groups = {key: values for key, values in groups.items() if values}
    return {source: 1 / len(groups) / len(values) for values in groups.values() for source in values}
