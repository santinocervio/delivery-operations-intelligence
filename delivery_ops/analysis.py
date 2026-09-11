"""Evidence-first operational analysis; no estimated effect is labelled causal.

The public entry point accepts the ETL's order and calendar-hour tables. All
figures in the result and CSVs are computed from those inputs. Date bootstrap
intervals resample whole dates, preserving within-date dependence. Missing
measurements are not converted into successful outcomes or zero capacity.
"""
from __future__ import annotations

import json
import math
import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

STAGES = {
    "t_created_to_notify_min": "Creation to final rider notification",
    "t_notify_to_accept_min": "Final rider notification to acceptance",
    "t_accept_to_pu_arrival_min": "Final rider approach to merchant",
    "t_wait_at_pu_min": "Final rider waiting at pickup",
    "t_last_mile_min": "Pickup to destination arrival",
}
SUPPORT = {"descriptive_orders": 100, "descriptive_dates": 5,
           "inference_hours": 30, "inference_dates": 10}


def _json(value: Any) -> Any:
    """Convert numpy/pandas scalars, NaN and infinity to strict JSON values."""
    if isinstance(value, dict):
        return {str(k): _json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)):
        return [_json(v) for v in value]
    if isinstance(value, (pd.Timestamp, np.datetime64)):
        return pd.Timestamp(value).isoformat()
    if value is None or value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, (np.integer, int)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return float(value) if math.isfinite(float(value)) else None
    return str(value) if not isinstance(value, str) else value


def _num(d: pd.DataFrame, name: str) -> pd.Series:
    if name not in d:
        return pd.Series(np.nan, index=d.index, dtype=float)
    return pd.to_numeric(d[name], errors="coerce").replace([np.inf, -np.inf], np.nan)


def _flag(d: pd.DataFrame, name: str, fallback: pd.Series) -> pd.Series:
    return d[name].fillna(False).astype(bool) if name in d else fallback.fillna(False)


def _divide(a: float, b: float) -> float:
    return float(a / b) if pd.notna(b) and b > 0 and pd.notna(a) else np.nan


def _total(s: pd.Series) -> float:
    return s.sum(min_count=1)


def _prepare(orders: pd.DataFrame, hours: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    d, h = orders.copy(), hours.copy()
    if "id_pedido" not in d or d.id_pedido.isna().any() or d.id_pedido.duplicated().any():
        raise ValueError("Analysis requires one non-null unique id_pedido per order.")
    if "date_hour" not in d or "date_hour" not in h:
        raise ValueError("Order and hour tables must include date_hour.")
    for frame in (d, h):
        frame["date_hour"] = pd.to_datetime(frame.date_hour, errors="coerce")
        if frame.date_hour.isna().any():
            raise ValueError("Invalid calendar-hour keys cannot be analyzed.")
        frame["fecha"] = frame.date_hour.dt.normalize()
        frame["hora_num"] = frame.date_hour.dt.hour
        frame["dia_semana"] = frame.date_hour.dt.day_name()
    if h.date_hour.duplicated().any():
        raise ValueError("Hour table must have unique date_hour keys.")
    # Within-clock descriptive bands separate day-to-day variation from the
    # mechanical alignment of global demand and supply with the daily cycle.
    for name, source in [("relative_demand_band", "pedidos"), ("relative_supply_band", "rider_hours_total")]:
        if name not in h:
            h[name] = "Unknown"
            values = _num(h, source)
            for _, indices in h.groupby("hora_num").groups.items():
                x = values.loc[indices]
                if x.notna().any():
                    low, high = x.dropna().quantile([1/3, 2/3])
                    labels = pd.Series(np.select([x.le(low), x.le(high)], ["Low", "Medium"], default="High"), index=x.index)
                    h.loc[indices, name] = labels.where(x.notna(), "Unknown")
    actual, promised = _num(d, "actual_min"), _num(d, "promised_min")
    completed = _num(d, "completed_flag").eq(1)
    d["_service"] = actual.where(_flag(d, "service_eligible", completed & actual.ge(0)))
    late_ok = _flag(d, "late_eligible", completed & actual.ge(0) & promised.ge(0))
    for source, target, tolerance in [("tardio", "_late", 0), ("tardio_5min", "_late5", 5)]:
        values = _num(d, source) if source in d else (actual - promised > tolerance).astype(float)
        d[target] = values.where(late_ok & values.isin([0, 1]))
    for name in ("pre_any", "post_any"):
        d[name] = _num(d, name).where(_num(d, name).isin([0, 1]))
    for name in ("pre_undispatches", "post_undispatches", "cpo_total", "cpo_undispatch", "order_value"):
        d[name] = _num(d, name)
    for name in STAGES:
        d[name] = _num(d, name)
    valid_chain = d[list(STAGES)].notna().all(axis=1) & d[list(STAGES)].ge(0).all(axis=1)
    d["_process_ok"] = _flag(d, "process_eligible", completed & valid_chain) & valid_chain
    d["_process_total"] = d[list(STAGES)].sum(axis=1, min_count=len(STAGES)).where(d._process_ok)
    for name in ("lluvia", "vertical", "vehicle", "dist_bucket", "ticket_bucket",
                 "demand_band", "supply_band", "relative_demand_band", "relative_supply_band",
                 "pressure_band", "peak_hour", "event_type"):
        if name not in d:
            if name in h:
                d[name] = d.date_hour.map(h.set_index("date_hour")[name])
            else:
                d[name] = "Unknown"
        d[name] = d[name].astype("string").fillna("Unknown")
    d["_distance_band"] = pd.cut(_num(d, "do_km"), [-np.inf, .5, 1, 2, 3, np.inf],
                                 labels=["<=0.5km", "0.5-1km", "1-2km", "2-3km", ">3km"])
    d["_distance_band"] = d._distance_band.astype("string").fillna("Unknown")
    if "partial_boundary_day" not in h:
        h["partial_boundary_day"] = False
    if "rider_hours_total" not in h:
        h["rider_hours_total"] = np.nan
    if "utr_proxy" not in h:
        h["utr_proxy"] = _num(h, "pedidos") / _num(h, "rider_hours_total").where(_num(h, "rider_hours_total") > 0)
    d["_tail95"] = d._service.gt(d._service.quantile(.95)).astype(float).where(d._service.notna())
    return d, h


def _metrics(g: pd.DataFrame) -> dict:
    s, cost = g._service.dropna(), g.cpo_total.dropna()
    n, days = len(g), g.fecha.nunique()
    return {
        "orders": n, "hours": g.date_hour.nunique(), "dates": days,
        "descriptive_support": n >= SUPPORT["descriptive_orders"] and days >= SUPPORT["descriptive_dates"],
        "service_orders": len(s), "mean_min": s.mean(), "median_min": s.median(),
        "p75_min": s.quantile(.75), "p90_min": s.quantile(.90), "p95_min": s.quantile(.95),
        "variance_min2": s.var(), "late_eligible_orders": g._late.count(),
        "tail95_orders": _total(g._tail95), "tail95_rate": g._tail95.mean(),
        "late_orders": _total(g._late), "late_rate": g._late.mean(), "late5_rate": g._late5.mean(),
        "pre_eligible_orders": g.pre_any.count(), "pre_affected_orders": _total(g.pre_any),
        "pre_rate": g.pre_any.mean(), "pre_events": _total(g.pre_undispatches),
        "post_eligible_orders": g.post_any.count(), "post_affected_orders": _total(g.post_any),
        "post_rate": g.post_any.mean(), "post_events": _total(g.post_undispatches),
        "cost_known_orders": len(cost), "recorded_cost_total": _total(cost),
        "recorded_cost_mean": cost.mean(), "recorded_aborted_leg_cost": _total(g.cpo_undispatch),
        "recorded_order_value_mean": g.order_value.mean(),
    }


def _segments(d: pd.DataFrame) -> pd.DataFrame:
    dimensions = {
        "hour": ["hora_num"], "weekday_hour": ["dia_semana", "hora_num"],
        "weather": ["lluvia"], "weather_hour": ["lluvia", "hora_num"],
        "weather_demand": ["lluvia", "demand_band"], "weather_supply": ["lluvia", "supply_band"],
        "demand_supply": ["demand_band", "supply_band"],
        "relative_demand_supply": ["relative_demand_band", "relative_supply_band"],
        "weather_relative_supply": ["lluvia", "relative_supply_band"],
        "peak_weather_supply": ["peak_hour", "lluvia", "supply_band"],
        "weekday_supply": ["dia_semana", "supply_band"],
        "vertical_distance": ["vertical", "_distance_band"],
        "vehicle_ticket": ["vehicle", "ticket_bucket"], "event_hour": ["event_type", "hora_num"],
        "pressure": ["pressure_band"],
    }
    rows = []
    for family, keys in dimensions.items():
        for values, g in d.groupby(keys, observed=True, dropna=False, sort=True):
            if not isinstance(values, tuple):
                values = (values,)
            row = {"family": family, "segment": " | ".join(map(str, values)), **_metrics(g)}
            row.update({f"dimension_{i+1}": col for i, col in enumerate(keys)})
            row.update({f"value_{i+1}": str(val) for i, val in enumerate(values)})
            rows.append(row)
    return pd.DataFrame(rows)


def _stages(d: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    p = d.loc[d._process_ok].copy()
    total = p._process_total.mean()
    rows = []
    for position, (name, label) in enumerate(STAGES.items(), 1):
        s = p[name]
        rows.append({"stage": name, "label": label, "position": position, "orders": len(p),
                     "mean_min": s.mean(), "median_min": s.median(), "p75_min": s.quantile(.75),
                     "p90_min": s.quantile(.90), "p95_min": s.quantile(.95), "variance_min2": s.var(),
                     "share_total_time": _divide(s.mean(), total), "total_mean_min": total})
    stages = pd.DataFrame(rows)
    late = p[p._late.notna()]
    comparison = []
    a, b = late[late._late.eq(1)], late[late._late.eq(0)]
    total_diff = a._process_total.mean() - b._process_total.mean()
    for name, label in STAGES.items():
        delta = a[name].mean() - b[name].mean()
        comparison.append({"stage": name, "label": label, "late_orders": len(a), "on_time_orders": len(b),
                           "late_mean_min": a[name].mean(), "on_time_mean_min": b[name].mean(),
                           "difference_min": delta, "share_of_total_difference": _divide(delta, total_diff),
                           "total_difference_min": total_diff})
    by_segment = []
    for dims in (["demand_band", "supply_band"], ["relative_demand_band", "relative_supply_band"],
                 ["lluvia", "hora_num"], ["pressure_band"]):
        for vals, g in p.groupby(dims, observed=True, dropna=False):
            vals = vals if isinstance(vals, tuple) else (vals,)
            for name, label in STAGES.items():
                by_segment.append({"family": "_".join(dims), "segment": " | ".join(map(str, vals)),
                                   "stage": name, "label": label, "orders": len(g), "dates": g.fecha.nunique(),
                                   "mean_min": g[name].mean(), "p90_min": g[name].quantile(.9),
                                   "share_total_time": _divide(g[name].mean(), g._process_total.mean())})
    completed_n = int(_num(d, "completed_flag").eq(1).sum())
    best = stages.loc[stages.mean_min.idxmax()] if stages.mean_min.notna().any() else None
    summary = {"eligible_orders": len(p), "completed_orders": completed_n,
               "coverage": _divide(len(p), completed_n), "mean_total_min": total,
               "main_stage": None if best is None else best.label,
               "main_stage_mean_min": None if best is None else best.mean_min,
               "stages": stages.to_dict("records"), "late_contributions": comparison,
               "reconciliation_mean_error_min": (p._process_total - p._service).mean(),
               "reconciliation_max_abs_error_min": (p._process_total - p._service).abs().max(),
               "limitation": "The initial interval ends at the final recorded rider notification. It does not identify individual rejection attempts or isolate dispatcher queue time."}
    return stages, pd.DataFrame(comparison), pd.DataFrame(by_segment), summary


def date_bootstrap_contrast(data: pd.DataFrame, value: str, exposure: pd.Series,
                            *, name: str, seed: int = 42, samples: int = 500) -> dict:
    """Difference of pooled means (exposed minus reference), resampling dates.

    Unknown exposure and outcome values are excluded and their exclusion is
    visible through group denominators. Ineligible comparisons retain estimates
    but receive no confidence interval or significance label.
    """
    v = _num(data, value)
    e = pd.Series(exposure, index=data.index).astype("boolean")
    x = pd.DataFrame({"date": pd.to_datetime(data.fecha).dt.normalize(), "hour": data.date_hour,
                      "v": v, "e": e}).dropna()
    a, b = x[x.e], x[~x.e]
    supported = min(len(a), len(b)) >= SUPPORT["descriptive_orders"] and (
        min(a.date.nunique(), b.date.nunique()) >= SUPPORT["inference_dates"] and
        min(a.hour.nunique(), b.hour.nunique()) >= SUPPORT["inference_hours"])
    result = {"contrast": name, "metric": value, "exposed_orders": len(a), "reference_orders": len(b),
              "exposed_hours": a.hour.nunique(), "reference_hours": b.hour.nunique(),
              "exposed_dates": a.date.nunique(), "reference_dates": b.date.nunique(),
              "exposed_mean": a.v.mean(), "reference_mean": b.v.mean(),
              "difference": a.v.mean() - b.v.mean(), "ci_low": np.nan, "ci_high": np.nan,
              "inference_eligible": supported, "bootstrap_samples": 0,
              "reason": "Whole-date bootstrap; association only." if supported else "Insufficient independent-date/hour/group support; descriptive comparison only."}
    if not supported or samples <= 0:
        return result
    by_day = x.groupby(["date", "e"], observed=True).v.agg(["sum", "count"]).unstack("e").fillna(0)
    dates = by_day.index
    sums_a = by_day[("sum", True)].to_numpy(float)
    sums_b = by_day[("sum", False)].to_numpy(float)
    n_a = by_day[("count", True)].to_numpy(float)
    n_b = by_day[("count", False)].to_numpy(float)
    draws = np.random.default_rng(seed).integers(0, len(dates), size=(samples, len(dates)))
    da, db = n_a[draws].sum(axis=1), n_b[draws].sum(axis=1)
    ok = (da > 0) & (db > 0)
    differences = sums_a[draws].sum(axis=1)[ok] / da[ok] - sums_b[draws].sum(axis=1)[ok] / db[ok]
    if len(differences):
        result.update(ci_low=np.quantile(differences, .025), ci_high=np.quantile(differences, .975),
                      bootstrap_samples=len(differences))
    return result


def _contrasts(d: pd.DataFrame, seed: int, samples: int) -> pd.DataFrame:
    d = d.copy()
    d["_tail95"] = d._service.gt(d._service.quantile(.95)).astype(float).where(d._service.notna())
    do = _num(d, "do_km")
    wet = _num(d, "precip_mm").gt(0).astype("boolean").mask(_num(d, "precip_mm").isna())
    pressure = d.pressure_band.map({"High": True, "Low": False}).astype("boolean")
    orphans = d.pre_undispatches.ge(4).astype("boolean").mask(d.pre_undispatches.isna())
    distance = pd.Series(pd.NA, index=d.index, dtype="boolean")
    distance.loc[do.gt(3)] = True
    distance.loc[do.ge(0) & do.le(1)] = False
    high_demand_supply = d.supply_band.map({"Low": True, "High": False}).astype("boolean").where(d.demand_band.eq("High"))
    low_demand_supply = d.supply_band.map({"High": True, "Low": False}).astype("boolean").where(d.demand_band.eq("Low"))
    relative_high = d.relative_supply_band.map({"Low": True, "High": False}).astype("boolean").where(d.relative_demand_band.eq("High"))
    relative_low = d.relative_supply_band.map({"High": True, "Low": False}).astype("boolean").where(d.relative_demand_band.eq("Low"))
    peak = d.peak_hour.str.lower().isin(["true", "1"])
    peak_known = d.peak_hour.str.lower().isin(["true", "false", "1", "0"])
    specs = [
        ("Late versus on-time completed orders", "_service", d._late.astype("boolean")),
        ("Post-undispatch exposure versus no post-undispatch", "_service", d.post_any.astype("boolean")),
        ("At least four pre events versus fewer", "_service", orphans),
        ("At least four pre events versus fewer: recorded cost", "cpo_total", orphans),
        ("Dropoff distance >3km versus <=1km: pre incidence", "pre_any", distance),
        ("Observed wet versus dry hours: service", "_service", wet),
        ("Observed wet versus dry hours: recorded cost", "cpo_total", wet),
        ("High versus low observed orders per rider-hour: late >5min", "_late5", pressure),
        ("High versus low observed orders per rider-hour: pre incidence", "pre_any", pressure),
        ("High demand: low versus high observed supply, pre incidence", "pre_any", high_demand_supply),
        ("High demand: low versus high observed supply, late >5min", "_late5", high_demand_supply),
        ("Low demand: high versus low observed supply, recorded cost", "cpo_total", low_demand_supply),
        ("Low demand: high versus low observed supply, late >5min", "_late5", low_demand_supply),
        ("Peak hours: observed wet versus dry service", "_service", wet.where(peak & peak_known)),
        ("Non-peak hours: observed wet versus dry service", "_service", wet.where(~peak & peak_known)),
        ("Peak hours: observed wet versus dry P95-tail incidence", "_tail95", wet.where(peak & peak_known)),
        ("Within-clock high demand: low versus high supply, pre incidence", "pre_any", relative_high),
        ("Within-clock high demand: low versus high supply, late >5min", "_late5", relative_high),
        ("Within-clock high demand: low versus high supply, service", "_service", relative_high),
        ("Within-clock high demand: low versus high supply, P95-tail incidence", "_tail95", relative_high),
        ("Within-clock low demand: high versus low supply, recorded cost", "cpo_total", relative_low),
        ("Within-clock low demand: high versus low supply, late >5min", "_late5", relative_low),
    ]
    return pd.DataFrame([date_bootstrap_contrast(d, value, exposure, name=name, seed=seed+i, samples=samples)
                         for i, (name, value, exposure) in enumerate(specs)])


def _contrast_evidence(contrasts: pd.DataFrame, name: str) -> dict:
    row = contrasts.loc[contrasts.contrast.eq(name)]
    if row.empty:
        return {"comparison": name, "status": "unavailable"}
    r = row.iloc[0]
    return {"comparison": name, "difference": r.difference, "ci_low": r.ci_low, "ci_high": r.ci_high,
            "exposed_orders": r.exposed_orders, "reference_orders": r.reference_orders,
            "exposed_dates": r.exposed_dates, "reference_dates": r.reference_dates,
            "inference_eligible": r.inference_eligible}


def _evidence_text(evidence: dict) -> str:
    return json.dumps(_json(evidence), ensure_ascii=False, allow_nan=False)


def _weather(d: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    rows = []
    for label, g in d.groupby("lluvia", observed=True):
        rows.append({"weather": label, **_metrics(g), "inference_support":
                     len(g) >= 100 and g.fecha.nunique() >= 10 and g.date_hour.nunique() >= 30})
    t = pd.DataFrame(rows)
    precip = _num(d, "precip_mm")
    wet, dry = d[precip.gt(0)], d[precip.eq(0)]
    eligible = min(wet.fecha.nunique(), dry.fecha.nunique()) >= 10 and min(wet.date_hour.nunique(), dry.date_hour.nunique()) >= 30
    return t, {"support": t.to_dict("records"), "wet_orders": len(wet), "wet_hours": wet.date_hour.nunique(),
               "wet_dates": wet.fecha.nunique(), "missing_orders": int(precip.isna().sum()),
               "inference_eligible": eligible,
               "limitation": "Weather observations are shared by many orders. Count independent dates and hours; one rainfall episode cannot establish a general weather effect."}


def _tails(d: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    cutoff = d._service.quantile(.95)
    d = d.copy()
    d["_tail"] = d._service.gt(cutoff).where(d._service.notna())
    rows = []
    for dim in ("lluvia", "pressure_band", "vertical", "_distance_band", "demand_band"):
        for label, g in d.groupby(dim, observed=True):
            t = g[g._tail.eq(True)]
            row = {"family": dim, "segment": str(label), "service_orders": g._service.count(),
                   "tail_orders": len(t), "tail_rate": _divide(len(t), g._service.count()),
                   "tail_cutoff_min": cutoff, "tail_dates": t.fecha.nunique(),
                   "tail_mean_min": t._service.mean(), "tail_recorded_cost": _total(t.cpo_total)}
            for col in STAGES:
                row[col] = t.loc[t._process_ok, col].mean()
            rows.append(row)
    tail = d[d._tail.eq(True)]
    pre4 = d[d.pre_undispatches.ge(4)]
    return pd.DataFrame(rows), {"p95_cutoff_min": cutoff, "tail_orders": len(tail),
        "tail_share": _divide(len(tail), d._service.count()), "tail_mean_min": tail._service.mean(),
        "tail_share_service_minutes": _divide(_total(tail._service), _total(d._service)),
        "pre4_orders": len(pre4), "pre4_order_share": _divide(len(pre4), d.pre_undispatches.count()),
        "pre4_event_share": _divide(_total(pre4.pre_undispatches), _total(d.pre_undispatches)),
        "pre4_mean_min": pre4._service.mean(), "pre4_recorded_cost_mean": pre4.cpo_total.mean(),
        "pre4_late5_rate": pre4._late5.mean()}


def _hour_outcomes(d: pd.DataFrame, h: pd.DataFrame) -> pd.DataFrame:
    # Recompute numerators from eligible orders; do not average hourly rates.
    a = d.groupby("date_hour").agg(orders=("id_pedido", "size"), service_count=("_service", "count"),
         service_sum=("_service", "sum"), late_count=("_late5", "sum"), late_n=("_late5", "count"),
         pre_count=("pre_any", "sum"), pre_n=("pre_any", "count"), post_count=("post_any", "sum"),
         post_n=("post_any", "count"), cost_sum=("cpo_total", "sum"), cost_n=("cpo_total", "count"))
    base = h.drop(columns=[c for c in a.columns if c in h], errors="ignore").merge(a, on="date_hour", how="outer", validate="one_to_one")
    base[list(a.columns)] = base[list(a.columns)].fillna(0)
    base["fecha"] = base.date_hour.dt.normalize()
    base["utr_proxy"] = base.orders / _num(base, "rider_hours_total").where(_num(base, "rider_hours_total").gt(0))
    return base


def _capacity(d: pd.DataFrame, h: pd.DataFrame, seed: int, samples: int) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    a = _hour_outcomes(d, h)
    valid = a[a.utr_proxy.notna() & np.isfinite(a.utr_proxy) & a.orders.gt(0)].copy()
    bins = []
    if len(valid):
        # duplicates='drop' makes tied or constant capacity series safe.
        cuts, exact_edges = pd.qcut(valid.utr_proxy, 4, labels=False, retbins=True, duplicates="drop")
        for code, g in valid.groupby(cuts, observed=True):
            code = int(code)
            bins.append({"bin": f"Q{code+1}", "lower": exact_edges[code], "upper": exact_edges[code+1],
                         "lower_inclusive": code == 0,
                         "orders": int(g.orders.sum()), "hours": len(g), "dates": g.fecha.nunique(),
                         "mean_hourly_proxy": g.utr_proxy.mean(), "pooled_proxy": _divide(g.orders.sum(), g.rider_hours_total.sum()),
                         "late5_rate": _divide(g.late_count.sum(), g.late_n.sum()),
                         "pre_rate": _divide(g.pre_count.sum(), g.pre_n.sum()),
                         "post_rate": _divide(g.post_count.sum(), g.post_n.sum()),
                         "mean_min": _divide(g.service_sum.sum(), g.service_count.sum()),
                         "recorded_cost_mean": _divide(g.cost_sum.sum(), g.cost_n.sum())})
    dates = sorted(a.loc[~a.partial_boundary_day.fillna(True).astype(bool), "fecha"].unique())
    threshold_rows, holdout_rows, discovery_bins = [], [], []
    if len(dates) >= 20:
        holdout_dates = dates[-10:]
        discovery_dates = dates[:-10]
        train_h = valid[valid.fecha.isin(discovery_dates)]
        cut = train_h.utr_proxy.quantile(.75)
        if pd.notna(cut) and train_h.utr_proxy.nunique() > 1:
            labels, edges = pd.qcut(train_h.utr_proxy, 4, labels=False, retbins=True, duplicates="drop")
            for code, g in train_h.groupby(labels, observed=True):
                code = int(code)
                discovery_bins.append({"bin": f"Q{code+1}", "lower": edges[code], "upper": edges[code+1],
                    "orders": int(g.orders.sum()), "hours": len(g), "dates": g.fecha.nunique(),
                    "late5_rate": _divide(g.late_count.sum(), g.late_n.sum()),
                    "pre_rate": _divide(g.pre_count.sum(), g.pre_n.sum()),
                    "support": g.orders.sum() >= 100 and len(g) >= 30 and g.fecha.nunique() >= 10})
            train = d[d.fecha.isin(discovery_dates)].copy()
            test = d[d.fecha.isin(holdout_dates)].copy()
            proxy = a.set_index("date_hour").utr_proxy
            for name, frame in [("discovery", train), ("holdout", test)]:
                p = frame.date_hour.map(proxy)
                exp = p.gt(cut).astype("boolean").mask(p.isna())
                for metric in ("_late5", "pre_any"):
                    row = date_bootstrap_contrast(frame, metric, exp, name=f"{name}: proxy > discovery P75", seed=seed, samples=samples)
                    row.update(split=name, cutoff=cut)
                    holdout_rows.append(row)
            for metric in ("_late5", "pre_any"):
                r = [x for x in holdout_rows if x["metric"] == metric]
                rate = "late5_rate" if metric == "_late5" else "pre_rate"
                upper = discovery_bins[-3:]
                adjacent = len(upper) == 3 and all(x["support"] for x in upper) and all(
                    pd.notna(upper[i][rate]) and upper[i+1][rate] > upper[i][rate] for i in range(2))
                validated = adjacent and len(r) == 2 and all(x["inference_eligible"] and pd.notna(x["ci_low"]) and x["ci_low"] > 0 for x in r)
                threshold_rows.append({"metric": metric, "candidate_cutoff": cut,
                    "status": "Replicated association; not a calibrated staffing trigger" if validated else "No validated operational threshold",
                    "validated_association": validated, "discovery_dates": len(discovery_dates), "holdout_dates": len(holdout_dates),
                    "consistent_adjacent_discovery_bins": adjacent,
                    "rule": "Three supported upper discovery quartiles must deteriorate monotonically; one discovery P75 candidate, held-out final 10 complete dates; each comparison side >=100 orders, 30 hours and 10 dates; positive date-bootstrap intervals in both splits."})
    if not threshold_rows:
        threshold_rows = [{"metric": metric, "candidate_cutoff": np.nan, "status": "No validated operational threshold",
                           "validated_association": False, "discovery_dates": max(len(dates)-10, 0), "holdout_dates": min(len(dates), 10),
                           "rule": "Insufficient complete dates or variation for discovery and independent confirmation."} for metric in ("_late5", "pre_any")]
    supply = _num(a, "rider_hours_total")
    summary = {"observed_rider_hours": _total(supply),
               "orders_per_observed_rider_hour": _divide(a.loc[supply.gt(0), "orders"].sum(), _total(supply)),
               "orders_with_observed_supply": int(a.loc[supply.gt(0), "orders"].sum()),
               "full_calendar_hours": len(a), "demand_hours": int(a.orders.gt(0).sum()),
               "hours_with_observed_supply": int(supply.notna().sum()),
               "supply_hours_without_orders": int((supply.gt(0) & a.orders.eq(0)).sum()),
               "demand_hours_missing_supply": int((supply.isna() & a.orders.gt(0)).sum()),
               "orders_missing_supply": int(a.loc[supply.isna(), "orders"].sum()),
               "bins": bins, "thresholds": threshold_rows, "discovery_bins": discovery_bins,
               "limitation": "Orders per observed rider-hour is an incomplete-coverage pressure proxy, not measured utilization or a proven capacity limit."}
    return pd.DataFrame(bins), pd.DataFrame(threshold_rows), pd.DataFrame(holdout_rows), summary


def _models(d: pd.DataFrame, h: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    coefficients, diagnostics = [], []
    try:
        import statsmodels.api as sm
    except ImportError:
        diagnostic = {"model": "all", "status": "unavailable", "reason": "statsmodels is not installed; no model estimates were fabricated."}
        return pd.DataFrame(), pd.DataFrame([diagnostic]), {"status": "unavailable", "diagnostics": [diagnostic]}
    work = d.copy()
    top = work.vertical.value_counts().head(5).index
    work["vertical_group"] = work.vertical.where(work.vertical.isin(top), "Other")
    hourly = _hour_outcomes(d, h).set_index("date_hour")
    work["hour_orders"] = work.date_hour.map(hourly.orders)
    work["observed_supply"] = work.date_hour.map(hourly.rider_hours_total)
    exposure = hourly[hourly.orders.gt(0) & hourly.rider_hours_total.gt(0)].copy()
    exposure["demand_high"] = exposure.orders.gt(exposure.orders.median())
    exposure["supply_high"] = exposure.rider_hours_total.gt(exposure.rider_hours_total.median())
    cell_support = exposure.groupby(["demand_high", "supply_high"]).agg(
        hours=("orders", "size"), dates=("fecha", "nunique"), orders=("orders", "sum"))
    interaction_supported = len(cell_support) == 4 and bool(
        (cell_support.hours.ge(30) & cell_support.dates.ge(10) & cell_support.orders.ge(100)).all())
    # Fixed grouping makes two-count binomial observations; no frequency weights
    # masquerading as independent weather/supply observations are used.
    keys = ["date_hour", "vertical_group", "_distance_band"]
    for outcome in ("pre_any", "post_any", "_late5"):
        w = work[work[outcome].notna() & work.hour_orders.gt(0) & work.observed_supply.gt(0) & work._distance_band.ne("Unknown")].copy()
        g = w.groupby(keys, observed=True).agg(events=(outcome, "sum"), n=(outcome, "size"),
                     hour_orders=("hour_orders", "first"), observed_supply=("observed_supply", "first")).reset_index()
        g["date"] = g.date_hour.dt.normalize()
        g["hour"] = g.date_hour.dt.hour.astype(str)
        g["weekday"] = g.date_hour.dt.dayofweek.astype(str)
        info = {"model": outcome, "orders": len(w), "groups": len(g), "dates": g.date.nunique(),
                "events": g.events.sum(), "non_events": (g.n-g.events).sum(),
                "status": "ineligible", "reason": "Requires >=10 dates, >=100 events and >=100 non-events.",
                "interpretation": "Adjusted association; whole-date clustered covariance; coarsened order-mix controls.",
                "demand_supply_interaction_eligible": interaction_supported,
                "weather_included": False,
                "weather_exclusion": "Sparse independent weather exposure; no weather-versus-staffing importance ranking is identified."}
        if min(info["events"], info["non_events"]) < 100 or info["dates"] < 10:
            diagnostics.append(info)
            continue
        X = pd.get_dummies(g[["hour", "weekday", "vertical_group", "_distance_band"]], drop_first=True, dtype=float)
        references = {field: sorted(g[field].astype(str).unique())[0]
                      for field in ("hour", "weekday", "vertical_group", "_distance_band")}
        info["reference_categories"] = json.dumps(references, sort_keys=True)
        X["log_hour_orders"] = np.log(g.hour_orders)
        X["log_observed_rider_hours"] = np.log(g.observed_supply)
        if interaction_supported:
            # Centering makes main effects refer to the other log variable's
            # pooled-cell mean, rather than an implausible one-unit baseline.
            X["log_hour_orders"] -= X.log_hour_orders.mean()
            X["log_observed_rider_hours"] -= X.log_observed_rider_hours.mean()
            X["demand_supply_interaction"] = X.log_hour_orders * X.log_observed_rider_hours
        constant = X.columns[X.nunique() < 2].tolist()
        X = X.drop(columns=constant)
        X = sm.add_constant(X, has_constant="add").astype(float)
        rank = np.linalg.matrix_rank(X.to_numpy())
        info.update(design_columns=X.shape[1], design_rank=rank)
        if rank < X.shape[1]:
            info.update(status="not_estimable", reason="Rank-deficient design; no unstable coefficients reported.")
            diagnostics.append(info)
            continue
        try:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                result = sm.GLM(np.column_stack([g.events, g.n-g.events]), X, family=sm.families.Binomial()).fit(
                    maxiter=100, cov_type="cluster", cov_kwds={"groups": g.date})
            finite = np.isfinite(result.params).all() and np.isfinite(result.bse).all()
            good = bool(result.converged and finite)
            info.update(status="estimated" if good else "failed_diagnostics", converged=bool(result.converged),
                        reason="" if good else "Nonconvergence or nonfinite covariance.",
                        warning=" | ".join(sorted({str(x.message) for x in caught})))
            if good:
                ci = result.conf_int()
                for term in X.columns:
                    if term == "const":
                        continue
                    factor = np.log(2) if term.startswith("log_") else 1.0
                    b, se = result.params[term], result.bse[term]
                    reference = next((base for field, base in references.items() if term.startswith(field+"_")), "Not a category contrast")
                    coefficients.append({"model": outcome, "term": term, "coefficient": b, "std_error": se,
                        "odds_ratio": np.exp(np.clip(b*factor, -700, 700)),
                        "ci_low": np.exp(np.clip(ci.loc[term, 0]*factor, -700, 700)),
                        "ci_high": np.exp(np.clip(ci.loc[term, 1]*factor, -700, 700)), "p_value": result.pvalues[term],
                        "reference_category": reference,
                        "contrast": ("Centered log-demand x log-supply product" if term == "demand_supply_interaction" else
                                     "Per doubling at the other exposure's mean log level" if factor != 1 and interaction_supported else
                                     "Per doubling" if factor != 1 else "Category versus omitted reference"),
                        "inference": "Exploratory; date-clustered; not causal"})
        except (ValueError, np.linalg.LinAlgError, RuntimeError, OverflowError) as exc:
            info.update(status="failed", reason=f"{type(exc).__name__}: {exc}")
        diagnostics.append(info)
    status = "estimated" if coefficients else "no_estimable_models"
    return pd.DataFrame(coefficients), pd.DataFrame(diagnostics), {"status": status, "diagnostics": diagnostics,
        "limitation": "Models describe conditional associations. Supply may respond to demand; final-rider attributes and observed waiting time are excluded. Weather effects are not inferred from sparse episodes. No predictive-performance claim is made."}


def _actor_exposure(d: pd.DataFrame, entity: str) -> pd.DataFrame:
    if entity not in d:
        return pd.DataFrame()
    grouped = d.groupby(entity, observed=True)
    table = grouped.agg(orders=("id_pedido", "size"), hours=("date_hour", "nunique"), dates=("fecha", "nunique"),
        service_orders=("_service", "count"), mean_min=("_service", "mean"),
        late_eligible_orders=("_late5", "count"), late5_orders=("_late5", "sum"), late5_rate=("_late5", "mean"),
        pre_eligible_orders=("pre_any", "count"), pre_rate=("pre_any", "mean"),
        post_eligible_orders=("post_any", "count"), post_rate=("post_any", "mean"),
        recorded_cost_mean=("cpo_total", "mean"))
    table["recorded_cost_total"] = grouped.cpo_total.sum(min_count=1)
    table["descriptive_support"] = table.orders.ge(100) & table.dates.ge(5)
    table["interpretation"] = ("Final-assignee order exposure, not responsibility for earlier events" if entity == "id_repartidor"
                               else "Descriptive merchant cohort; order mix is not risk-adjusted")
    return table.reset_index(names="entity_id").sort_values("orders", ascending=False)


def _hypotheses(d, h, contrasts, capacity, weather, process, coefficients) -> list[dict]:
    evidence = lambda name: _contrast_evidence(contrasts, name)
    h1 = evidence("High demand: low versus high observed supply, pre incidence")
    h1_late = evidence("High demand: low versus high observed supply, late >5min")
    relative_pre = evidence("Within-clock high demand: low versus high supply, pre incidence")
    relative_late = evidence("Within-clock high demand: low versus high supply, late >5min")
    relative_tail = evidence("Within-clock high demand: low versus high supply, P95-tail incidence")
    h2_time = evidence("Observed wet versus dry hours: service")
    h2_cost = evidence("Observed wet versus dry hours: recorded cost")
    peak = evidence("Peak hours: observed wet versus dry service")
    nonpeak = evidence("Non-peak hours: observed wet versus dry service")
    peak_tail = evidence("Peak hours: observed wet versus dry P95-tail incidence")
    lowcost = evidence("Low demand: high versus low observed supply, recorded cost")
    lowlate = evidence("Low demand: high versus low observed supply, late >5min")
    hourly = _hour_outcomes(d, h)
    low_profiles = []
    for family, demand_col, supply_col in [("global", "demand_band", "supply_band"),
                                          ("within_clock", "relative_demand_band", "relative_supply_band")]:
        if {demand_col, supply_col}.issubset(hourly.columns):
            for supply_label in ("Low", "High"):
                x = hourly[hourly[demand_col].eq("Low") & hourly[supply_col].eq(supply_label)]
                low_profiles.append({"segmentation": family, "supply_band": supply_label, "hours": len(x), "dates": x.fecha.nunique(),
                                     "orders": x.orders.sum(), "observed_rider_hours": _total(x.rider_hours_total),
                                     "orders_per_observed_rider_hour": _divide(x.orders.sum(), _total(x.rider_hours_total))})
    staffing = [] if coefficients.empty else coefficients[coefficients.term.isin(
        ["log_hour_orders", "log_observed_rider_hours", "demand_supply_interaction"])][
            ["model", "term", "coefficient", "odds_ratio", "ci_low", "ci_high"]].to_dict("records")
    return [
        {"id": "H1", "hypothesis": "Demand/capacity mismatch is associated with pre-undispatch",
         "supporting_evidence": _evidence_text({"global_high_demand_pre": h1, "global_high_demand_late5": h1_late,
                                                "within_clock_pre": relative_pre, "within_clock_late5": relative_late, "within_clock_tail95": relative_tail}),
         "contradicting_or_limiting_evidence": "Global demand/supply bands may have no opposite-cell overlap. Within-clock bands restore some comparisons but use full-sample descriptive tertiles; supply is incomplete and scheduling may respond to demand.",
         "conclusion": "A within-clock conditional comparison is available; no causal mismatch effect is identified." if relative_pre.get("inference_eligible") else "Independent support for the within-clock high-demand comparison is insufficient; a mismatch mechanism is unproven.",
         "strength": "Association" if relative_pre.get("inference_eligible") else "Insufficient support", "source_table": "headline_contrasts"},
        {"id": "H2", "hypothesis": "Weather relates to recorded cost through longer service time",
         "supporting_evidence": _evidence_text({"service_difference": h2_time, "recorded_cost_difference": h2_cost}),
         "contradicting_or_limiting_evidence": f"Only {weather['wet_dates']} wet dates and {weather['wet_hours']} wet hours. Final recorded cost and service time do not identify a mediation mechanism; monetary units are unverified.",
         "conclusion": "Wet/dry differences are descriptive. Neither a general weather effect nor cost mediation is established.",
         "strength": "Limited independent weather exposure" if not weather["inference_eligible"] else "Association only", "source_table": "weather_support"},
        {"id": "H3", "hypothesis": "Low throughput reflects excess observed capacity during low demand",
         "supporting_evidence": _evidence_text({"low_demand_profiles": low_profiles, "global_cost": lowcost, "global_late5": lowlate,
                                                "within_clock_cost": evidence("Within-clock low demand: high versus low supply, recorded cost"),
                                                "within_clock_late5": evidence("Within-clock low demand: high versus low supply, late >5min"),
                                                "supply_hours_without_orders": capacity["supply_hours_without_orders"]}),
         "contradicting_or_limiting_evidence": "A low orders/hour ratio follows mechanically from low demand or more recorded hours. Standby requirements, true busy time and staffing overhead costs are unavailable.",
         "conclusion": "Identify low-throughput periods for schedule review; actual overstaffing, utilization and avoidable cost remain unmeasured.",
         "strength": "Descriptive capacity proxy", "source_table": "capacity_bins"},
        {"id": "H4", "hypothesis": "Weather combined with peak demand worsens service and its upper tail",
         "supporting_evidence": _evidence_text({"peak_service": peak, "nonpeak_service": nonpeak, "peak_p95_tail": peak_tail}),
         "contradicting_or_limiting_evidence": "The same weather dates supply many correlated orders. Separate peak/nonpeak differences do not prove an interaction; independent support is required in every comparison.",
         "conclusion": "Combined conditions are described; no reproducible weather-by-peak effect is established in sparse exposure.",
         "strength": "Insufficient interaction support" if not (peak.get("inference_eligible") and nonpeak.get("inference_eligible")) else "Exploratory contrasts", "source_table": "headline_contrasts"},
        {"id": "H5", "hypothesis": "Staffing explains more performance variation than weather",
         "supporting_evidence": _evidence_text({"staffing_associations": staffing, "wet_dates": weather["wet_dates"],
                                                "wet_hours": weather["wet_hours"], "weather_inference_eligible": weather["inference_eligible"]}),
         "contradicting_or_limiting_evidence": "Coefficient magnitudes on different scales are not explanatory importance. Sparse weather exposure prevents a fair head-to-head model comparison; no prediction experiment is claimed.",
         "conclusion": "Staffing associations can be examined where estimable; relative staffing-versus-weather importance is not identified.",
         "strength": "Relative-importance claim unsupported", "source_table": "model_coefficients"},
        {"id": "H6", "hypothesis": "Long dropoff distance is associated with pre-event incidence",
         "supporting_evidence": _evidence_text(evidence("Dropoff distance >3km versus <=1km: pre incidence")),
         "contradicting_or_limiting_evidence": "Offer-level payment and rejected-assignment history are unavailable. Recorded cost per kilometre cannot establish an incentive mechanism.",
         "conclusion": "Evaluate the measured distance association; pricing mechanism remains untested.",
         "strength": "Association only", "source_table": "headline_contrasts"},
        {"id": "H7", "hypothesis": "Final-rider pickup waiting is the dominant measured stage",
         "supporting_evidence": _evidence_text({"stages": process["stages"], "late_gaps": process["late_contributions"]}),
         "contradicting_or_limiting_evidence": "The earlier incomplete decomposition omitted the initial interval. Components describe the final recorded timeline, not the causes of each interval.",
         "conclusion": f"Largest measured stage: {process['main_stage']}.", "strength": "Direct descriptive decomposition", "source_table": "stage_summary"},
        {"id": "H8", "hypothesis": "Repeated pre events mark an operational exception cohort",
         "supporting_evidence": _evidence_text({"service": evidence("At least four pre events versus fewer"),
                                                "cost": evidence("At least four pre events versus fewer: recorded cost")}),
         "contradicting_or_limiting_evidence": "An observational final-counter cohort does not establish preventability or an optimal intervention trigger.",
         "conclusion": "Use the observed cohort for diagnosis and a monitored pilot; do not book estimated savings.",
         "strength": "Descriptive concentration", "source_table": "headline_contrasts"},
    ]


def _priorities(d: pd.DataFrame, h: pd.DataFrame) -> list[dict]:
    """Transparent burden ordering; overlapping cohorts must never be summed."""
    first_cut = d.loc[d._process_ok, "t_created_to_notify_min"].quantile(.9)
    wait_cut = d.loc[d._process_ok, "t_wait_at_pu_min"].quantile(.9)
    supply = d.date_hour.map(h.set_index("date_hour").rider_hours_total)
    definitions = [
        ("Long initial interval", d._process_ok & d.t_created_to_notify_min.gt(first_cut),
         f"Creation-to-final-notification > observed P90 ({first_cut:.3f} min); descriptive case-review cutoff",
         "Instrument first dispatch and reassignment; review high-delay orders before testing an escalation workflow.",
         "Moderate: operational escalation can be tested; missing assignment history limits diagnosis.",
         "P90 creation-to-final-notification, late >5min, completion, recorded cost per reviewed order",
         "Premature escalation and manual review add effort; validate a small pilot.", "stage_summary"),
        ("Repeated pre events", d.pre_undispatches.ge(4), "At least four recorded pre events; a review cohort, not a calibrated optimum",
         "Pilot exception review and capture why repeated assignments fail.",
         "Moderate: dispatch policy is testable; rider offer decisions are unobserved.",
         "Time to final notification, pre-event count, completion, late >5min, recorded cost",
         "Intervention can increase incentives or manual work; measure the trade-off.", "headline_contrasts"),
        ("Pickup waiting tail", d._process_ok & d.t_wait_at_pu_min.gt(wait_cut),
         f"Final-rider pickup waiting > observed P90 ({wait_cut:.3f} min)",
         "Review merchant readiness and rider arrival coordination in supported merchant cohorts.",
         "Shared: merchant readiness and arrival coordination require joint action.",
         "Pickup wait P90, service P90, late >5min, completion",
         "Later rider arrival can reduce waiting but delay delivery if readiness is misestimated.", "stage_by_segment"),
        ("High within-clock demand with low observed supply", d.relative_demand_band.eq("High") & d.relative_supply_band.eq("Low"),
         "Within-clock high-demand / low-observed-supply tertile cell; descriptive combination",
         "Audit supply coverage and order mix before piloting a schedule adjustment in repeated problem windows.",
         "Conditional: schedules can change, but actual capacity and coverage must be verified first.",
         "Supply coverage, pressure proxy, service P95, late >5min, completion",
         "More scheduled hours can reduce throughput per observed hour; no savings are assumed.", "operational_segments"),
        ("Missing hourly supply observations", supply.isna(), "An order falls in an hour without observed supply",
         "Repair missing shift observations and monitor join coverage before interpreting capacity metrics.",
         "High for data capture; missing observation does not mean no riders.",
         "Observed-supply coverage of order hours and orders",
         "Capture quality is an enabling investment with unquantified financial benefit.", "capacity_bins"),
    ]
    rows = []
    for issue, mask, trigger, action, controllability, monitor, tradeoff, source in definitions:
        mask = mask.fillna(False)
        g, reference = d[mask], d[~mask]
        if g.empty:
            continue
        supported = len(g) >= 100 and g.fecha.nunique() >= 5
        rows.append({"issue": issue, "trigger": trigger, "action": action, "controllability": controllability,
                     "monitoring_kpi": monitor, "trade_off": tradeoff, "source_table": source,
                     "affected_orders": len(g), "affected_share": _divide(len(g), len(d)),
                     "affected_hours": g.date_hour.nunique(), "affected_dates": g.fecha.nunique(),
                     "affected_late5_orders": _total(g._late5), "affected_late5_eligible_orders": g._late5.count(),
                     "late5_rate": g._late5.mean(), "service_mean_min": g._service.mean(),
                     "reference_mean_min": reference._service.mean(),
                     "observed_mean_difference_min": g._service.mean()-reference._service.mean(),
                     "affected_recorded_cost": _total(g.cpo_total), "descriptive_support": supported,
                     "confidence": "Supported descriptive cohort; intervention effect untested" if supported else "Sparse case-review cohort",
                     "ordering_rule": "Supported cohorts first, then observed late>5min order burden descending, then order frequency. Controllability is qualitative; cohorts overlap and burdens must not be summed."})
    rows.sort(key=lambda r: (r["descriptive_support"], r["affected_late5_orders"] if pd.notna(r["affected_late5_orders"]) else -1, r["affected_orders"]), reverse=True)
    for rank, row in enumerate(rows, 1):
        row["priority"] = rank
    return rows


def analyze(orders: pd.DataFrame, hours: pd.DataFrame, output_dir: Path,
            seed: int = 42, bootstrap_samples: int = 500) -> dict:
    """Compute business evidence, write numeric CSVs and return strict JSON data."""
    if bootstrap_samples < 1:
        raise ValueError("bootstrap_samples must be positive.")
    d, h = _prepare(orders, hours)
    destination = Path(output_dir) / "analysis"
    destination.mkdir(parents=True, exist_ok=True)
    tables = {}

    def save(name: str, frame: pd.DataFrame) -> None:
        if frame.empty and len(frame.columns) == 0:
            frame = pd.DataFrame(columns=["status"])
        frame.to_csv(destination / f"{name}.csv", index=False)
        tables[name] = f"analysis/{name}.csv"

    kpis = _metrics(d)
    kpis.update(completed_orders=int(_num(d, "completed_flag").eq(1).sum()),
                cancelled_orders=int(_num(d, "cancelled_flag").eq(1).sum()),
                service_coverage=_divide(d._service.count(), len(d)),
                late_coverage=_divide(d._late.count(), len(d)))
    save("kpis", pd.DataFrame([kpis]))
    stages, late_stages, stage_segments, process = _stages(d)
    save("stage_summary", stages)
    save("stage_late_contrasts", late_stages)
    save("stage_by_segment", stage_segments)
    segments = _segments(d)
    save("operational_segments", segments)
    tails, tail_summary = _tails(d)
    save("tail_segments", tails)
    weather_t, weather = _weather(d)
    save("weather_support", weather_t)
    contrasts = _contrasts(d, seed, bootstrap_samples)
    save("headline_contrasts", contrasts)
    cap_bins, thresholds, holdout, capacity = _capacity(d, h, seed+100, bootstrap_samples)
    save("capacity_bins", cap_bins)
    save("threshold_assessment", thresholds)
    save("temporal_holdout", holdout)
    save("threshold_discovery_bins", pd.DataFrame(capacity["discovery_bins"]))
    coef, diagnostics, models = _models(d, h)
    save("model_coefficients", coef)
    save("model_diagnostics", diagnostics)
    save("merchant_screening", _actor_exposure(d, "id_comercio"))
    save("rider_exposure", _actor_exposure(d, "id_repartidor"))
    costs = {"recorded_total_cost": _total(d.cpo_total), "recorded_aborted_leg_cost": _total(d.cpo_undispatch),
             "aborted_leg_share": _divide(_total(d.cpo_undispatch), _total(d.cpo_total)),
             "cost_known_orders": d.cpo_total.count(), "orders_with_aborted_leg_cost": int(d.cpo_undispatch.gt(0).sum()),
             "unit": "Source monetary unit unverified", "interpretation": "Recorded cost accounting, not avoidable cost or guaranteed savings"}
    save("recorded_cost", pd.DataFrame([costs]))
    findings = []
    if process["eligible_orders"]:
        best = stages.loc[stages.mean_min.idxmax()]
        late_best = late_stages.loc[late_stages.difference_min.idxmax()] if late_stages.difference_min.notna().any() else None
        findings.append({"id": "process", "title": "Locate elapsed time before choosing an operational lever",
            "observation": f"The largest measured stage is {best.label.lower()}.",
            "evidence": {"stage_mean_min": best.mean_min, "stage_share": best.share_total_time,
                         "process_orders": process["eligible_orders"], "process_coverage": process["coverage"],
                         "largest_late_gap_stage": None if late_best is None else late_best.label,
                         "largest_late_gap_share": None if late_best is None else late_best.share_of_total_difference},
            "interpretation": "A complete additive timeline changes the diagnosis; stage differences are descriptive, not causal.",
            "action": "Instrument the interval from creation to final notification, then distinguish scheduling, first assignment and subsequent reassignment before selecting a dispatch intervention.",
            "confidence": "Strong descriptive evidence", "limitation": process["limitation"], "source_table": "stage_summary"})
    if tail_summary["pre4_orders"]:
        findings.append({"id": "repeat_pre", "title": "Repeated pre events identify an observable exception cohort",
            "observation": "Orders with at least four recorded pre events concentrate a measurable share of all recorded pre events.",
            "evidence": tail_summary,
            "interpretation": "This cohort is suitable for case review and escalation design; four events is an observable grouping, not an optimized trigger.",
            "action": "Pilot exception review after repeated pre events; monitor time to final notification, completion, late >5min and recorded cost per reviewed order.",
            "confidence": "Strong descriptive evidence" if tail_summary["pre4_orders"] >= 100 else "Limited descriptive support",
            "limitation": "Final-state counters reveal concentration but not the sequence, offer compensation or rejecting rider.", "source_table": "tail_segments"})
    findings.append({"id": "capacity", "title": "Observed staffing pressure requires coverage-aware interpretation",
        "observation": "Capacity comparisons use orders divided by observed rider-hours, with missing-supply hours retained in coverage reporting.",
        "evidence": {k: v for k, v in capacity.items() if k not in ("bins", "thresholds", "limitation")},
        "interpretation": "A staffing ratio does not measure busy time or prove undercapacity. Any threshold must reproduce on held-out dates.",
        "action": "Monitor hour-specific demand, observed supply, coverage and service tails together; validate a scheduling change prospectively.",
        "confidence": "Descriptive proxy", "limitation": capacity["limitation"], "source_table": "capacity_bins"})
    relative = contrasts[contrasts.contrast.eq("Within-clock high demand: low versus high supply, service")]
    if len(relative):
        row = relative.iloc[0]
        if row.inference_eligible and pd.notna(row.ci_low) and (row.ci_low > 0 or row.ci_high < 0):
            findings.append({"id": "within_clock_capacity", "title": "Within-clock comparisons separate daily timing from observed supply variation",
                "observation": "Among orders in high-demand hours relative to the same clock hour, service differs between low and high observed-supply cohorts.",
                "evidence": _contrast_evidence(contrasts, row.contrast),
                "interpretation": "This is an association between observed combinations, after removing the global hour-of-day scale through within-clock bands; order mix and reactive scheduling can still differ.",
                "action": "Review the identified combinations across repeated dates and inspect process-stage differences before selecting a scheduling pilot.",
                "confidence": "Date-bootstrap descriptive association", "limitation": "Full-sample descriptive bands and incomplete supply coverage do not identify a causal staffing effect or a deployable threshold.",
                "source_table": "headline_contrasts"})
    hypotheses = _hypotheses(d, h, contrasts, capacity, weather, process, coef)
    priorities = _priorities(d, h)
    save("hypotheses", pd.DataFrame(hypotheses))
    save("priorities", pd.DataFrame(priorities))
    result = {"schema_version": "1.0", "status": "complete", "support_rules": SUPPORT,
        "cohorts": {"orders": len(d), "dates": d.fecha.nunique(), "first_date": d.fecha.min(), "last_date": d.fecha.max(),
                    "service_orders": d._service.count(), "late_eligible_orders": d._late.count(), "process_orders": int(d._process_ok.sum())},
        "kpis": kpis, "process": process, "weather": weather, "capacity": capacity, "tails": tail_summary,
        "contrasts": contrasts.to_dict("records"), "models": models, "costs": costs,
        "findings": findings, "hypotheses": hypotheses, "priorities": priorities, "tables": tables,
        "limitations": ["Observational data support associations, not causal effects or guaranteed savings.",
             "Final order rows do not reconstruct rejected assignments or identify responsible rejecting riders.",
             "Recorded monetary and order-value units are unverified in source documentation.",
             "Observed shift hours are a coverage-dependent proxy, not utilization; order delay is not rider labor time.",
             "Date bootstrap accounts for within-date dependence but not serial dependence between dates; this short window limits generalization.",
             "Exploratory segment and model comparisons are not a multiple-testing-controlled search; decisions need replication."]}
    clean = _json(result)
    # An explicit round-trip prevents nonstandard NaN/Infinity from leaking into reports.
    json.dumps(clean, allow_nan=False)
    return clean
