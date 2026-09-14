**JEPA and the benchmark-only SLM project — research assessment, 14 September 2026**

My recommendation is to investigate JEPA as an additional learning objective, beginning with a small Semantic Tube Prediction experiment. The more ambitious research direction is a model that learns reusable transitions between problem states from benchmark solutions. Neither is a demonstrated improvement for this project yet.

This is research and a proposed experiment sequence, not an implementation or training authorization. No model weights, datasets, frozen campaign inputs, running processes, or evaluation suites were changed. Literature was checked through the date above. Paper results, repository observations, and my proposed adaptations are distinguished below.

**What JEPA contributes**

JEPA means Joint-Embedding Predictive Architecture. An encoder represents an observed input, a predictor estimates the representation of a related target, and a target encoder supplies the learning target. The prediction error is measured between representations rather than reconstructed pixels or words. A predictor can also receive information about the requested location, action, or prediction horizon. This is a family of objectives and designs; it does not require replacing a Transformer. [I-JEPA, 2023](https://arxiv.org/html/2301.08243v3)

For an illustrative language adaptation:

```text
problem ── encoder ── predictor ── predicted solution representation
                                               │
                                      representation loss
                                               │
original solution ── target encoder ── target representation

problem ── existing causal decoder ── generated answer
                                      token loss during training
```

The target solution is available during training only. The bottom path preserves the ability to produce actual answers. The predicted vector is not automatically a readable answer, a verified proof, or a planning procedure.

I-JEPA uses an exponential-moving-average target encoder and an asymmetric predictor to resist collapse. Without an effective constraint, encoders can map everything to the same vector and make prediction trivial. These particular mechanisms are not mandatory for every JEPA variant. [I-JEPA method](https://arxiv.org/html/2301.08243v3)

LeCun's original proposal places hierarchical predictive representations inside a larger system with memory, objectives, and planning. Adding an embedding loss alone does not implement that whole system. [A Path Towards Autonomous Machine Intelligence, 2022](https://openreview.net/forum?id=BZ5a1r-kVsf)

**The evidence most relevant to this decision**

| Work | What it establishes or reports | Relevance and limit here |
| --- | --- | --- |
| [LLM-JEPA, v2, October 2025](https://arxiv.org/html/2509.14252v2) | Combines token loss with cross-view embedding prediction; tests language tasks including GSM8K and Spider. Uses shared language-model weights and predictor tokens. The revised implementation needs one extra forward pass, with independently masked views. | Closest direct precedent. Evidence is mainly fine-tuning larger pretrained models. Its limited random-initialization experiment uses a relaxed prefix-correct metric because termination was unreliable. It does not establish success for a 27M benchmark-only model. |
| [Semantic Tube Prediction, February 2026](https://arxiv.org/html/2602.22617v1) | Regularizes the directions of hidden-state changes across token positions while retaining token loss. Reuses the ordinary forward pass and needs no separately constructed paired views. | Most attractive inexpensive probe. Its 16× unique-data reduction is on NL-RX-SYNTH fine-tuning, with proportionally more epochs on the smaller subsets. It is not a 16× compute reduction or evidence that broad pretraining scaling laws have been overturned. |
| [data2vec, 2022](https://arxiv.org/abs/2202.03555) | Predicts contextual representations of a full input from a masked view; includes language experiments. | Relevant precedent for an auxiliary text encoder. Its language-understanding results do not establish autonomous free-answer generation. |
| [V-JEPA 2, June 2025](https://arxiv.org/abs/2506.09985) | Combines video representation learning with action-conditioned learning from robot trajectories for planning. | Inspires learning transitions from benchmark solution steps. The project has neither comparable video observations nor robot interaction data, so this is an analogy, not a directly transferable recipe. |
| [VL-JEPA, v2, February 2026](https://arxiv.org/abs/2512.10942) | Predicts target text embeddings from visual/query inputs and invokes a text decoder when needed. | Supports the architectural idea of separating semantic prediction and verbalization. Its visual-language setup and pretrained components do not satisfy this project's provenance constraints. |
| [LeJEPA, November 2025](https://arxiv.org/abs/2511.08544) | Introduces SIGReg to constrain embedding distributions, avoiding the usual teacher/stop-gradient machinery in its formulation. | A possible anti-collapse alternative. Its theory has assumptions, and its vision evidence does not guarantee useful semantics or stable learning with this project's tiny batches. |
| [DLLM-JEPA, May 2026](https://arxiv.org/abs/2606.00091) | Uses masked diffusion language models to construct views and reports fine-tuning improvements. | Interesting future branch, but changing to diffusion would confound architecture, objective, and decoding. Poor first experiment here. |
| [The JEPA Paradox in Language, July 2026](https://arxiv.org/abs/2607.23531) | A recent preprint argues that deterministic squared-error prediction can average incompatible linguistic alternatives and reports degenerating representations in its text experiments. | A warning against naive masked-span regression. It is not a general impossibility result for language JEPA, and its criticism should not be extended automatically to every objective above. |

The authors' [LLM-JEPA repository](https://github.com/galilai-group/llm-jepa) also provides intermittent auxiliary-loss computation and compute-matched comparisons. The implementation uses PyTorch/Hugging Face, with CUDA-specific code paths. Treat it as a reference for a small MLX port, not a launcher for this machine. Repository `main` is mutable; an implementation study should pin an exact commit.

**Why this project is a plausible testbed**

The project asks whether benchmark training material alone can teach reusable capabilities. JEPA offers a different way to exploit the relationships already present in that material. A question, an explanation, a formal solution, and an equivalent formulation can encode related knowledge in different forms. No outside teacher is inherently required.

The inspected [model](slm/model.py) is a causal Transformer with RoPE, RMSNorm, gated feed-forward layers, and tied input/output embeddings. Its normal call returns vocabulary logits. The current objective is full next-token cross-entropy over non-padding tokens; answer masks exist in the [sampler](slm/data.py), but are not used by the ordinary `loss_fn` to make training answer-only. The [compiled update](slm/optimization.py) imports that loss directly. These are straightforward extension points, though a safe experimental branch must preserve the baseline path.

The established small configuration has 27,294,208 parameters, width 512, six layers, eight heads, and a 1,024-token context; the larger has 97,536,768 parameters. The documented machine is an M1 Max with 64 GB unified memory. See [size-comparison design](MODELLGROESSENVERGLEICH.md). These facts make an auxiliary objective on the small model more plausible than importing a billion-parameter JEPA system.

The [historical findings](ERKENNTNISSE.md) show that lower reference loss has not consistently translated into better generated answers. That motivates testing representation objectives, but does not diagnose the cause: weighting, decoding, data limitations, and evaluation noise also remain possible explanations. I have not inferred a new live campaign result from that historical document.

Keep two data states separate: the ongoing experimental line uses corrected v4 with 32 sources; the prepared [v6 expansion](BENCHMARKS_47.md) has 47 sources, 13 families, and 2,344,017 training pairs. The expansion has not thereby become an authorized training run. Start an objective comparison on one fixed data version; changing both data and loss would obscure the result.

**Candidate approaches, ordered by practical value**

1. **Add Semantic Tube Prediction to the existing decoder.** This is my first experiment. The auxiliary term aligns successive hidden-state displacement directions at selected positions; the original token objective stays active. See the [paper](https://arxiv.org/html/2602.22617v1) and [reference implementation](https://raw.githubusercontent.com/galilai-group/llm-jepa/main/stp.py).

   My adaptation would sample only within individual complete records, exclude padding and formatting-only spans, and explicitly track coverage across sources. Sampling random triplets and sampling at reasoning-step boundaries should be separate variants. Some records contain only a short label; forcing them through the same policy as a long mathematical solution could create an unhelpful bias. Test whether any benefit survives free generation, especially exact numbers, negation, and termination. Straight-looking representations are not an endpoint.

2. **Predict a substantial solution representation from its problem.** This is the clearest direct JEPA experiment. Begin with original question/solution pairs in GSM8K, MATH, QASC, and SQL tasks. QASC's converter already preserves its two supporting facts in the answer; the math converters retain original explanations. APPS also retains multiple original reference solutions. These observations come from [prepare.py](slm/prepare.py) and [prepare_v2.py](slm/prepare_v2.py).

   Keep generation loss on every ordinary training batch, and apply a separate representation objective to eligible examples. A small predictor can operate on the final prompt state; encode the target solution independently so its representation cannot be obtained by copying the prompt. This MLP-based variant is my adaptation, not an exact reproduction of the predictor-token paper.

   For the first direct reproduction, preserve the published shared-weight objective. An EMA target is a separate alternative, not an unnoticed substitution. Use an immutable project checkpoint if choosing a fixed teacher; it respects the no-external-weights constraint but inherits the teacher's weaknesses. There is no reason to expect a frozen random target encoder to supply rich semantic supervision.

3. **Learn equivalence while preserving relationships.** The prepared MRPC/QQP positives can supply equivalent text views; negative pairs must not be pulled together. Existing multiple solutions can teach that different implementations solve one task. A more informative objective on NLI or WIQA would predict a relation-dependent representation, rather than treating entailment, contradiction, and causal direction as interchangeable similarity.

   The hypothesis is that this encourages transfer between formulations. Compare against ordinary supervised relation classification and contrastive learning: any gain may come from using the labels better, rather than from JEPA specifically. Some equivalence operations can be constructed deterministically from existing training records, but must be audited. Renaming variables is not always semantics-preserving in Python; changing numbers is not label-preserving unless the answer is recomputed correctly. Such derivatives belong to a declared new data condition.

4. **Predict the next reasoning state.** Split original, usable worked solutions into steps and train a predictor from the problem plus a solution prefix to a representation of a later step. Add the step distance as input and compare one-step with multi-step targets. Mathematical calculation, combining QASC facts, and successive SQL operations provide different domains; this need not become a coding-only experiment.

   Begin as an auxiliary training loss while the model still generates normal text. The central test is whether it solves new combinations of known operations. A text line is not automatically a valid reasoning step, and many benchmark answers contain no usable trajectory. Coverage and segmentation quality must be measured before planning a large study.

5. **Use representations to retrieve helpful training examples.** Build a memory containing only original training records, retrieve by the predicted problem/solution representation, and condition the decoder on relevant examples. This could reduce the amount the small model must store in its weights.

   Compare with lexical retrieval, ordinary decoder embeddings, and the same retrieved context budget. Split related task groups before indexing; held-out references must never enter memory. Report retrieval-assisted and model-only scores separately. A gain would establish a better system, not necessarily better knowledge stored in the model.

6. **Train a latent plan and a separate verbalizer.** Let a predictor produce a short sequence of latent states, then condition the text decoder on that sequence. During training, include predicted plans rather than only plans encoded from the correct answer; otherwise the decoder could learn to depend on information unavailable at inference.

   Test whether shuffling or zeroing the plan changes answers. If it does not, the decoder has learned to ignore the expensive component. Compare against the same extra parameters and inference compute spent on ordinary decoding. This has conceptual neighbors in [Coconut](https://arxiv.org/abs/2412.06769) and [Large Concept Models](https://arxiv.org/abs/2412.08821), but neither should be presented as an interchangeable JEPA implementation. All encoders and decoders here would have to originate within the project's permitted training process.

**The wilder directions worth keeping**

My favorite speculative direction is **a world model of solving problems**. Treat a partially solved task as a state, a reasoning operation as an action, and the changed task as the next state. An operation could be selecting evidence, substituting into an equation, eliminating a contradicted option, or executing a query. Learn a shared transition predictor across capabilities. Then search over short sequences of operations and verbalize a chosen path.

This gives a concrete version of the idea that benchmarks contain more than answers: some contain traces of how problems change under valid operations. The connection to action-conditioned prediction is inspired by [V-JEPA 2](https://arxiv.org/abs/2506.09985); applying it across benchmark reasoning domains is my hypothesis. It requires an action vocabulary, grounded transition targets, and a success criterion. Static question/answer pairs alone do not identify arbitrary counterfactual dynamics.

An even more ambitious extension would create **verified alternative trajectories** by executing benchmark-derived arithmetic, SQL, or code operations. A learned model could predict which operation is useful; an exact checker would confirm selected transitions. Any interpreter runs need isolation and resource bounds. New generated trajectories alter the current original-reference-only setup and must be named as a separate benchmark-derived-data experiment. They are not implicitly authorized by this research request.

Three other speculative extensions:

- **Several possible internal futures.** Predict a small set or distribution of candidate solution states rather than one vector, then score or verify them. Multiple valid reference solutions can supervise some of this. Merely adding heads can produce duplicate predictions; require useful diversity and compare with equal-cost ordinary sampling. Embedding distance is not a calibrated correctness probability.
- **A shared algebra of reasoning operations.** Test whether a learned operation such as composition or elimination transfers between math, logical relations, and database questions. Hold out combinations and task families before training. A shared module that only recognizes dataset templates would fail the intended test.
- **A curriculum based on learning progress.** Use declining prediction error, together with correctness and uncertainty, to allocate training examples. Raw high JEPA error can mean ambiguity, bad references, or impossibility; sampling only those examples may waste the budget. Maintain minimum family coverage and compare against the existing balanced sampler.

**The engineering details that decide whether a result is credible**

The existing sampler packs several examples into one causal sequence and returns token, real-token, and answer masks, but not explicit record IDs or pair indices. Causal attention can see earlier packed records. A new objective therefore needs record boundaries and deliberate attention semantics. A triplet crossing two unrelated tasks would train the wrong relationship. Independent paired encodings require genuine isolation; ordinary causal masking by itself does not isolate the second view from the first.

For an initial STP arm, preserve the baseline attention behavior and ensure triplets stay within records. If the experiment also changes cross-record attention or packing, apply that change identically to its controls. For a paired-view arm, isolate the auxiliary views through separate encodings or a verified mask. Never pool all tokens in a packed row into one solution target.

Expose hidden states before the tied vocabulary projection without changing the default `LanguageModel.__call__`. Validate zero auxiliary weight against the baseline update on identical batches. Because the compiled update captures state, any predictor parameters must be included in optimization and any teacher state updated deliberately. Checkpoints need the new objective configuration, predictor/teacher states when applicable, and the independent random state used for selecting spans or views. Architecture, objective, and tokenizer changes belong in the resume signature.

STP can avoid a second backbone pass, but local overhead still needs measurement. Retaining extra activations and changing the compiled graph can affect MLX memory and throughput. Paired objectives add real encoder work; the [authors' implementation](https://github.com/galilai-group/llm-jepa) provides options to skip the extra work on selected updates. That is a useful optimization to test after objective correctness, not a speed guarantee for this Mac.

A width-512 two-layer 512→512→512 predictor would add about 525,312 parameters including biases: roughly 1.9% of the small model. A full FP32 EMA copy of that model adds about 109 MB in weights alone, before runtime overhead. These are arithmetic estimates, not measured memory or runtime. Backbone passes and activations may matter much more than predictor parameter count.

Keep FP32, tokenizer, sequence budget, ordinary loss weighting, and sampling fixed in the first comparison. Both gradient magnitude and auxiliary sampling frequency change the effective strength of a new loss. Record them rather than assuming a numerical loss coefficient transfers unchanged from a billion-parameter model.

Monitor collapse across many distinct examples: per-dimension variance, effective rank, pairwise similarity, and ability to distinguish relevant alternatives. Rank computed from two pooled batch examples is almost uninformative. Collect a fixed larger diagnostic set; gradient accumulation alone does not recreate a large simultaneous batch for covariance-based regularization. Even healthy global rank can coexist with loss of numbers or negation, so add exact-content diagnostics. Neither low embedding error nor continued token learning guarantees a useful auxiliary representation.

**A staged experiment that would answer the actual question**

First prepare a separate branch and an explicit finite protocol. Pin one retired small-model checkpoint, its provenance, one corrected data version, matched optimizer states, and a new development/confirmation split. Existing repeatedly inspected suites can remain historical diagnostics; they should not be relabeled fresh confirmation. Preserve the reserved external tests. This preparation is still separate from a training start.

The first screen should compare ordinary next-token training with two modest predeclared STP strengths. Use the same example order, parent state, LR schedule, and at least two paired data orders. Choose coefficients after a bounded numerical/gradient check, not a large accuracy search. Budget calibration, checkpoint/recovery checks, training, and evaluation together; there is no reliable wall-time estimate for the new objective yet.

Measure both common ordinary training-token checkpoints and an equal-wall-time endpoint. Report auxiliary target tokens/passes separately so extra data processing is visible. Fix generation settings and select by free-answer quality across capabilities. Include exact numeric answers, label correctness, repetition, termination, truncation, and functional checks where already supported. Do not pool incompatible metrics into an unexplained single score. A six-hour pilot could be a reasonable proposed envelope after calibration, but it is neither allocated nor started here.

If an auxiliary arm helps, a second experiment should distinguish useful structure from generic regularization: compare the chosen objective with a simple regularizer, and for paired prediction add a carefully matched shuffled-pair control. Such controls are diagnostics, not additional defaults for an uncontrolled parameter sweep. If only representation metrics improve, the result does not meet the project's goal.

For larger confirmation, add independent initialization seeds and either fresh training from random weights or a shared, explicitly counted token-training warm-up. Different data orders from the same parent establish continuation robustness only. To test the project's central generalization claim, eventually reserve whole sources or families before any training in that experiment. A current checkpoint that already trained on those sources cannot establish source-held-out transfer. Keep the final external tests unopened until the selection protocol is complete.

Continue only if the benefit repeats on untouched confirmation data, remains worthwhile at equal compute/time, and is not explained solely by formatting or one family. Report uncertainty at the task-group level and initialization variation separately. Small source samples and a handful of additional correct answers are not enough to establish a general winner.

The practical priority is therefore: inexpensive hidden-state regularization, then meaningful paired solution prediction, then step-conditioned transitions if the earlier probes justify the cost. The long-term research opportunity is to test whether benchmark solutions teach a transferable model of problem-solving operations. JEPA provides a plausible tool for that question; the experiments still have to supply the evidence.
