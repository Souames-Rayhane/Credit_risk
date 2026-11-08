# AI-generated dashboard image vs our dashboard

**Tool:** Claude (Claude Opus 5.5), claude.ai · **Date:** 8 November 2026
**Prompt:** `prompt.txt` (one prompt, schema only, first image kept) · **AI image:** `ai_dashboard.png`
**Our dashboard:** Streamlit, 5 pages (`dashboard/`), screenshots in `screenshots/`

## What an AI-generated dashboard image is
An AI is given the business problem and the schema and produces a picture of what the
dashboard could look like. It never connects to the database, so every number in the
picture is invented. Its value is design inspiration (layout, KPI ideas, visual
hierarchy), not analysis.

## Real values to compare against (from our SQL)
| Measure | Our data | Source |
|---|---|---|
| Clients | 1,300 | checks |
| Clients in difficulty | 105 (8.08 %) | checks / `v_dash_global` |
| Instalments | 45,296 | Q1 |
| Late (any delay) | 8.90 % | Q1 |
| Late > 7 days | 2.87 % | Q1 |
| Late > 30 days | 0.36 % (163 instalments) | Q1, Q4 |
| Past lateness > 7 d → difficulty | 11.45 % vs 7.10 % (×1.61) | Q7 |

## Audit of the AI image

| # | Check | What the AI image shows | Verdict | Our dashboard |
|---|---|---|---|---|
| 1 | Numbers vs real data | 15,240 clients; 12.4 % late; 2 % of instalments 60+ days late | **Invented.** Real: 1,300 clients, 8.90 % late, 0.36 % > 30 days. Its > 30-day figure is ~17× too high | Every number read from a SQL view |
| 2 | KPIs the schema cannot support | "Total Credit Exposure $412.6M" (no currency, and no outstanding-balance column); "vs last year" deltas | **Fabricated.** No column gives an outstanding balance; no calendar to compare years | KPIs map to Q1 and `v_dash_global` |
| 3 | Time axis | Monthly trend Jan–Dec 2025, period filter | **Impossible.** Our dates are days relative to each client's application; there is no calendar | No calendar trend; explained in footer |
| 4 | Internal consistency | KPI says 12.4 % late, donut says 18 % late (12+4+2). Donut says 6 % > 30 days, trend line says 10–12 % > 30 days | **Contradicts itself** on the same measure | Q5 buckets add up to totals |
| 5 | Business terms | "Default rate", "Defaulted" | **Wrong term.** target = 1 means payment difficulty, not default | "Clients in difficulty" |
| 6 | Coverage of questions A–D | A: yes (late rate, portfolio). B: partly (income type only, score curve). C: **missing** (no link past lateness → difficulty). D: a "risk" label with no stated rule | Misses the most actionable finding | One page per question; Q7 and Q8 explicit |
| 7 | Reading aids | No overall reference line, no sample sizes | Can't tell above/below average or trust small groups | Overall-rate line, n on hover, reliability flags |
| 8 | Chart choices | Donut, overlapping density curves, 12 bars in one grouped chart | Polished, but the donut hides the small buckets that matter | Sorted bars, one risk colour |
| 9 | Interactivity | Filter buttons drawn, but it is a static picture | None | Source filter, profile selector, hover, zoom |
| 10 | Traceability | No query behind any figure | Not verifiable | Each chart cites its query |

## What the AI did well
- Professional layout: clear KPI row, six panels, consistent colours; it looks like a real BI product.
- It thought of filters (region, portfolio, contract type) at the top: a good idea for interactivity.
- The external-score distribution by status is a strong visual: it shows at a glance that
  low scores concentrate the difficulty cases.
- A client-level "high-risk" list is something a credit officer wants; our dashboard shows
  counts per score group but no list of clients.

## What we take from it / what we had to fix
- **Take:** a global filter bar; a client list behind the alert score (score 2 clients); the score-distribution chart.
- **Fix:** replace every invented number with SQL results; drop the calendar trend and the
  "vs last year" deltas; drop "exposure"; rename "default" to "difficulty"; make the late-rate
  definitions consistent (one definition, from Q1); add the past-lateness finding (Q7) and an
  explicit alert rule (Q8).

## Scores (/5)

| Criterion | AI image | Ours | Why |
|---|---|---|---|
| Analytical relevance | 2 | 4 | AI covers A and part of B; misses C, D has no rule |
| KPI selection | 2 | 4 | AI includes unsupported KPIs (exposure, yearly deltas) |
| Visual clarity | 4 | 3 | AI layout is more polished; ours is plainer but has reference lines |
| Correctness | 1 | 5 | AI numbers invented and self-contradictory; ours come from SQL |
| Decision-support value | 2 | 4 | AI shows risk, not what to do; ours states findings and a follow-up rule |

(Adjust "Ours" after looking at your own screenshots: these are our proposal.)

## Conclusion
The AI produced in seconds a dashboard that looks more polished than ours, and it gave us
three ideas worth adopting. But none of its numbers come from the data, it contradicts
itself on the late-payment rate, it shows a calendar trend our data cannot support, and it
misses the most actionable finding (past lateness → 1.6× more difficulty). It is a design
sketch to audit, not a decision tool.