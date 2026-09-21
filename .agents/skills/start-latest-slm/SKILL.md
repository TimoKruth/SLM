---
name: start-latest-slm
description: Start local chat inference with the latest trained SLM checkpoint in this project. Use for "start the latest model", "chat with our SLM", or "open the trained model". Does not start or resume training, run benchmarks, or start the Qwen comparison.
---

# Start the latest trained SLM

Use the existing `slm.chat` interface. Work from this repository's root (three
directories above this skill folder). Read [CHAT.md](../../../CHAT.md) for chat
options and [AGENTS.md](../../../AGENTS.md) for the current campaign and archive
policy. Creating or documenting this skill alone is not an instruction to launch
inference.

## Choose the checkpoint

- An explicitly requested model/campaign takes precedence. Otherwise use the
  latest completed, non-deprecated SLM training campaign supported by local
  status and completion records. The model path built into `slm.chat` is only a
  default for one campaign; do not assume it remains the newest campaign.
- Check the current campaign named in project instructions and look for newer
  candidates using the shallow patterns `runs/*/model/latest.json` and
  `runs/*/latest.json`. Read candidate `status.json` and completion records to
  establish training chronology. Checkpoint numbers compare updates within one
  run, not recency across runs. Directory names and filesystem modification times
  alone do not prove which training finished last.
- Select the run's `latest.json` checkpoint, never its development-selected
  `best.safetensors`. Exclude archived legacy runs, Qwen reference outputs,
  `.tmp`/`.old` checkpoints and token snapshots. Do not restore archives for this
  workflow. If status evidence leaves multiple plausible latest models, ask which
  to use rather than silently choosing a different model.
- Resolve the selected model with `slm.chat.resolve_model(model_directory)` in
  the project Python environment. This reads metadata without importing MLX or
  loading weights, and returns the exact checkpoint path. Pin its directory name
  with `--checkpoint` for launch so a changing latest pointer cannot switch it.
  Missing files or inconsistent metadata should produce a clear error, not a
  fallback to another checkpoint.

## Launch chat for the user

Build this command with the resolved paths and checkpoint name:

```sh
.venv/bin/python -m slm.chat --model MODEL_DIRECTORY --checkpoint CHECKPOINT_NAME
```

For an interactive chat request, open it in a user-accessible macOS Terminal
window, with the working directory set to the repository root. Use `osascript`
to tell Terminal to `do script` the command, then `activate`. Shell-quote the
repository path and every argument (e.g. Python `shlex.join`), and separately
escape backslashes and quotes in the AppleScript string. Pass AppleScript to
`osascript` as an argument, not as interpolated shell code. Do not leave chat in
an agent-only PTY that the user cannot type into. If Terminal automation is
unavailable, give the exact command and explain that the chat window was not
opened.

CPU is the default. Honor an explicit GPU request with `--device gpu`; the chat
program acquires the project's shared exclusive GPU lease. If occupied, report
the conflict without killing another job or bypassing the lease. Keep PowerWatch
running. This is interactive inference, not a training/evaluation launch through
`run_slm.py`.

If the user supplies a question to answer here, use `--prompt QUESTION --json`
instead of opening a terminal; pass the question as a single argument. For
multiline text, `--prompt - --json` accepts stdin. Do not invent a test question
or run a benchmark suite as part of opening chat.

Check the Terminal startup output (or one-shot exit/result) for the loaded
checkpoint before claiming success. Report the chosen campaign, checkpoint and
device. Mention `/reset` to clear history and `/quit` to exit. If startup failed,
report the actual error. No model registration in Ollama is performed.

Chat displays output tokens, elapsed seconds and tokens/s after each answer;
one-shot JSON includes `tokens_per_second`. This measures the current device's
response generation including prompt processing, excluding model loading and
user typing. Use this live value for chat speed, not training throughput or the
historical overall evaluation estimate.

The existing checkpoint is read-only; chat history stays in memory. Do not
restart training, remove STOP files, adopt a model as a benchmark winner, or
publish weights/responses. Conversational quality is experimental because this
model was trained on benchmark question/answer records.
