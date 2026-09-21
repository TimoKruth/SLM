# Chat with the trained SLM locally

## Start through the project skill

Ask **"Start the latest trained SLM for chat"** or invoke **`$start-latest-slm`**.
The project skill lives in
[.agents/skills/start-latest-slm/SKILL.md](.agents/skills/start-latest-slm/SKILL.md).
It checks current campaign records, resolves the latest complete checkpoint,
and opens chat in a Terminal window you can type into. It starts inference only;
it does not resume training. A question supplied with the request can instead
be answered directly using the one-shot interface.

The skill selects the latest completed, non-deprecated training campaign from
local evidence. The plain command below uses the configured default campaign
and its `latest.json` pointer; it does not search across campaigns. Use `--model`
to choose a different campaign manually.

## Start from a terminal

Run from this repository on the Apple Silicon Mac with the existing Python 3.12
environment (`uv sync` if dependencies have not been installed):

```sh
.venv/bin/python -m slm.chat
```

This loads the latest complete checkpoint from
`runs/fresh47-97m-2026-09-16/model` once. Currently that is the final chronological
`checkpoint-0215720` (97.54M parameters). The startup message prints the exact
weights path. It runs on CPU by default. For faster Apple GPU inference:

```sh
.venv/bin/python -m slm.chat --device gpu
```

GPU mode holds the project's exclusive GPU lease and refuses to run if another
cooperating workload owns it. Exit with `/quit` or Ctrl-D to release memory and
the lease. Ctrl-C cancels the current answer and returns to the prompt.

Commands:

- `/reset`: clear conversation history.
- `/multiline`: paste a question, passage, or code; finish with `/end` on a new line.
- `/help`: show commands.
- `/quit` or `/exit`: close chat.

Answers use greedy decoding, with a default limit of 128 output tokens and a
60-second budget checked between decoding steps. Set `--max-tokens 256` or
`--max-seconds 120` as needed. Answers appear when generation finishes. The
interactive interface reports when an answer reaches a token or time limit.

For a single answer or use from another local program:

```sh
.venv/bin/python -m slm.chat --prompt 'What is a rainbow?'
.venv/bin/python -m slm.chat --prompt 'What is a rainbow?' --json
printf 'Explain this sentence:\nThe cat is sleeping.\n' | .venv/bin/python -m slm.chat --prompt - --json
```

JSON includes `text`, token counts, `stop_reason`, elapsed seconds,
`dropped_turns`, and the checkpoint path. Diagnostics go to stderr; stdout is
the answer or JSON. Invalid inputs and missing artifacts return a nonzero exit.

To select another trained checkpoint of this project's architecture, supply its
model directory (containing `config.json`, `tokenizer.json`, and checkpoint
directories), or its parent campaign directory:

```sh
.venv/bin/python -m slm.chat \
  --model runs/fresh47-97m-2026-09-16/model \
  --checkpoint checkpoint-0215720
```

There is no fallback to `best.safetensors`. This is inference only: it does not
train, resume a campaign, run benchmark suites, modify weights, write chat logs,
or contact a service. Conversation state lives in memory until reset or exit.
PowerWatch continues independently; this interactive tool is separate from the
monitored training/evaluation launcher.

The model was trained on benchmark question/answer records, not assistant
conversations. Free-form chat and conversational memory may be poor. Each new
question uses its original `<bos><question>…<answer>` format; earlier turns are
included as complete question/answer records. Oldest turns are removed as needed
to reserve answer space within the 1,024-token context. The current question is
never silently truncated. Use `--no-history` for independent questions in the
same session, which is closer to its training and evaluation use. Literal model
control tokens in user messages are rejected.

## Ollama

This interface runs the model directly with MLX; it does not register a model in
Ollama. [Ollama's import workflow](https://docs.ollama.com/import) accepts model
artifacts via a Modelfile. This project's safetensors file uses custom tensor
names, fused QKV weights, a tied output embedding, and a project-specific config
and tokenizer. It is not a ready-to-import Hugging Face/Ollama model directory.
A reliable Ollama export would need architecture/tensor/tokenizer conversion
and numerical parity checks. No such conversion is claimed here; direct loading
retains the existing checkpoint and inference implementation.
