# Fresh 47-source / 97M — final evaluation

Training ended at the user's request, at **215,720 updates / 394,558,006 tokens**. Final checkpoint: `checkpoint-0215720` (97,536,768 parameters).

User requested stopping training early because recent improvements appeared unlikely to help. Final chronological checkpoint after the requested stop is evaluated, not the checkpoint with the best development loss. This endpoint timing was chosen after observing development results; confirmation had not been inspected when the early endpoint was chosen.

The best periodic development loss was 1.179134 at 326,701,345 tokens. After 67,856,661 more tokens, final periodic development loss was 1.190955. This supports a plateau in this diagnostic, not proof that no further training could help.

## Final task performance

| Suite | Generated tasks | Correct / scored | Mixed scored-item rate | Unscored tasks |
| --- | ---: | ---: | ---: | ---: |
| Development | 1,269 | 315 / 1064 | 29.6% | 205 |
| Confirmation (primary) | 1,267 | 300 / 1064 | 28.2% | 203 |

The pooled rate is a descriptive mixture of task-specific internal scoring rules, not an official benchmark or a general intelligence score. Family accuracy below averages source accuracies equally; counts show the actual scored denominators.

| Family | Dev mean source accuracy | Confirmation mean source accuracy | Confirmation correct / scored |
| --- | ---: | ---: | ---: |
| entailment | 60.1% | 60.0% | 75 / 136 |
| programming and queries | unscored | unscored | 0 / 0 |
| mathematics | 4.7% | 8.6% | 11 / 128 |
| science and causality | 26.5% | 24.9% | 42 / 193 |
| reading and extraction | 28.5% | 20.4% | 33 / 170 |
| commonsense and social | 30.4% | 30.6% | 55 / 181 |
| dialogue | 25.0% | 15.6% | 5 / 32 |
| logical reasoning | 3.1% | 6.2% | 2 / 32 |
| medical knowledge | 25.0% | 25.0% | 8 / 32 |
| language meaning | 65.6% | 67.7% | 65 / 96 |
| summarization | unscored | unscored | 0 / 0 |
| factual knowledge | 0.0% | 3.1% | 1 / 32 |
| multilingual reading | 15.6% | 9.4% | 3 / 32 |

## Confirmation source results

| Source | Metric | Correct / scored | Generated |
| --- | --- | ---: | ---: |
| anli | answer_match | 15 / 32 | 32 |
| apps | syntax_only_not_functional | 0 / 0 | 32 |
| aqua_rat | final_answer_match | 3 / 32 | 32 |
| arc | answer_match | 5 / 32 | 32 |
| boolq | answer_match | 17 / 32 | 32 |
| cb | original_label_or_answer_match | 7 / 8 | 8 |
| code_contests | syntax_only_not_functional | 0 / 0 | 32 |
| commonsenseqa | answer_match | 4 / 32 | 32 |
| copa | original_label_or_answer_match | 3 / 25 | 25 |
| cosmos_qa | answer_match | 7 / 32 | 32 |
| dream | answer_match | 5 / 32 | 32 |
| drop | answer_exact_and_token_f1 | 1 / 32 | 32 |
| go_emotions | emotion_label_set_exact_and_f1 | 12 / 32 | 32 |
| gsm8k | final_answer_match | 0 / 32 | 32 |
| hellaswag | unscored_open_generation | 0 / 0 | 32 |
| logiqa | original_label_or_answer_match | 2 / 32 | 32 |
| math | final_answer_match | 0 / 32 | 32 |
| mbpp | syntax_only_not_functional | 0 / 0 | 7 |
| medqa | original_label_or_answer_match | 8 / 32 | 32 |
| mrpc | original_label_or_answer_match | 18 / 32 | 32 |
| multinli | original_label_or_answer_match | 11 / 32 | 32 |
| multirc | original_label_or_answer_match | 10 / 20 | 20 |
| openbookqa | answer_match | 6 / 32 | 32 |
| piqa | unscored_open_generation | 0 / 0 | 32 |
| qasc | final_answer_match | 3 / 32 | 32 |
| qqp | original_label_or_answer_match | 26 / 32 | 32 |
| quarel | answer_match | 15 / 32 | 32 |
| quartz | answer_match | 1 / 4 | 4 |
| quoref | answer_exact_and_token_f1 | 1 / 32 | 32 |
| race | answer_match | 1 / 32 | 32 |
| ropes | answer_exact_and_token_f1 | 3 / 10 | 10 |
| samsum | summary_unigram_f1_proxy_not_factuality | 0 / 0 | 32 |
| sciq | answer_match | 7 / 32 | 32 |
| scitail | answer_match | 21 / 32 | 32 |
| snli | answer_match | 21 / 32 | 32 |
| social_i_qa | answer_match | 14 / 32 | 32 |
| spider | sql_text_match_not_execution | 0 / 0 | 4 |
| squad | answer_exact_and_token_f1 | 0 / 12 | 12 |
| tabmwp | original_answer_exact_proxy | 8 / 32 | 32 |
| triviaqa | original_answer_exact_proxy | 1 / 32 | 32 |
| tydiqa | original_answer_exact_proxy | 3 / 32 | 32 |
| wic | original_label_or_answer_match | 21 / 32 | 32 |
| wikisql | sql_text_match_not_execution | 0 / 0 | 32 |
| winogrande | answer_match | 11 / 32 | 32 |
| wiqa | answer_match | 2 / 4 | 4 |
| wsc | original_label_or_answer_match | 7 / 21 | 21 |

## Closed-label concentration (confirmation)

Post-hoc label-distribution diagnostic, not a pre-registered or training-derived baseline. A high repeated-label proportion warns that apparent accuracy may reflect class composition.

| Source | Distinct predictions | Most common prediction count | Most common reference-label count | Total |
| --- | ---: | ---: | ---: | ---: |
| boolq | 2 | 27 | 18 | 32 |
| wic | 2 | 21 | 18 | 32 |
| mrpc | 2 | 27 | 21 | 32 |
| qqp | 2 | 25 | 25 | 32 |
| snli | 3 | 12 | 15 | 32 |
| scitail | 2 | 22 | 19 | 32 |
| anli | 3 | 16 | 15 | 32 |
| multinli | 3 | 12 | 32 | 32 |
| cb | 2 | 6 | 5 | 8 |

## Other diagnostics

Confirmation response stop reasons: `{"special_token": 1192, "token_limit": 75}`. Empty responses: 0.
Confirmation limited proxies: `{"go_emotions_label_f1": {"count": 32, "mean": 0.3958333333333333}, "nonempty": {"count": 64, "positive": 64}, "samsum_token_f1": {"count": 32, "mean": 0.3419950899219418}, "syntax_valid": {"count": 71, "positive": 38}, "text_match": {"count": 36, "positive": 5}}`.
Teacher-forced answer loss on the fixed suites: dev 1.163554; confirmation 1.164358. These use their fixed suites; they are distinct from the periodic training diagnostic. Lower reference loss does not establish free-answer correctness.

## Practical assessment of this run

The evaluated model is stronger on short label-based language tasks than on broad free-answer capability. The results do not establish a reliable general-purpose assistant. Loss convergence alone overstated how much practical capability had been gained.
Class composition matters. qqp: 26/32 correct, versus 25/32 for the most frequent reference label. boolq: 17/32 correct, versus 18/32 for the most frequent reference label. mrpc: 18/32 correct, versus 21/32 for the most frequent reference label. multinli: 11/32 correct, versus 32/32 for the most frequent reference label. These post-hoc observations expose limitations of the small suite; they are not separately trained baselines or grounds for changing these reported scores.
GSM8K scored 0/32 and MATH 0/32 under this generation protocol. However, 6 GSM8K and 28 MATH responses reached the 256-token cap, so failure can include unfinished answers as well as reasoning/format errors. This evaluation does not isolate those causes or establish what a longer answer budget would achieve.
Code syntax passed for 38/71 samples and SQL text matched for 5/36. Neither is a functional correctness result. Summary unigram F1 was 0.342 across 32 samples; summary factuality was not evaluated.

## Coverage and interpretation

- All 47 sources trained the model; both evaluation suites cover 46 sources. HotpotQA has no safely separated direct holdout and is training-only.
- Most sources have at most 32 questions; several have smaller quota deficits. Source percentages are coarse and uncertain. These are internal proxies, not official benchmark scores.
- Code syntax validity is not functional code correctness; SQL text matching is not execution correctness; summary lexical overlap is not factuality. Open-generation narrative tasks lack correctness scoring.
- Exact prompt-answer and group separation is enforced for this fresh run, not semantic independence. Some inherited holdout groups were used in older experiments; confirmation is held out from this model, not universally unseen research data.
- Final checkpoint selection was chronological, but the early stopping time was chosen after inspecting development behavior. There is no best-checkpoint substitution.
- Qwen has not been evaluated. No fresh-vs-legacy score or cross-tokenizer-loss comparison is valid; all older runs remain deprecated and ZIP-only.

## Execution and provenance

Device: Apple M1 Max; physical memory 64 GiB. FP32 training, light monitoring. Maximum sampled MLX peak: 5.573 GB; minimum sampled available system RAM: 25.68 GB.
Median of recorded training-throughput samples: 5,872 tokens/s (not a time-weighted or end-to-end throughput). Cumulative controller time before final evaluation: 20.23 hours, including checks, checkpointing and periodic development evaluation; user/power pauses are recorded separately.
Mains power, a free GPU lease, fresh PowerWatch observations and memory were checked before final evaluation. No numerical/data/scorer inputs were modified. Both evaluations use the same final-checkpoint hash and the original fixed suites, 256 maximum new tokens, greedy decoding, no functional code execution, and reference-answer loss.
Frozen inputs verified: 337. Plan SHA256: `6b963b91190e9c7b691b60304d5994b46d5465f27c2c4e00c49ab1e4139c8740`. Final model SHA256: `00e4435ad8e3ed50a5a71951e76d6298f320ee6d76909b9d0b69b9c557eb3ba6`.
Aggregate evidence is in `aggregate.json`; raw responses, model/optimizer weights, data and process logs stay local.
