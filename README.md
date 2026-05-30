# Claude Model Upgrade Skill

A [Claude Skill](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview)
that guides you through upgrading a Claude-backed app or agent from one model to
another (e.g. `claude-sonnet-4-5 → claude-opus-4-8`), or migrating off a model that's
being retired.

It activates automatically when you ask Claude to upgrade or migrate a model. It
works with the Messages API, custom agent harnesses, and Managed Agents.

## Install

Copy the folder into a skills directory:

```bash
# Project-scoped (this repo/project only)
cp -R model-upgrade .claude/skills/

# User-scoped (available everywhere)
cp -R model-upgrade ~/.claude/skills/
```

See the [Agent Skills docs](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview)
for how skill discovery works.

## How to use it

Start a conversation with Claude and describe the upgrade you want, for example:

> *"We're on Sonnet 4.5 and want to move our support agent to the latest Opus —
> what'll break?"*

The skill takes over and runs through four phases. It tells you which phase it's in
and asks for confirmation before anything that costs money or touches production.

### Phase 1 — Identify your setup

Have these ready:

- **Current and target model.** Free-form names are fine; the skill resolves IDs.
- **Prompt surface.** System prompt, instructions, few-shot examples, output format.
  Provide a git path, a Managed Agent ID, or pasted text.
- **Harness config** (for agents). Tool/function schemas, memory strategy, thinking
  config, max tokens, stop conditions.
- **Evals.** A git repo or directory of test cases. Without evals you're upgrading
  blind — if you don't have any, the skill will offer to bootstrap a starter set of
  15–30 representative cases.

You'll also be asked whether you have your own metric definitions. If you do, the
skill uses them verbatim. If you don't, it proposes a default set (accuracy on a
gold set, tool-call correctness, latency, cost per task, refusal rate) and confirms
with you.

Subjective outputs are graded with LLM-as-judge using Opus (`claude-opus-4-8`), held
fixed across old and new runs.

### Phase 2 — Summarize what changed

The skill pulls live Claude release notes and model docs and gives you:

- Capability deltas, behavioral shifts (verbosity, thinking defaults, tool-use
  style), interface/pricing changes, and any deprecation deadline.
- The 3–5 changes most likely to affect your specific setup, ranked by likelihood ×
  severity.

### Phase 3 — Run the eval loop

1. **Baseline both models** with your unchanged prompt and harness. The bundled
   [`scripts/run_eval_comparison.py`](scripts/run_eval_comparison.py) runs every case
   against both models and emits a before/after diff (per-case pass/fail, aggregate
   pass rate, tokens, cost, latency).
2. **Read the diff** to see where the new model regressed or improved.
3. **Iterate to close regressions.** Prompt-level fixes use Claude's prompt-improver
   workflow to optimize against your eval score. Harness fixes adjust tool
   descriptions, thinking budget, max tokens, or the orchestration loop — one change
   at a time, re-measured each time.
4. **Managed Agents.** If you provide a Managed Agent ID and auth, the skill can
   pull the agent's config, apply candidate changes to a non-production draft, and
   loop via API until it's optimized. It never writes to a production agent without
   explicit confirmation.

Reference: [Prompt improver](https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/prompt-improver),
[Claude Code slash commands](https://docs.claude.com/en/docs/claude-code/slash-commands).

### Phase 4 — Migration report

The skill produces a summary you can circulate, using
[`assets/migration_report_template.md`](assets/migration_report_template.md):

- Recommendation (go / go-with-changes / hold).
- Models from → to, with IDs.
- What changed in the model.
- Every change made, with the regression each one fixed.
- Before/after eval results — old vs. new baseline vs. new tuned.
- Cost and latency delta.
- Open risks, follow-ups, and suggested rollout (canary %, monitoring, rollback).

## Running the eval comparison directly

The eval runner is usable standalone:

```bash
pip install anthropic
export ANTHROPIC_API_KEY=sk-ant-...

python scripts/run_eval_comparison.py evals/fixtures/support-agent/evals.json \
  --old claude-sonnet-4-5 \
  --new claude-opus-4-8 \
  --system evals/fixtures/support-agent/system_prompt.txt \
  --out diff.json
```

Eval cases are a JSON list of `{input, expected, grader, metadata}`. Grader types:
`exact`, `contains`, `json_match`, `tool_call`, `rubric` (Opus judge by default).
Full format in [`references/running-experiments.md`](references/running-experiments.md).

## Repo contents

```
SKILL.md                          # the 4-phase flow
references/
  finding-changes.md              # live docs/release-notes sources
  impact-areas.md                 # model-ID table + regression/cost catalog
  running-experiments.md          # eval formats, graders, optimization loop
scripts/
  run_eval_comparison.py          # old-vs-new eval runner + diff
assets/
  migration_report_template.md    # phase-4 report structure
evals/
  evals.json                      # example test prompts for the skill itself
  fixtures/support-agent/         # example agent setup
```

## Notes

- Model IDs, pricing, and behavior change over time. The skill prefers live docs
  over baked-in knowledge; the ID table in `references/impact-areas.md` is a
  convenience, not the source of truth.
- The eval script's price table is an estimate — verify against the
  [pricing page](https://docs.claude.com/en/docs/about-claude/pricing).
- This is an MVP, designed to be hackable. Adapt the graders, eval format, and
  report to your own stack.
