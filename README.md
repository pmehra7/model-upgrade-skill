# Claude Model Upgrade Skill

An interactive **upgrade coach** for moving a Claude-backed app or agent from one
model to another — e.g. `claude-sonnet-4-5 → claude-opus-4-8`, or migrating off a
model that's being retired — with as little friction and risk as possible.

New Claude models ship fast, but adopting them is rarely a one-line model-ID change.
Prompts tuned for the old model can underperform on the new one; agent harnesses
(tools, memory, thinking budget) behave differently — tool misuse, over-thinking,
cost overruns. Teams end up spending weeks of every model cycle validating and
tuning. This skill collapses that into a guided, **evidence-backed** session.

> This is a [Claude **Skill**](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview).
> Drop it into a skills directory (see [Install](#install)) and it activates
> automatically when you ask Claude to upgrade or migrate a model.

---

## Who it's for

| Persona | What they own | What this gives them |
| --- | --- | --- |
| **AI Engineer** | One or a few agents | Ship the new model's gains *without* regressions; prompt + harness tuning measured against evals |
| **AI Platform Lead / Admin** | A *fleet* of agents | A consistent, repeatable rollout and a defensible go/no-go decision per agent |

Works across the **Messages API**, **custom agent harnesses**, and **Managed Agents**.

---

## The customer flow

Tell Claude something like *"we're on Sonnet 4.5 and want to move our support agent
to the latest Opus — what'll break?"* and it walks you through four phases. You stay
in control: it tells you what phase it's in and asks before anything that costs money
or touches production.

### 1. Identify your setup → and agree on how we'll measure

The skill asks for what's being upgraded:

- **Current model + target model** (free-form is fine; it resolves exact IDs).
- **The prompt surface** — system prompt, instructions, few-shot examples, output
  format. Share via a git repo path, a Managed Agent ID, or pasted text.
- **The harness** (for agents) — tool/function schemas, memory strategy,
  thinking/extended-thinking config, max tokens, stop conditions.
- **Your evals** — a git repo or directory. This is the most important asset; without
  it you're upgrading blind. *No evals? The skill offers to bootstrap a small starter
  set (15–30 representative cases) before going further.*

**Metrics & judging.** The skill asks **whether you have your own metric
definitions**:

- **If you do** — it uses *your* definitions and rubrics verbatim.
- **If you don't** — it proposes a sensible default set (accuracy on a gold set,
  tool-call correctness, latency, cost per task, refusal rate) and confirms with you.

For any subjective or open-ended outputs, grading is done with **LLM-as-judge using
Opus (`claude-opus-4-8`)** — the strongest grader — held fixed across the old and new
runs so the comparison is apples-to-apples.

### 2. Summarize what changed

You shouldn't have to parse changelogs, blogs, and socials yourself. The skill pulls
the **live** Claude release notes and model docs, then gives you a scannable summary:

- Capability deltas, behavioral shifts (verbosity, thinking defaults, tool-use style),
  interface/pricing changes, and any **deprecation deadline** if you're on a
  sunsetting model.
- **Mapped onto your setup** — the 3–5 things most likely to bite *you*, ranked by
  likelihood × severity, with the common regression/cost patterns (over-thinking,
  tool misuse, format drift, refusals) called out.

### 3. Run the eval loop

This is where speculation becomes evidence.

1. **Baseline both models** with your *unchanged* prompt/harness — the honest "what
   happens if we just flip the model ID" number. The bundled
   [`scripts/run_eval_comparison.py`](scripts/run_eval_comparison.py) runs every case
   against both models and emits a structured before/after diff (per-case pass/fail,
   aggregate pass rate, tokens, cost, latency).
2. **Read the diff** — where did the new model regress, where did it improve, and why.
3. **Iterate to close regressions.** For prompt-level fixes, the skill uses Claude's
   **`/goal`** workflow to optimize the system prompt *against your eval score* (not
   against taste), then re-measures. For harness fixes it adjusts tool descriptions,
   thinking budget, max tokens, or the orchestration loop — one change at a time,
   re-run, keep what helps.
   - 📖 **Claude `/goal` & prompt optimization docs:**
     [Prompt improver](https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/prompt-improver)
     · [Claude Code slash commands](https://docs.claude.com/en/docs/claude-code/slash-commands)
     (use whichever `/goal`-style workflow your environment exposes).
4. **Managed Agents** — if you provide a Managed Agent ID **and** auth, the skill can
   pull the agent's config, apply candidate changes to a *non-production* draft, and
   loop via API until it's optimized — then hand the winning config back for you to
   promote. It never writes to a production agent without explicit, specific
   confirmation.

### 4. Summarize the changes → migration report

Finally, the skill produces a migration summary you can circulate, using
[`assets/migration_report_template.md`](assets/migration_report_template.md):

- **Recommendation** (go / go-with-changes / hold) up top.
- Models from → to, with IDs.
- What changed in the model (condensed).
- **Every change made**, with the rationale tied to the regression it fixed.
- **Before/after eval results** — old vs. new baseline vs. new tuned. The evidence.
- Cost & latency delta.
- Open risks, follow-ups, and a suggested rollout (canary %, monitoring, rollback).
- *(Fleet)* What's reusable across agents, so the next upgrade is cheaper.

---

## What's in this repo

```
SKILL.md                          # the coach: 4-phase flow + persona routing
references/
  finding-changes.md              # live docs/release-notes sources + search strategy
  impact-areas.md                 # current model-ID table + regression/cost catalog
  running-experiments.md          # eval formats, graders, /goal loop, Managed Agent loop
scripts/
  run_eval_comparison.py          # Anthropic-native old-vs-new eval runner + diff
assets/
  migration_report_template.md    # the phase-4 report structure
evals/
  evals.json                      # example test prompts for the skill itself
  fixtures/support-agent/         # a realistic example agent setup to try it on
```

---

## Install

Copy the folder into a skills directory so Claude can discover it:

```bash
# Project-scoped (this repo/project only)
cp -R model-upgrade .claude/skills/

# or User-scoped (available everywhere)
cp -R model-upgrade ~/.claude/skills/
```

Then just ask, e.g. *"help me upgrade our agents to the latest Opus"* — the skill
activates on its own. See the
[Agent Skills docs](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview)
for how skill discovery works.

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

Eval cases are a simple JSON list (`input` / `expected` / `grader` / `metadata`).
Graders: `exact`, `contains`, `json_match`, `tool_call`, `rubric` (Opus judge by
default). See [`references/running-experiments.md`](references/running-experiments.md)
for the full format.

---

## Notes & disclaimers

- Model IDs, pricing, and behavior change over time — the skill always prefers the
  **live docs** over baked-in knowledge. The ID table in
  `references/impact-areas.md` is a convenience, not the source of truth.
- The eval script's price table is an estimate; verify against the
  [pricing page](https://docs.claude.com/en/docs/about-claude/pricing).
- This is an MVP designed to be **hackable** — adapt the graders, eval format, and
  report to your own stack.

---

*Authored by Paras Mehra. Built as a Claude Skill.*
