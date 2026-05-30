# Model Upgrade Migration Summary

> Fill every section. Lead with the recommendation and the before/after numbers —
> that's what a reviewer reads first. Delete these quote lines when done.

## Recommendation
**<GO / GO-WITH-CHANGES / HOLD>** — one sentence on why.

## Scope
- **From:** `<old-model-id>`  →  **To:** `<new-model-id>`
- **Workload:** <API call | custom agent | Managed Agent ID `<id>`>
- **Owner / persona:** <AI Engineer / Platform Lead>
- **Deprecation deadline (if any):** <date, or N/A>

## What changed in the model
<3–6 bullets from phase 2: capability deltas, behavioral shifts, interface/pricing
changes. Link the release-notes/docs sources used.>

## Before / after eval results
| Metric | Old model | New model (baseline) | New model (tuned) |
| --- | --- | --- | --- |
| Pass rate | | | |
| Cost / task | | | |
| Avg latency | | | |
| <key slice, e.g. tool_call> | | | |

- **Regressions found (baseline):** <case IDs / pattern>
- **Improvements found:** <case IDs / pattern>
- **Net after tuning:** <one line>

## Changes made
| # | Change | Surface | Fixes | Evidence |
| --- | --- | --- | --- | --- |
| 1 | <e.g. tightened `search_db` tool description> | harness | tool misuse on close-* | pass 72%→94% |
| 2 | <e.g. lowered thinking budget to 4k> | config | cost overrun | $/task −38%, pass flat |

<Include diffs for non-trivial prompt/harness edits.>

## Cost & latency delta
<Per-task cost and p50/p95 latency, old vs. new (tuned). Note any caching/batch/
routing levers applied or recommended.>

## Open risks & follow-ups
- <Unresolved regression or tradeoff the user must decide on>
- <Compliance/safety item to review (esp. regulated workloads)>
- **Rollout plan:** <canary %, monitoring metric + threshold, rollback trigger>

## Reusable across the fleet
<For Platform Leads: prompt patterns / harness settings / eval cases that transfer to
the next agent or the next upgrade, so this gets cheaper over time.>
