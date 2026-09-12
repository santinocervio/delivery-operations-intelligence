---
format: 1920x1080
duration: 48.6s
message: "A complex delivery operation was structured, diagnosed and quantified — and the obvious explanation was tested and rejected before any action was proposed."
arc: "Scale → Rhythm → The wrong answer → The real answer → Concentration → Decision → Build → Signature"
audience: "recruiters and hiring managers in operations, analytics and consulting"
mode: autonomous
---

Every figure in every frame is read from `src/data/*.json`, frozen by
`scripts/extract-data.py` from the repository's published aggregate CSVs, and
re-checked by `scripts/verify-claims.mjs`. No figure is typed by hand into a
composition.

## Frame 1 — Open

- status: animated
- src: compositions/s1-open.html
- duration: 3.8s
- transition_in: cut
- scene: Title lockup over a schematic dispatch network drawing itself in.
- blueprint: logo-assemble-lockup
- rules: svg-path-draw, ambient-glow-bloom
- data: src/data/scale.json

Nodes and curved links draw on across a dark field — a **schematic** dispatch
network, explicitly not a geographic map (the dataset carries no coordinates).
The lockup lands: **DELIVERY OPERATIONS / INTELLIGENCE**, kicker
`INDEPENDENT OPERATIONS CASE STUDY`, spine line
`334,144 orders · 32 days · 4 raw sources`.

## Frame 2 — The operation

- status: animated
- src: compositions/s2-scale.html
- duration: 5.2s
- transition_in: cut
- scene: Six KPI cards assemble into a command grid, every numeral counting up.
- blueprint: dataviz-countup
- rules: counting-dynamic-scale, center-outward-expansion, stat-bars-and-fills
- data: src/data/scale.json

Orders 334,144 · mean service 25.72 min · late >5 min 15.6% · observed
rider-hours 193,501 · matched throughput 1.727 orders per rider-hour · recorded
cost per order 344.60 (unit unverified, and labelled as such on screen).

## Frame 3 — Demand is not evenly distributed

- status: animated
- src: compositions/s3-rhythm.html
- duration: 5.6s
- transition_in: cut
- scene: The real 24-hour demand curve draws, then a playhead scrubs it and reads out the peak.
- blueprint: dataviz-countup
- rules: svg-path-draw, chart-scrub-readout
- data: src/data/hourly.json

All 24 hours, real order counts. The curve is bimodal — lunch 13:00 (26,708)
and dinner 20:00 (45,112). The playhead stops on 21:00, where mean service is
worst among the 20 well-supported hours: 28.85 min.

## Frame 4 — The obvious explanation, tested

- status: animated
- src: compositions/s4-rejected.html
- duration: 7.0s
- transition_in: cut
- scene: The pressure hypothesis is stated, measured, and stamped rejected on held-out dates.
- blueprint: dataviz-countup
- rules: stat-bars-and-fills, chromatic-glitch, depth-of-field-blur
- data: src/data/rejected.json

The film's signature beat. "More orders per rider-hour → more late orders" is
written as a hypothesis, then tested on 108,510 vs 59,818 orders. The measured
difference is **−0.58 pp** and the 95% date-bootstrap interval **[−2.14, +1.25]**
is drawn as a real interval straddling a zero line. The four discovery quartiles
refuse to deteriorate monotonically (15.26 / 16.99 / 15.50 / 16.53%). The stamp
lands: **NO VALIDATED / OPERATIONAL THRESHOLD** — the exact wording of
`threshold_assessment.csv` — confirmed on 10 held-out dates. Closing line:
"The hypothesis was dropped, not decorated."

## Frame 5 — So where does the time actually go?

- status: animated
- src: compositions/s5-diagnosis.html
- duration: 7.4s
- transition_in: cut
- scene: Five process stations carry real stage means above two stacked proportion bars — share of service time, then share of the late gap.
- blueprint: spatial-pan-stations
- rules: stat-bars-and-fills, counting-dynamic-scale
- data: src/data/stages.json

Creation → notification → acceptance → approach → pickup wait → last mile, with
the real means (10.58 / 0.25 / 3.13 / 4.60 / 7.17 min, total 25.73). The view
then switches to the late-versus-on-time gap (6.05 / 0.05 / 1.07 / 2.85 / 1.85,
total 11.88). Stage one dips and returns in both bars to bind them. Payoff: **51.0% of the late gap
accrues before a rider is even notified.**

## Frame 6 — The damage is concentrated

- status: animated
- src: compositions/s6-concentration.html
- duration: 5.8s
- transition_in: cut
- scene: A 3.1% cohort inflates to 36.6% of all pre-dispatch events; a distance ladder climbs beside it.
- blueprint: dataviz-countup
- rules: stat-bars-and-fills, counting-dynamic-scale
- data: src/data/concentration.json

Two proportion bars set 3.1% of orders (10,472) against 36.6% of recorded
pre-dispatch events. That cohort averages 45.88 min against a 25.08 reference —
+20.81 min, CI [19.98, 21.75] — and is 67.1% late >5 min. Beside it, the
restaurant distance ladder (84% of orders) climbs 15.6% → 46.6% pre-event
incidence, with the headline contrast **17.3% → 47.9%, +30.59 pp**.

## Frame 7 — Evidence becomes decision

- status: animated
- src: compositions/s7-action.html
- duration: 6.0s
- transition_in: cut
- scene: Three ranked priorities expand into observation / evidence / action / guardrail rows.
- blueprint: grid-card-assemble
- rules: anchored-layout-expand, stat-bars-and-fills
- data: src/data/actions.json

The three supported priorities from `priorities.csv`, each carrying its real
trigger, affected order count, late >5 min rate, action and **trade-off**. A
persistent banner states what the repository states: these are pilot designs
with monitoring KPIs, not projected savings.

## Frame 8 — How it was built

- status: animated
- src: compositions/s8-stack.html
- duration: 3.4s
- transition_in: cut
- scene: Four fast stations — DATA → ANALYSIS → TOOL → DECISION — under a real code fragment.
- blueprint: grid-card-assemble
- rules: svg-path-draw, discrete-text-sequence
- data: src/data/actions.json

4 raw sources → a reproducible pandas pipeline (seed 42, 500 date-bootstrap
resamples, date-clustered models, 20/10 discovery–holdout) → a Streamlit
decision tool and a Power BI semantic model → 6 findings and 5 ranked
priorities. A real four-line fragment of `delivery_ops/analysis.py` shows the
support gate that decides whether a comparison earns a confidence interval at
all. Stack chips name only what the repository actually uses — SQL is absent
from the project and therefore absent from the film.

## Frame 9 — Signature

- status: animated
- src: compositions/s9-close.html
- duration: 4.4s
- transition_in: cut
- scene: The network returns behind the closing lockup, author line and two CTAs.
- blueprint: titlecard-reveal
- rules: svg-path-draw, ambient-glow-bloom
- data: —

**DELIVERY OPERATIONS ANALYTICS** · Santino Cervio · Industrial Engineering —
ITBA · Operations · Data · Process Improvement. Two CTAs (LIVE CASE STUDY,
GITHUB) and the repository's own disclaimer: an independent portfolio analysis,
not an official PedidosYa product or proof of employment.

## Frame L — Hero loop (separate deliverable)

- status: animated
- src: ../pedidosya-loop/index.html
- duration: 10s
- transition_in: cut
- scene: Seamless 10s background loop for the portfolio project card.
- blueprint: dataviz-countup
- rules: svg-path-draw, sine-wave-loop
- data: src/data/hourly.json, src/data/stages.json

Built from the same tokens and the same frozen data. The lockup, network and
histogram never animate; the radial breathes through four exact half-cycles, a
playhead sweeps the histogram, and three claims rotate in 3.33 s slots. Every
animated property holds the same value at t=0 and t=10, so the loop is seamless
with no crossfade — verified by comparing snapshots at 0.02 s and 9.98 s.
