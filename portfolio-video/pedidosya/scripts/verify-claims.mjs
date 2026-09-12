#!/usr/bin/env node
/**
 * Verify every figure the film shows against the published aggregate evidence.
 *
 * Two kinds of claim are checked, because a composition renders figures in two
 * ways:
 *
 *   text — a string typed into the markup ("45,112 orders"). Checked against
 *          the scene's visible text with tags stripped and whitespace and
 *          Unicode minus signs normalised.
 *   num  — a value the timeline formats at runtime from a data literal. A
 *          labelled regex pulls that exact literal out of the scene and it is
 *          compared numerically to the CSV, within half a unit of the last
 *          digit the film actually displays.
 *
 * Either a figure was typed by hand, or the analysis moved — both fail here.
 *
 *     node scripts/verify-claims.mjs
 */

import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const PROJECT = dirname(dirname(fileURLToPath(import.meta.url)));
const REPO = dirname(dirname(PROJECT));
const ANALYSIS = join(REPO, "outputs", "analysis");

// ---------------------------------------------------------------- CSV
function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    if (quoted) {
      if (ch === '"') {
        if (text[i + 1] === '"') {
          field += '"';
          i += 1;
        } else quoted = false;
      } else field += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === ",") {
      row.push(field);
      field = "";
    } else if (ch === "\n") {
      row.push(field);
      rows.push(row);
      row = [];
      field = "";
    } else if (ch !== "\r") field += ch;
  }
  if (field !== "" || row.length) {
    row.push(field);
    rows.push(row);
  }
  const header = rows.shift();
  return rows
    .filter((r) => r.length === header.length)
    .map((r) => Object.fromEntries(header.map((h, i) => [h, r[i]])));
}

const csv = (name) => parseCsv(readFileSync(join(ANALYSIS, `${name}.csv`), "utf8"));
const findings = JSON.parse(
  readFileSync(join(REPO, "outputs", "executive_findings.json"), "utf8")
);
const finding = (id) => findings.find((f) => f.id === id).evidence;

// ------------------------------------------------------------ source rows
const kpis = csv("kpis")[0];
const stages = csv("stage_summary");
const gaps = csv("stage_late_contrasts");
const contrasts = csv("headline_contrasts");
const priorities = csv("priorities");
const bins = csv("threshold_discovery_bins");
const thresholds = csv("threshold_assessment")[0];
const segments = csv("operational_segments");
const hours = segments.filter((r) => r.family === "hour");

const contrast = (n) => contrasts.find((r) => r.contrast === n);
const hour = (h) => hours.find((r) => Number(r.value_1) === h);
const stage = (k) => stages.find((r) => r.stage === k);
const gap = (k) => gaps.find((r) => r.stage === k);
const priority = (n) => priorities.find((r) => Number(r.priority) === n);
const ladder = (band) =>
  segments.find(
    (r) =>
      r.family === "vertical_distance" && r.value_1 === "restaurants" && r.value_2 === band
  );

const pressure = contrast("High versus low observed orders per rider-hour: late >5min");
const cohort = contrast("At least four pre events versus fewer");
const distance = contrast("Dropoff distance >3km versus <=1km: pre incidence");
const f02 = finding("F02");
const f04 = finding("F04");

// ------------------------------------------------------------ formatting
const group = (n) => String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
const int = (v) => group(Math.round(Number(v)));
const fx = (v, d) => Number(v).toFixed(d);
const pct = (v, d) => (Number(v) * 100).toFixed(d);

// --------------------------------------------------------------- claims
const T = (scene, expect) => ({ kind: "text", scene, expect });
const N = (scene, label, re, expected, decimals) => ({
  kind: "num",
  scene,
  label,
  re,
  expected: Number(expected),
  decimals,
});

const claims = [
  // ---- Scene 1 ---------------------------------------------------------
  T("s1-open", `${int(kpis.orders)} orders`),
  T("s1-open", `${kpis.dates} days`),

  // ---- Scene 2 — scale -------------------------------------------------
  T("s2-scale", `${int(kpis.completed_orders)} completed`),
  T("s2-scale", `${int(kpis.cancelled_orders)} cancelled`),
  T("s2-scale", `median ${fx(kpis.median_min, 2)}`),
  T("s2-scale", `P90 ${fx(kpis.p90_min, 2)}`),
  T("s2-scale", `${kpis.dates} recorded dates`),
  T("s2-scale", `${kpis.hours} hours`),
  N("s2-scale", "orders", /orders:\s*([\d.]+)/, kpis.orders, 0),
  N("s2-scale", "mean service", /mean_min:\s*([\d.]+)/, kpis.mean_min, 2),
  N("s2-scale", "late >5 min", /late5_pct:\s*([\d.]+)/, Number(kpis.late5_rate) * 100, 1),
  N("s2-scale", "rider-hours", /rider_hours:\s*([\d.]+)/, f04.observed_rider_hours, 0),
  N("s2-scale", "throughput", /throughput:\s*([\d.]+)/, f04.matched_throughput, 3),
  N("s2-scale", "cost per order", /cost_per_order:\s*([\d.]+)/, kpis.recorded_cost_mean, 2),

  // ---- Scene 3 — hourly rhythm ----------------------------------------
  T("s3-rhythm", `${int(hour(20).orders)} orders`),
  T("s3-rhythm", `${fx(hour(21).mean_min, 2)} min mean`),
  T("s3-rhythm", `${hours.filter((r) => r.descriptive_support === "True").length} well-supported hours`),
  N("s3-rhythm", "hour 20 orders", /\[20,\s*(\d+),/, hour(20).orders, 0),
  N("s3-rhythm", "hour 21 orders", /\[21,\s*(\d+),/, hour(21).orders, 0),
  N("s3-rhythm", "hour 21 mean", /\[21,\s*\d+,\s*([\d.]+)/, hour(21).mean_min, 2),
  N("s3-rhythm", "hour 13 orders", /\[13,\s*(\d+),/, hour(13).orders, 0),

  // ---- Scene 4 — the rejected hypothesis ------------------------------
  T("s4-rejected", `${int(pressure.exposed_orders)} orders`),
  T("s4-rejected", `${int(pressure.reference_orders)} orders`),
  T("s4-rejected", `${pct(pressure.exposed_mean, 2)}% late`),
  T("s4-rejected", `${pct(pressure.reference_mean, 2)}% late`),
  T("s4-rejected", `${pressure.bootstrap_samples} resamples`),
  T("s4-rejected", `${thresholds.holdout_dates} held-out dates`),
  T("s4-rejected", thresholds.status.toUpperCase()),
  N("s4-rejected", "point estimate", /point:\s*(-?[\d.]+)/, Number(pressure.difference) * 100, 2),
  N("s4-rejected", "CI low", /low:\s*(-?[\d.]+)/, Number(pressure.ci_low) * 100, 2),
  N("s4-rejected", "CI high", /high:\s*(-?[\d.]+)/, Number(pressure.ci_high) * 100, 2),
  ...bins.map((b, i) =>
    N(
      "s4-rejected",
      `discovery ${b.bin}`,
      new RegExp(`\\["${b.bin}",\\s*([\\d.]+)\\]`),
      Number(b.late5_rate) * 100,
      2
    )
  ),

  // ---- Scene 5 — stage decomposition ----------------------------------
  ...stages.map((s) => T("s5-diagnosis", fx(s.mean_min, 2))),
  T("s5-diagnosis", `${fx(stages[0].total_mean_min, 2)} min`),
  T("s5-diagnosis", `${fx(gaps[0].total_difference_min, 2)} min`),
  T("s5-diagnosis", `${pct(gap("t_created_to_notify_min").share_of_total_difference, 1)}%`),
  ...stages.map((s, i) =>
    N(
      "s5-diagnosis",
      `time share ${i + 1}`,
      new RegExp(`TIME_SHARE = \\[[^\\]]*?(?:[\\d.]+,\\s*){${i}}([\\d.]+)`, "s"),
      s.share_total_time,
      4
    )
  ),
  ...gaps.map((g, i) =>
    N(
      "s5-diagnosis",
      `gap share ${i + 1}`,
      new RegExp(`GAP_SHARE = \\[[^\\]]*?(?:[\\d.]+,\\s*){${i}}([\\d.]+)`, "s"),
      g.share_of_total_difference,
      4
    )
  ),

  // ---- Scene 6 — concentration ----------------------------------------
  T("s6-concentration", `${int(f02.orders)} orders`),
  T("s6-concentration", `${fx(f02.service_mean_min, 2)} min`),
  T("s6-concentration", `${fx(cohort.reference_mean, 2)} min`),
  T("s6-concentration", `+${fx(cohort.difference, 2)} min`),
  T("s6-concentration", `[${fx(cohort.ci_low, 2)}, ${fx(cohort.ci_high, 2)}]`),
  T("s6-concentration", `${pct(f02.late5_rate, 1)}%`),
  T("s6-concentration", `${pct(distance.reference_mean, 1)}% at 1 km or less`),
  T("s6-concentration", `${pct(distance.exposed_mean, 1)}% above 3 km`),
  T("s6-concentration", `+${fx(Number(distance.difference) * 100, 2)} pp`),
  T(
    "s6-concentration",
    `[${fx(Number(distance.ci_low) * 100, 2)}, ${fx(Number(distance.ci_high) * 100, 2)}]`
  ),
  N("s6-concentration", "order share", /ORDER_SHARE = ([\d.]+)/, f02.order_share, 3),
  N("s6-concentration", "pre-event share", /EVENT_SHARE = ([\d.]+)/, f02.pre_event_share, 3),
  ...[
    ["≤0.5 km", "<=0.5km"],
    ["0.5–1 km", "0.5-1km"],
    ["1–2 km", "1-2km"],
    ["2–3 km", "2-3km"],
    ["> 3 km", ">3km"],
  ].map(([label, band]) =>
    N(
      "s6-concentration",
      `ladder ${band}`,
      new RegExp(`\\["${label}",\\s*([\\d.]+),`),
      Number(ladder(band).pre_rate) * 100,
      1
    )
  ),

  // ---- Scene 7 — the decision -----------------------------------------
  T("s7-action", `${int(priority(1).affected_orders)} orders`),
  T("s7-action", `${int(priority(3).affected_orders)} orders`),
  T("s7-action", `${pct(priority(1).affected_share, 1)}% of volume`),
  T("s7-action", `${pct(priority(3).affected_share, 1)}% of volume`),
  T("s7-action", `${pct(priority(1).late5_rate, 1)}%`),
  T("s7-action", `${pct(priority(2).late5_rate, 1)}%`),
  T("s7-action", `${pct(priority(3).late5_rate, 1)}%`),
  T("s7-action", `P90 of ${fx(stage("t_created_to_notify_min").p90_min, 2)} min`),
  T("s7-action", `P90 of ${fx(stage("t_wait_at_pu_min").p90_min, 2)} min`),
  ...[1, 2, 3].map((n, i) =>
    N(
      "s7-action",
      `late rate ${n}`,
      new RegExp(`LATE_RATES = \\[(?:[\\d.]+,\\s*){${i}}([\\d.]+)`),
      priority(n).late5_rate,
      3
    )
  ),
];

// ------------------------------------------------------------------- run
const cache = new Map();
const source = (scene) => {
  if (!cache.has(scene)) {
    cache.set(scene, readFileSync(join(PROJECT, "compositions", `${scene}.html`), "utf8"));
  }
  return cache.get(scene);
};

// Visible text only: drop <style>/<script>, strip tags, normalise minus signs.
const visible = (scene) =>
  source(scene)
    .replace(/<style[\s\S]*?<\/style>/g, " ")
    .replace(/<script[\s\S]*?<\/script>/g, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/&gt;/g, ">")
    .replace(/&lt;/g, "<")
    .replace(/[−–]/g, "-")
    .replace(/\s+/g, " ");

const norm = (s) => s.replace(/[−–]/g, "-").replace(/\s+/g, " ");

let failed = 0;
for (const c of claims) {
  if (c.kind === "text") {
    if (!visible(c.scene).includes(norm(c.expect))) {
      failed += 1;
      console.error(`FAIL  ${c.scene}  not shown on screen: "${c.expect}"`);
    }
    continue;
  }
  const m = source(c.scene).match(c.re);
  if (!m) {
    failed += 1;
    console.error(`FAIL  ${c.scene}  ${c.label}: data literal not found`);
    continue;
  }
  const got = Number(m[1]);
  const tol = 0.5 * 10 ** -c.decimals;
  if (Math.abs(got - c.expected) > tol) {
    failed += 1;
    console.error(
      `FAIL  ${c.scene}  ${c.label}: composition has ${got}, evidence says ${c.expected}`
    );
  }
}

const total = claims.length;
if (failed) {
  console.error(`\n${failed} of ${total} claims disagree with outputs/analysis/.`);
  process.exit(1);
}
console.log(`All ${total} on-screen figures agree with outputs/analysis/ and executive_findings.json.`);
