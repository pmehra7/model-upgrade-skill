# Impact areas: where model upgrades bite

Two parts: the current model-ID table (confirm against the live models page, IDs
change), and a catalog of the regression/cost patterns that model changes commonly
cause — with what to check and how to fix each. Use the catalog in phase 2 to form
hypotheses and in phase 3 to know what to look for in the eval diff.

## Current model IDs (verify against the live docs)

| Model | ID |
| --- | --- |
| Claude Opus 4.8 | `claude-opus-4-8` |
| Claude Sonnet 4.6 | `claude-sonnet-4-6` |
| Claude Haiku 4.5 | `claude-haiku-4-5-20251001` |

These are the latest as of this skill's writing. New models ship often — always
reconcile with `https://docs.claude.com/en/docs/about-claude/models/overview` during
phase 2, and use the exact ID the user is actually deploying (aliases vs. dated
snapshots matter for reproducibility — pin a dated snapshot for eval runs).

## The regression & cost catalog

For each pattern: what it is, how it shows up, and the first thing to try.

### 1. Verbosity / format drift
The new model may be more or less verbose, or format outputs slightly differently
(markdown where you wanted plain text, extra preamble, different JSON whitespace).
- **Shows up as:** strict format/regex assertions failing; downstream parsers
  breaking; longer outputs raising cost/latency.
- **First fix:** tighten the output-format instruction and add/refresh a few-shot
  example in the new model's voice. If you parse structured output, prefer tool-use
  / JSON mode over free-text parsing so format is enforced, not requested.

### 2. Over-thinking / excessive extended thinking
Newer models may think more by default or when thinking is enabled, improving
quality but inflating tokens, latency, and cost.
- **Shows up as:** big token/cost jump with marginal accuracy gain; latency SLO
  misses; "+X% accuracy, +Y% cost" tradeoffs.
- **First fix:** set or lower the thinking budget; reserve extended thinking for the
  hard subset of tasks rather than all of them; check whether the default changed
  between models.

### 3. Tool misuse
Agent harnesses are the highest-risk surface. The new model may call tools more/less
eagerly, pick the wrong tool, hallucinate arguments, or change how it sequences
multi-tool plans.
- **Shows up as:** wrong tool selected, malformed args, redundant calls, skipped
  required calls, loops.
- **First fix:** sharpen tool **descriptions** and parameter docs (the model leans
  heavily on these), add usage guidance/examples in the system prompt, and tighten
  schemas (enums, required fields). Re-check any "when to use this tool" heuristics
  written for the old model.

### 4. Instruction-following & prompt sensitivity
A prompt over-tuned to the old model's quirks can underperform on the new one;
conversely, workarounds for old-model weaknesses may now be unnecessary noise.
- **Shows up as:** broad, diffuse regression not tied to one tool or format.
- **First fix:** strip old-model workarounds, then re-optimize the system prompt
  against the evals with `/goal` (see running-experiments.md). Don't hand-tune to a
  few cases — measure across the set.

### 5. Refusal / safety calibration changes
Safety behavior is re-tuned across versions. The new model may refuse things the old
one allowed, or vice-versa — especially relevant for regulated workloads.
- **Shows up as:** new refusals or hedging on legitimate tasks; changed tone on
  sensitive content.
- **First fix:** add context/justification to the system prompt clarifying the
  legitimate use; for regulated customers, flag this explicitly as a compliance
  review item, not just an eval number.

### 6. Cost & latency
Even with equal quality, price-per-token, context window, thinking, and verbosity
shifts move unit economics.
- **Shows up as:** cost-per-task and p50/p95 latency deltas.
- **First fix:** quantify it (the eval script reports tokens/cost/latency); consider
  prompt caching, Message Batches (50% discount for non-interactive eval/offline
  workloads), or routing easy traffic to a cheaper model in the same family.

### 7. Long-context & memory behavior
Context-window size and how the model attends to long inputs / memory can change.
- **Shows up as:** regressions only on long-input or many-turn cases; changed recall
  of earlier context.
- **First fix:** re-test specifically the long-context slice of the eval set; revisit
  retrieval/memory truncation strategy and where key instructions sit in the prompt.

## Severity weighting

Rank flagged areas by **likelihood × severity for this user**, not abstractly. For
Bank_XYZ-type customers, a refusal or compliance miss outranks a small accuracy dip.
For ISV_123-type customers running many agents, a pattern that recurs across the
fleet (e.g. tool-description staleness) is worth more than a one-agent quirk because
the fix amortizes.
