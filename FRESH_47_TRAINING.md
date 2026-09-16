# Fresh training on 47 sources — prepared, not started

The 16 September 2026 request is to archive the previous experiments and prepare a completely new training. The user-selected preparation is **97,536,768 parameters with a 24-hour future campaign cap**. No model has been initialized, no GPU training/evaluation has run, and no starter or queue is installed. The campaign has a STOP file and no start authorization.

## Model and training recipe

- Random initialization, seed `20260916`; new AdamW state; no parent checkpoint or resume argument.
- Decoder: 12 layers, width 768, 12 heads, gated feed-forward width 2,048, tied embeddings, context 1,024; FP32, compiled execution, batch size 2.
- New byte-level BPE tokenizer with 16,384 tokens, fitted only to training-partition text. No pretrained tokenizer or weights.
- AdamW: peak learning rate `3e-4`, betas `(0.9, 0.95)`, weight decay `0.1`, 100-update warmup. Token-clock cosine decay to `3e-5` over 200M tokens, then the floor. This is a fixed fresh-training recipe, not a claimed winner from deprecated studies.
- Equal sequence sampling mass per capability family, then per source within each family. Token exposure will differ with sequence length and is reported separately. The next-token loss covers the complete formatted sequence; answer loss is evaluated separately.
- Checkpoints every five minutes retain model, Adam and sampler state. Evaluation-only snapshots at 10M, 25M, 50M, 100M and 200M tokens are saved if reached. Thresholds are observations, not promises of exposure or triggers for extension.
- Initial random-model development loss and periodic development loss every 30 minutes provide within-run learning diagnostics. Fixed generation suites are evaluated at the final endpoint.

## Data and isolation

Data version: `data/v7-benchmarks47-fresh-2026-09-16/`. All 47 sources contribute **2,343,583 training records** across 13 families, comprising 306,994,597 stored tokens before batch packing. This is pool size, not tokens already trained. The source catalog is in [BENCHMARKS_47.md](BENCHMARKS_47.md).

The new version derives from the already prepared v6 pool, preserving original training membership. Six known problematic reference groups are excluded. Original-32-source development groups are deterministically divided into development/confirmation; the 15 expansion sources retain their pre-existing grouped holdouts. All records originate from original training splits. Original validation and external test files are not consumed by this preparation.

The tokenizer saw 2,344,017 training-pool records. Re-encoding with the new tokenizer excluded 434 training records exceeding 1,024 tokens, leaving 2,343,583; targets were never truncated. Training token/mask/index files are regular, self-contained files with no legacy-run or worktree symlink dependencies. The 282 derived files are hashed; 1,474 token/mask samples and CPU batches from every nonempty source/split were checked.

Full partitions contain 87,272 development and 85,129 confirmation records. Groups and exact prompt-answer contents are disjoint across training/dev/confirmation. This does not guarantee semantic independence. The admitted pool still reflects v6's earlier context filtering; this preparation did not reconstruct discarded raw records. Some original-source holdout groups were previously used in historical experiments. Confirmation is held out from this fresh model, not guaranteed universally unseen research data.

## Endpoints and interpretation

Primary endpoint: the **final chronological checkpoint** on the fixed 1,267-task confirmation suite. Secondary endpoint: that same checkpoint on the separate 1,269-task development suite. Each suite selects at most 32 independent groups per source. Confirmation is not used for training, periodic development loss, checkpoint selection or tuning. The best-dev checkpoint may be saved by the trainer but is not the primary endpoint.

Both suites cover 46 sources. HotpotQA contributes training but has no safe direct holdout in the inherited grouping. Several small sources fall below 32 tasks; exact denominators are in the coverage table. Each suite contains 1,064 correctness-scored references; remaining tasks contribute reference loss and their declared proxy metrics.

Report per-source scores and counts, per-family means across scored sources, and teacher-forced answer loss. Show coverage gaps and unscored abilities explicitly. Code syntax is not functional correctness; SQL text matching is not execution correctness; summary lexical overlap is not factuality. These are internal proxies, not official benchmark scores or proof of transfer. No legacy scores or tokenizer losses are used as a baseline. There is no automatic model adoption.

Successful technical completion requires both suites' generation and reference-loss evaluations to finish, zero context-overflow responses, finite training/loss outputs, unchanged frozen inputs, and completion within the cap. Any failure is recorded as incomplete/paused; it does not authorize another attempt. Quality findings are reported descriptively, with no post-hoc threshold for declaring a winner.

## Budget and controls

| Phase | Maximum |
| --- | ---: |
| Runtime input/resource checks | 15 minutes |
| Training, inline development and checkpoint saving | 22 hours 30 minutes |
| Two final evaluations | 1 hour |
| Verification and CPU report | 15 minutes |
| Total | **24 hours** |

The training child gets a deadline 90 seconds before its phase boundary to save its final checkpoint. Each evaluation has at most 1,740 seconds of workload time plus 30 seconds of process-exit reserve. Optional token snapshots are saved but not evaluated automatically. Unused phase time does not extend training. Today's completed CPU dataset/tokenizer preparation is recorded separately; the proposed future 24-hour cap starts only at an explicitly authorized campaign launch.

The supervisor requires mains power and an exclusive GPU lease, records runtime power conditions, and uses light monitoring with PowerWatch. STOP, signals, a child failure, lost mains power or a deadline stop the campaign. Existing status prevents reusing the run directory to reset the budget. A future continuation needs an explicit instruction and a budget-adjusted plan. No retry, automatic extension, scheduling or model adoption is configured.

## Artifacts and inspection

- Local frozen plan and STOP: `runs/fresh47-97m-2026-09-16/`.
- Committed plan and aggregate checks: `plans/fresh47-2026-09-16/`.
- Data audit: `data/v7-benchmarks47-fresh-2026-09-16/READY.json` and `INDEPENDENT_CHECKS.json`.
- CPU preparation: `fresh47/prepare.py`; independent audit: `fresh47/verify.py`; future controller: `fresh47/campaign.py`.

Read the proposed command without starting work:

```sh
.venv/bin/python -m fresh47.campaign --run runs/fresh47-97m-2026-09-16 --dry-run
```

On a later explicit start request, recheck the frozen inputs and resource conditions, record authorization matching the exact `plan.json` SHA256, and remove only this campaign's STOP immediately before launching through `run_slm.py --module fresh47.campaign`. These preparation instructions are not a start authorization. A real GPU smoke/admission check belongs to that future runtime preflight; only CPU preparation and orchestration tests have run so far.
