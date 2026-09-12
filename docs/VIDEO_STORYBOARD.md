# Video storyboard — Delivery Operations Intelligence

The 48.6-second case-study film and the 10-second hero loop, scene by scene.
Source project: [`portfolio-video/pedidosya/`](../portfolio-video/pedidosya/).

Every figure named in the **Data used** column is read from a published
aggregate CSV, frozen into `src/data/*.json` by `scripts/extract-data.py`, and
re-checked against the source by `scripts/verify-claims.mjs` — 82 assertions
that fail the build if a number drifts or is edited by hand.

## Main case study — 1920×1080, 30 fps, 48.6 s

| Time | Scene | Visual | Text | Data used | Animation | Purpose |
|---|---|---|---|---|---|---|
| 0.0–3.8 s | 01 Open | Schematic dispatch network draws itself across the right two-thirds; accent radial breathes at lower left | **DELIVERY OPERATIONS / INTELLIGENCE** · "Independent operations case study" · "334,144 orders · 32 days · 4 raw sources" · "From raw operational data to decisions that survive scrutiny." | `kpis.csv` (orders, dates) | 20 arcs draw by normalised `pathLength`; nodes scale-pop on a 0.022 s stagger; order pulses ride `offset-path`; title lines rise out of overflow masks | Establish scale and register in under four seconds. Signals *operations analytics*, not a dashboard demo |
| 3.8–9.0 s | 02 The operation | Six-card command grid on the raised surface, each with an accent tick rail | Orders · mean service · late >5 min · observed rider-hours · matched throughput · recorded cost per order | `kpis.csv`, `manifest.json` row counts, `executive_findings.json#F04` | Cards arrive on a 0.07 s stagger; six tabular-figure count-ups land on the exact published values; tick rails wipe down | Prove the operation is genuinely large and that the analyst knows which denominator each KPI uses |
| 9.0–14.6 s | 03 The rhythm | Real 24-hour demand histogram with the mean-service line overlaid; hours 03–06 shaded "insufficient support"; playhead scrubs to 21:00 | **DEMAND IS NOT EVENLY DISTRIBUTED** · "Peak load lands at 20:00 — 45,112 orders. Service is worst one hour later: 21:00 — 28.85 min mean, highest of the 20 well-supported hours." | `operational_segments.csv` family = `hour`, all 24 rows | Bars grow on a 0.018 s stagger; the service line draws in two segments so the unsupported band stays a visible gap; a playhead sweeps and the readout writes only on index change | Show real temporal structure — and that low-support hours are marked, not quietly smoothed away |
| 14.6–21.6 s | 04 The hypothesis | Left: the hypothesis, then the rejection stamp. Right: a confidence interval drawn on a number line straddling a dashed zero, plus four non-monotonic discovery quartiles | **TEST THE OBVIOUS EXPLANATION FIRST** · "More orders per observed rider-hour should mean more late orders." · **NO VALIDATED / OPERATIONAL THRESHOLD** · "Re-tested on 10 held-out dates. The hypothesis was dropped, not decorated." | `headline_contrasts.csv`, `threshold_assessment.csv`, `threshold_discovery_bins.csv`, `temporal_holdout.csv` | Point estimate pops, then the interval grows **outward from it** so crossing zero is the motion itself; quartile bars stagger; the stamp is the film's single hit — 0.3 s `expo.out` plus a three-frame shake | The credibility beat. A recruiter sees an analyst who tested the intuitive answer and threw it away rather than selling it |
| 21.6–29.0 s | 05 The diagnosis | Five process stations with their real stage means, chevrons between; two stacked proportion bars beneath — share of service time, then share of the late gap | **SO WHERE DOES THE TIME ACTUALLY GO?** · **51.0% of the late-order gap accrues before a rider is even notified.** | `stage_summary.csv` + `stage_late_contrasts.csv` | Stations stagger in; each bar's segments fill left-to-right by `scaleX` from their own left edge; stage one dips and returns in both bars to bind them | The payoff. 41.1% of time but 51.0% of the *gap* — the finding that redirects where management should look |
| 29.0–34.8 s | 06 The concentration | Left: two proportion tracks (3.1% of orders → 36.6% of pre events). Right: the restaurant distance ladder climbing to an accent bar | **THE DAMAGE IS CONCENTRATED** · cohort service, CI and late rate · "17.3% at 1 km or less versus 47.9% above 3 km: +30.59 pp" | `headline_contrasts.csv`, `operational_segments.csv` (`vertical_distance`), `executive_findings.json#F02` | The two tracks fill at different speeds so the 12× jump is felt before it is read; ladder bars stagger bottom-anchored | Show the analyst can find the small population that carries the damage — the difference between a report and a target list |
| 34.8–40.8 s | 07 The decision | Three ranked priority cards, each carrying trigger, cohort, a late-rate bar, action and trade-off; a guardrail banner underneath | **EVIDENCE BECOMES A TESTABLE DECISION** · Observation → Evidence → Action → Guardrail · "Each row is a pilot design with a monitoring KPI and a stated trade-off — not a projected saving." | `priorities.csv` (three supported rows) | Cards assemble on a 0.22 s stagger, their fields cascade at 0.035 s, late-rate bars fill to the real rate | Business reasoning: the work ends in decisions someone can run on Monday, with costs stated rather than hidden |
| 40.8–44.2 s | 08 The build | Four fast stations DATA → ANALYSIS → TOOL → DECISION, a real four-line fragment of `analysis.py`, and stack chips | **HOW IT WAS BUILT** · "The gate that decides whether a comparison earns a confidence interval at all." · "21-phase brief · AI-assisted build · 26 canonical validation checks" | `delivery_ops/analysis.py`, `manifest.json` seed and bootstrap settings | Stations and chevrons stagger fast; code lines slide in one at a time; chips pop on a 0.035 s stagger | Technical credibility in 3.4 s. The code shown is the support gate — it *is* the rigour, not decoration |
| 44.2–48.6 s | 09 Signature | The network returns pushed to both frame edges, lockup centred in cleared space | **DELIVERY OPERATIONS / ANALYTICS** · Santino Cervio · Industrial Engineering — ITBA · Operations · Data · Process improvement · LIVE CASE STUDY / GITHUB · disclaimer | — | Arcs redraw, rule wipes from centre, CTAs stagger up | Attribution and two destinations, with the repository's own disclaimer kept on screen |

## Hero loop — 1920×1080, 30 fps, 10 s, seamless

| Time | Element | Behaviour | Data used |
|---|---|---|---|
| 0–10 s | Lockup, network, histogram | Permanently visible; never animates, so the loop point has nothing to betray | `hourly.json` |
| 0–10 s | Accent radial | Four `sine.inOut` half-cycles of 2.5 s — returns to its exact starting scale | — |
| 0.3–9.7 s | Playhead | Sweeps the histogram, invisible at both ends of the loop | `hourly.json` |
| 0.3–9.7 s | Claim rotator | Three claims in 3.33 s slots: 334,144 orders → 51.0% of the late gap → no validated threshold. All three sit at opacity 0 at t=0 and t=10 | `kpis.csv`, `stage_late_contrasts.csv`, `threshold_assessment.csv` |
| 0–10 s | Order pulses | Four 1.9 s passes per hot link, the last fading out exactly on the loop point | — |

Seamlessness is structural, not a crossfade: every animated property holds an
identical value at t=0 and t=10, verified by comparing snapshots at 0.02 s and
9.98 s.

## A note on the map

The dataset carries **no latitude or longitude** — only `pu_distance` and
`do_distance` in assumed metres (`outputs/data_dictionary.csv`). No city map,
route or zone in this film is geographic. The network is an authored schematic
with fixed constants, and the only spatial claim made anywhere is the distance
**band** contrast, which is real. No geographic data was fabricated.
