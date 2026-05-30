# Finding what changed between models

The goal of this reference is to let you answer "what's actually different about the
target model, and which docs say so" from **live** sources, not from training
memory. Model behavior, IDs, pricing, and deprecation dates all drift — always
prefer the live page.

## Primary sources (check these first)

Anthropic docs now live on `docs.claude.com` (older `docs.anthropic.com` links
redirect). The pages that matter for an upgrade:

| What you want | Page |
| --- | --- |
| Dated list of API/model changes | `https://docs.claude.com/en/release-notes/overview` |
| Current model line-up, IDs, context windows, pricing tiers | `https://docs.claude.com/en/docs/about-claude/models/overview` |
| Retirement / sunset dates and replacements | `https://docs.claude.com/en/docs/about-claude/model-deprecations` |
| "What's new" / migration guidance for the latest major version | search the docs for "migrating to Claude" |
| Pricing | `https://docs.claude.com/en/docs/about-claude/pricing` (or anthropic.com/pricing) |

The official Anthropic news/blog (`anthropic.com/news`) carries the announcement
posts, which often describe behavioral changes (thinking, tool use, agentic
improvements) in more practical terms than the docs.

## How to search effectively

1. Start with `WebFetch` on the release-notes and models-overview URLs above with a
   prompt like: "What changed for `<target model>` versus `<current model>` —
   capabilities, behavior, pricing, context window, default thinking behavior?"
2. If a URL 404s or the docs have been reorganized, fall back to `WebSearch` with
   `allowed_domains: ["docs.claude.com", "anthropic.com"]` and queries like
   `claude <target model name> release notes` or `claude <current model> deprecation
   date`.
3. For behavioral nuance not in the docs, a broader `WebSearch` (engineering blogs,
   the Anthropic cookbook, well-known practitioners) can surface real-world upgrade
   gotchas — but mark these as community signal, not official, and verify against
   evals rather than trusting them.

## What to extract

For the phase-2 summary, pull out specifically:

- **Capability deltas** — what the new model is better/worse at (reasoning, coding,
  long-context, vision, agentic/tool-use).
- **Behavioral shifts** — verbosity, default extended-thinking behavior, how
  eagerly it calls tools, refusal/safety calibration, output formatting tendencies.
  These are the silent regression sources.
- **Interface changes** — new or changed parameters, new tool types, new beta
  headers, changed defaults (e.g. a new default max thinking budget), deprecated
  params.
- **Pricing & context** — input/output price per token, context window size,
  prompt-caching and batch discounts. Needed for the cost delta in phase 4.
- **Deprecation timeline** — if the current model is sunsetting, the hard date.
  This converts "nice to have" into "must do by X" and should be loud in the report.

Tie each extracted change to a hypothesis about their setup (phase 2, step 3). A
change nobody's setup touches isn't worth the user's attention; one that hits their
hottest path is the headline.
