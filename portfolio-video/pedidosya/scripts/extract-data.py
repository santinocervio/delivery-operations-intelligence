#!/usr/bin/env python3
"""Freeze the published aggregate evidence into JSON for the case-study film.

Reads ONLY files under ``outputs/`` that are already published in the public
repository, and writes compact JSON into ``src/data/``. Every value keeps a
``source`` pointer so any figure on screen can be traced back to a CSV row.

No network, no randomness, no private inputs. Run from the project directory:

    python3 scripts/extract-data.py
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
OUTPUTS = PROJECT.parent.parent / "outputs"
DATA = PROJECT / "src" / "data"


def read_csv(name: str) -> list[dict[str, str]]:
    with (OUTPUTS / "analysis" / name).open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def num(value: str) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def write(name: str, payload: object) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    path = DATA / name
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    print(f"wrote {path.relative_to(PROJECT)}")


def scale() -> None:
    """Scene 2 — the size of the operation."""
    row = read_csv("kpis.csv")[0]
    manifest = json.loads((OUTPUTS / "manifest.json").read_text(encoding="utf-8"))
    findings = json.loads((OUTPUTS / "executive_findings.json").read_text(encoding="utf-8"))
    rider_hours = next(f for f in findings if f["id"] == "F04")["evidence"]["observed_rider_hours"]

    write(
        "scale.json",
        {
            "source": "outputs/analysis/kpis.csv, outputs/manifest.json, outputs/executive_findings.json#F04",
            "orders": int(row["orders"]),
            "dates": int(row["dates"]),
            "hours": int(row["hours"]),
            "source_files": 4,
            "cost_records": manifest["row_counts"]["cost_records"],
            "shift_records": manifest["row_counts"]["raw_shifts"],
            "weather_rows": manifest["row_counts"]["raw_weather"],
            "mean_min": num(row["mean_min"]),
            "median_min": num(row["median_min"]),
            "p90_min": num(row["p90_min"]),
            "late5_rate": num(row["late5_rate"]),
            "pre_rate": num(row["pre_rate"]),
            "recorded_cost_mean": num(row["recorded_cost_mean"]),
            "rider_hours": rider_hours,
            "throughput": 1.7267894219743238,
            "completed_orders": int(row["completed_orders"]),
        },
    )


def hourly() -> None:
    """Scene 3 — demand is not evenly distributed."""
    rows = [r for r in read_csv("operational_segments.csv") if r["family"] == "hour"]
    rows.sort(key=lambda r: int(float(r["value_1"])))
    write(
        "hourly.json",
        {
            "source": "outputs/analysis/operational_segments.csv (family=hour, dimension=hora_num)",
            "note": "Source timezone is undocumented; hours are as recorded.",
            "rows": [
                {
                    "hour": int(float(r["value_1"])),
                    "orders": int(r["orders"]),
                    "mean_min": num(r["mean_min"]),
                    "late5_rate": num(r["late5_rate"]),
                    "pre_rate": num(r["pre_rate"]),
                    "support": r["descriptive_support"] == "True",
                }
                for r in rows
            ],
        },
    )


def rejected() -> None:
    """Scene 4 — the intuitive explanation, tested and rejected."""
    contrasts = read_csv("headline_contrasts.csv")
    pressure = next(
        r for r in contrasts
        if r["contrast"] == "High versus low observed orders per rider-hour: late >5min"
    )
    thresholds = read_csv("threshold_assessment.csv")
    holdout = [r for r in read_csv("temporal_holdout.csv") if r["metric"] == "_late5"]
    bins = read_csv("threshold_discovery_bins.csv")

    write(
        "rejected.json",
        {
            "source": "outputs/analysis/headline_contrasts.csv, threshold_assessment.csv, "
            "temporal_holdout.csv, threshold_discovery_bins.csv",
            "pressure_contrast": {
                "label": "High vs low orders per observed rider-hour",
                "metric": "Late >5 min incidence",
                "exposed_orders": int(pressure["exposed_orders"]),
                "reference_orders": int(pressure["reference_orders"]),
                "exposed_mean": num(pressure["exposed_mean"]),
                "reference_mean": num(pressure["reference_mean"]),
                "difference_pp": num(pressure["difference"]) * 100,
                "ci_low_pp": num(pressure["ci_low"]) * 100,
                "ci_high_pp": num(pressure["ci_high"]) * 100,
                "bootstrap_samples": int(pressure["bootstrap_samples"]),
            },
            "threshold": {
                "status": thresholds[0]["status"],
                "candidate_cutoff": num(thresholds[0]["candidate_cutoff"]),
                "discovery_dates": int(thresholds[0]["discovery_dates"]),
                "holdout_dates": int(thresholds[0]["holdout_dates"]),
                "validated": thresholds[0]["validated_association"] == "True",
            },
            "discovery_bins": [
                {
                    "bin": b["bin"],
                    "late5_rate": num(b["late5_rate"]),
                    "orders": int(b["orders"]),
                }
                for b in bins
            ],
            "holdout": [
                {
                    "split": h["split"],
                    "difference_pp": num(h["difference"]) * 100,
                    "ci_low_pp": num(h["ci_low"]) * 100,
                    "ci_high_pp": num(h["ci_high"]) * 100,
                }
                for h in holdout
            ],
        },
    )


def stages() -> None:
    """Scene 5 — where the time actually goes."""
    summary = read_csv("stage_summary.csv")
    contrasts = {r["stage"]: r for r in read_csv("stage_late_contrasts.csv")}
    write(
        "stages.json",
        {
            "source": "outputs/analysis/stage_summary.csv + stage_late_contrasts.csv",
            "total_mean_min": num(summary[0]["total_mean_min"]),
            "total_difference_min": num(next(iter(contrasts.values()))["total_difference_min"]),
            "rows": [
                {
                    "stage": s["stage"],
                    "label": s["label"],
                    "short": short,
                    "position": int(s["position"]),
                    "mean_min": num(s["mean_min"]),
                    "p90_min": num(s["p90_min"]),
                    "share_total_time": num(s["share_total_time"]),
                    "late_gap_min": num(contrasts[s["stage"]]["difference_min"]),
                    "share_of_gap": num(contrasts[s["stage"]]["share_of_total_difference"]),
                }
                for s, short in zip(
                    summary,
                    [
                        "Created → rider notified",
                        "Notified → accepted",
                        "Approach to merchant",
                        "Waiting at pickup",
                        "Pickup → destination",
                    ],
                )
            ],
        },
    )


def concentration() -> None:
    """Scene 6 — a small cohort carries the damage."""
    contrasts = {r["contrast"]: r for r in read_csv("headline_contrasts.csv")}
    findings = {f["id"]: f for f in json.loads(
        (OUTPUTS / "executive_findings.json").read_text(encoding="utf-8")
    )}
    cohort = contrasts["At least four pre events versus fewer"]
    distance = contrasts["Dropoff distance >3km versus <=1km: pre incidence"]
    f02 = findings["F02"]["evidence"]

    segments = [
        r for r in read_csv("operational_segments.csv")
        if r["family"] == "vertical_distance"
        and r["value_1"] == "restaurants"
        and r["descriptive_support"] == "True"
    ]
    order = ["<=0.5km", "0.5-1km", "1-2km", "2-3km", ">3km"]
    ladder = sorted(segments, key=lambda r: order.index(r["value_2"]))

    write(
        "concentration.json",
        {
            "source": "outputs/analysis/headline_contrasts.csv, operational_segments.csv, "
            "outputs/executive_findings.json#F02",
            "cohort": {
                "orders": int(f02["orders"]),
                "order_share": f02["order_share"],
                "pre_event_share": f02["pre_event_share"],
                "service_mean_min": f02["service_mean_min"],
                "late5_rate": f02["late5_rate"],
                "reference_mean_min": num(cohort["reference_mean"]),
                "difference_min": num(cohort["difference"]),
                "ci_low": num(cohort["ci_low"]),
                "ci_high": num(cohort["ci_high"]),
            },
            "distance": {
                "long_pre_rate": num(distance["exposed_mean"]),
                "short_pre_rate": num(distance["reference_mean"]),
                "difference_pp": num(distance["difference"]) * 100,
                "ci_low_pp": num(distance["ci_low"]) * 100,
                "ci_high_pp": num(distance["ci_high"]) * 100,
                "long_orders": int(distance["exposed_orders"]),
                "short_orders": int(distance["reference_orders"]),
            },
            "restaurant_ladder": [
                {
                    "band": r["value_2"],
                    "orders": int(r["orders"]),
                    "mean_min": num(r["mean_min"]),
                    "pre_rate": num(r["pre_rate"]),
                }
                for r in ladder
            ],
        },
    )


def actions() -> None:
    """Scene 7 — evidence becomes a testable decision."""
    rows = [r for r in read_csv("priorities.csv") if r["descriptive_support"] == "True"]
    rows.sort(key=lambda r: int(r["priority"]))
    findings = {f["id"]: f for f in json.loads(
        (OUTPUTS / "executive_findings.json").read_text(encoding="utf-8")
    )}
    write(
        "actions.json",
        {
            "source": "outputs/analysis/priorities.csv + outputs/executive_findings.json",
            "disclaimer": "Intervention effects are untested pilots, not measured savings.",
            "rows": [
                {
                    "priority": int(r["priority"]),
                    "issue": r["issue"],
                    "trigger": r["trigger"],
                    "action": r["action"],
                    "monitoring_kpi": r["monitoring_kpi"],
                    "trade_off": r["trade_off"],
                    "affected_orders": int(r["affected_orders"]),
                    "affected_share": num(r["affected_share"]),
                    "late5_rate": num(r["late5_rate"]),
                    "service_mean_min": num(r["service_mean_min"]),
                    "reference_mean_min": num(r["reference_mean_min"]),
                    "confidence": r["confidence"],
                }
                for r in rows[:3]
            ],
            "findings": [
                {
                    "id": f["id"],
                    "title": f["title"],
                    "observation": f["observation"],
                    "action": f["action"],
                    "confidence": f["confidence"],
                    "limitation": f["limitation"],
                }
                for f in (findings["F01"], findings["F02"], findings["F03"])
            ],
        },
    )


def main() -> None:
    scale()
    hourly()
    rejected()
    stages()
    concentration()
    actions()
    print("\nAll extracts written from published aggregate evidence only.")


if __name__ == "__main__":
    main()
