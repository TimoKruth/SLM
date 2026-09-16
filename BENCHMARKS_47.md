# Active 47-source catalog

Prepared 16 September 2026. Every listed source contributes to the new training pool. This is a data/coverage catalog, not a model-result report.

| Family | Sources |
| --- | --- |
| commonsense_and_social | hellaswag, winogrande, piqa, commonsenseqa, social_i_qa, cosmos_qa, wsc, go_emotions |
| dialogue | dream |
| entailment | snli, anli, scitail, multinli, cb |
| factual_knowledge | triviaqa |
| language_meaning | mrpc, qqp, wic |
| logical_reasoning | logiqa |
| mathematics | gsm8k, math, aqua_rat, tabmwp |
| medical_knowledge | medqa |
| multilingual_reading | tydiqa |
| programming_and_queries | apps, mbpp, code_contests, spider, wikisql |
| reading_and_extraction | squad, boolq, ropes, drop, hotpotqa, quoref, race, multirc |
| science_and_causality | arc, sciq, openbookqa, qasc, quartz, quarel, wiqa, copa |
| summarization | samsum |

Sampling gives equal sequence mass to each family, then each source within the family. Medical knowledge and multilingual reading are internal research tasks; their presence does not establish real-world reliability.

| Source | Training records | Dev suite | Confirmation suite |
| --- | ---: | ---: | ---: |
| anli | 155,358 | 32 | 32 |
| apps | 30,654 | 32 | 32 |
| aqua_rat | 92,558 | 32 | 32 |
| arc | 3,193 | 32 | 32 |
| boolq | 8,969 | 32 | 32 |
| cb | 232 | 10 | 8 |
| code_contests | 39,520 | 32 | 32 |
| commonsenseqa | 9,274 | 32 | 32 |
| copa | 343 | 32 | 25 |
| cosmos_qa | 24,014 | 32 | 32 |
| dream | 5,781 | 32 | 32 |
| drop | 68,750 | 32 | 32 |
| go_emotions | 38,839 | 32 | 32 |
| gsm8k | 7,092 | 32 | 32 |
| hellaswag | 37,777 | 32 | 32 |
| hotpotqa | 5,969 | 0 | 0 |
| logiqa | 10,497 | 32 | 32 |
| math | 6,969 | 32 | 32 |
| mbpp | 359 | 8 | 7 |
| medqa | 9,166 | 32 | 32 |
| mrpc | 3,316 | 32 | 32 |
| multinli | 353,453 | 32 | 32 |
| multirc | 24,166 | 17 | 20 |
| openbookqa | 4,675 | 32 | 32 |
| piqa | 14,069 | 32 | 32 |
| qasc | 7,718 | 32 | 32 |
| qqp | 329,554 | 32 | 32 |
| quarel | 1,854 | 32 | 32 |
| quartz | 2,610 | 4 | 4 |
| quoref | 18,135 | 32 | 32 |
| race | 82,884 | 32 | 32 |
| ropes | 10,549 | 10 | 10 |
| samsum | 12,407 | 32 | 32 |
| sciq | 11,088 | 32 | 32 |
| scitail | 21,875 | 32 | 32 |
| snli | 520,773 | 32 | 32 |
| social_i_qa | 31,764 | 32 | 32 |
| spider | 6,400 | 5 | 4 |
| squad | 82,630 | 13 | 12 |
| tabmwp | 20,655 | 32 | 32 |
| triviaqa | 68,888 | 32 | 32 |
| tydiqa | 33,148 | 32 | 32 |
| wic | 4,921 | 32 | 32 |
| wikisql | 53,390 | 32 | 32 |
| winogrande | 38,471 | 32 | 32 |
| wiqa | 28,387 | 5 | 4 |
| wsc | 489 | 13 | 21 |

**Total:** 2,343,583 training records; 1,269 development tasks; 1,267 confirmation tasks. Both suites cover 46 sources. HotpotQA remains training-only because inherited document grouping leaves no safely separated holdout. Small-source deficits are shown rather than filled with overlapping examples.

Each suite has 1,064 correctness-scored tasks. Remaining tasks have reference loss and limited code/SQL/narrative/summary proxies. All task denominators and metrics must accompany future scores. Source revisions and file checksums are retained in the local manifest; the expansion lockfiles remain in `benchmark_expansion/`. Data originates from original training splits. Dataset terms remain source-specific; no blanket redistribution permission is implied.

See [the training plan](FRESH_47_TRAINING.md) for preparation checks, endpoints and limitations. All previous catalog/result reports are deprecated in [the report archive](archives/README.md).
