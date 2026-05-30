# Running upgrade experiments (Anthropic-native)

This covers the phase-3 mechanics: eval formats, running old vs. new with the
Messages and Message Batches APIs, scoring, iterating on the prompt with `/goal`,
bootstrapping evals when there are none, and the Managed Agent optimization loop.

The throughline: **never tune by vibes — change one thing, re-run the evals,
keep what measurably helps, and watch cost/latency alongside quality.**

## Eval format

Keep eval cases as a simple JSON list so the bundled script and any custom scoring
can consume them. Each case:

```json
{
  "id": "close-001",
  "input": "user/task input, or a messages array for multi-turn",
  "expected": "gold answer, or a rubric/keywords for grading",
  "grader": "exact | contains | json_match | tool_call | rubric",
  "metadata": {"slice": "long-context", "severity": "high"}
}
```

If the user already has evals in another shape (Console eval exports, promptfoo,
pytest cases, CSV), don't force a rewrite — read theirs and adapt, or write a thin
converter into the shape above. The point is a consistent record of input →
expected → score, runnable against any model ID.

### Graders

- **exact / contains** — cheap, good for classification or required substrings.
- **json_match** — parse structured/tool output and compare fields; robust to
  formatting noise. Prefer this over regex on free text.
- **tool_call** — assert the right tool was called with the right args (the key
  grader for agents).
- **rubric (LLM-as-judge)** — for open-ended outputs, grade with a model against a
  written rubric. **Default the judge to Opus (`claude-opus-4-8`)** — it's the
  strongest grader and you want the most reliable verdicts deciding the upgrade.
  Keep the rubric in the eval case and hold the judge model fixed across old/new
  runs so comparisons are apples-to-apples. Use the customer's own metric/rubric
  definitions if they have them; otherwise propose defaults and confirm. Spot-check
  judge agreement on a few cases so you trust it.

## Running old vs. new

Use `scripts/run_eval_comparison.py` (Anthropic SDK). It:
- Takes an eval file and two model IDs (`--old`, `--new`) plus a system prompt /
  config, runs every case against both, scores with the per-case grader, and writes
  a structured diff: per-case pass/fail for each model, aggregate pass rate, and
  tokens / cost / latency per model.
- Uses the **Message Batches API** for the bulk runs when the set is large —
  non-interactive eval traffic gets the batch discount (~50%) and avoids rate-limit
  thrash. Small sets run inline for speed.

Always baseline first with the **unchanged** prompt on both models — that's the
honest "flip the ID" result and the denominator for every later improvement.

## Iterating on the prompt with `/goal`

For prompt-level regressions, optimize the system prompt *against the eval score*,
not against taste:

1. Identify the failing slice and the regression hypothesis (from phase 2).
2. Use Claude's `/goal` workflow to propose system-prompt revisions targeted at that
   slice. Frame the goal as the measurable objective ("raise tool_call pass rate on
   the close-* cases without lowering others"), feed it the failing cases, and let it
   propose edits.
3. Re-run `run_eval_comparison.py` on the candidate. Keep it only if the target slice
   improves **and** the overall score doesn't regress (guard against overfitting).
4. Repeat per regression. Stop when new-model ≥ old-model on the metrics that matter.

Apply the same loop logic to harness changes (tool descriptions, thinking budget,
max tokens, orchestration): one change → re-measure → keep/revert.

## Bootstrapping evals (when there are none)

Don't run a blind upgrade. To stand up a starter set fast:
1. Gather 15–30 representative inputs — from logs, the prompt's examples, or the
   user's description of real traffic. Cover the hot paths and a couple of known
   hard cases.
2. For each, capture the **current** model's output and have the user confirm/correct
   it to create a gold answer (or write a rubric where outputs are open-ended).
3. Save in the eval format above. This is now both the regression guard and the
   tuning target. Be explicit that it's a starter set — coverage can grow, but even
   small-but-real beats none.

## Managed Agent optimization loop

If the user gives a **Managed Agent ID** and **auth**, you can close the loop
automatically — pull config, apply candidate changes, re-eval — because the full
harness is addressable via API. This is the highest-leverage path and the most
sensitive one.

Flow:
1. **Read** the agent's current config via the Agent/Managed Agents API (system
   prompt, tools, model, thinking/token settings). Confirm you've got the live
   config.
2. **Fork to a non-production target.** Apply candidate changes to a draft/version or
   test agent — never edit the live production agent in place during iteration.
3. **Loop:** apply change → run the eval set against the draft on the new model →
   score → keep/revert → repeat until the metrics clear the bar.
4. **Hand back, don't auto-ship.** Present the winning config and eval evidence and
   let the human promote it.

Guardrails (state these to the user):
- **Never write to a production agent without explicit, specific confirmation** of
  that exact action. Generic "go ahead" from earlier in the session does not cover
  a production write.
- Show the config diff before applying anything.
- Keep the old config recorded so rollback is one step.
- Respect spend — large loops cost money; agree on a budget/iteration cap up front.

See the `claude-api` skill for SDK specifics (auth, Message Batches, tool use,
thinking config) if you need exact call shapes.
