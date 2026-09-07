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


def sampling_weights(sources, mode='families'):
    """Choose equal family mass or equal source mass, retaining every available source."""
    sources = set(sources)
    unknown = sources - SOURCE_FAMILY.keys()
    if unknown:
        raise ValueError(f'Unmapped sources: {unknown}')
    if mode == 'sources':
        return {source: 1 / len(sources) for source in sorted(sources)}
    if mode != 'families':
        raise ValueError(mode)
    groups = {key: sorted(set(values) & sources) for key, values in FAMILIES.items()}
    groups = {key: values for key, values in groups.items() if values}
    return {source: 1 / len(groups) / len(values) for values in groups.values() for source in values}
