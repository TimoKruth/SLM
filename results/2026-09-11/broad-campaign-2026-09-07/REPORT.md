# Broad mixture comparison

Same architecture, tokenizer, examples and training wall-clock budget; only sampling weights differ. Actual source-token exposure is reported separately.

| Capability | Equal families | Equal sources |
| --- | ---: | ---: |
| commonsense_and_social | 0.125 | 0.083 |
| dialogue | 0.333 | 0.500 |
| entailment | 0.500 | 0.500 |
| mathematics | 0.000 | 0.000 |
| reading_and_extraction | 0.111 | 0.167 |
| science_and_causality | 0.143 | 0.167 |

Narrative and SQL execution quality require separate assessment; no aggregate score is used to hide these gaps.
Next prepared stage: compare the smaller model with the same broad mixture, then choose any longer continuation from the observed learning curves. No automatic specialization or external-test opening.
