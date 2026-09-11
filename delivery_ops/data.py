"""Canonical source-to-order and source-to-hour reconstruction.

No work is performed at import. Raw records are never overwritten. All joins
declare their grain and all missing observations remain distinguishable from 0.
"""
from pathlib import Path
import numpy as np
import pandas as pd

from .config import Config, SOURCES, STAGES, SCHEMA_VERSION
from .io import sha256, write_json

TIMESTAMPS = ["fecha_creacion", "sent_to_vendor_at", "vendor_accepted_at", "rider_notified_at",
              "rider_accepted_at", "rider_at_pu", "rider_picked_up", "rider_at_do", "rider_droped_off"]
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def parse_datetime(values):
    """Parse mixed fractional/nonfractional seconds without format inference loss."""
    return pd.to_datetime(values, format="mixed", errors="coerce")


def band(values, cuts=(1/3, 2/3)):
    """Quantile bands with ties kept together and explicit missing values."""
    x = pd.to_numeric(values, errors="coerce").astype("float64")
    good = x[np.isfinite(x)]
    if good.empty:
        return pd.Series("Unknown", index=values.index), []
    q = good.quantile(list(cuts)).tolist()
    out = pd.Series(np.select([x.le(q[0]), x.le(q[1])], ["Low", "Medium"], default="High"), index=x.index)
    return out.where(x.notna() & np.isfinite(x), "Unknown"), q


def _calendar(frame):
    frame["fecha"] = frame.date_hour.dt.normalize()
    frame["hora_num"] = frame.date_hour.dt.hour
    frame["dia_semana"] = frame.date_hour.dt.dayofweek.map(dict(enumerate(WEEKDAYS)))
    return frame


def reconstruct_orders(raw):
    required = set(TIMESTAMPS + ["id_pedido", "id_comercio", "id_repartidor", "cpo", "undispatch_reason",
                               "order_status", "tiempo_real", "tiempo_estimado", "pre_accept_undispatchs", "post_accept_undispatchs"])
    missing = required - set(raw.columns)
    if missing:
        raise ValueError(f"Missing order columns: {sorted(missing)}")
    if raw.id_pedido.isna().any():
        raise ValueError("Order IDs must be present; unresolved rows cannot be silently dropped.")
    df = raw.copy()
    for col in ["id_pedido", "id_comercio", "id_repartidor"]:
        df[col] = df[col].astype("string")
    df["source_row_id"] = np.arange(2, len(df) + 2)
    df["cost_record_type"] = np.where(df.undispatch_reason.isna(), "Principal", "Reason-bearing")
    main = df[df.cost_record_type.eq("Principal")].copy()
    sizes = main.groupby("id_pedido").size().reindex(df.id_pedido.unique(), fill_value=0)
    if not sizes.eq(1).all():
        raise ValueError(f"Expected exactly one principal row per order; {int(sizes.ne(1).sum())} ambiguous/missing orders.")
    if df.cpo.isna().any() or not np.isfinite(pd.to_numeric(df.cpo, errors="coerce")).all():
        raise ValueError("Recorded cost must be finite for exact cost reconciliation.")
    costs = df.groupby("id_pedido").agg(cpo_total=("cpo", "sum"), cost_record_count=("source_row_id", "size"))
    extra = df[df.cost_record_type.eq("Reason-bearing")].groupby("id_pedido").agg(
        cpo_undispatch=("cpo", "sum"),
        undispatch_reasons_all=("undispatch_reason", lambda x: " | ".join(sorted(set(x.dropna().astype(str)))))
    )
    main = main.rename(columns={"cpo": "cpo_entrega"}).drop(columns="undispatch_reason")
    o = main.merge(costs, on="id_pedido", validate="one_to_one").merge(extra, on="id_pedido", how="left", validate="one_to_one")
    o["cpo_undispatch"] = o.cpo_undispatch.fillna(0)
    o["undispatch_reasons_all"] = o.undispatch_reasons_all.fillna("No reason-bearing record")
    o["undispatch_reason"] = o.undispatch_reasons_all
    for col in TIMESTAMPS:
        o[col] = parse_datetime(o[col])
    if o.fecha_creacion.isna().any():
        raise ValueError("Unparseable creation timestamps prevent calendar alignment.")
    o["date_hour"] = o.fecha_creacion.dt.floor("h")
    _calendar(o)
    o["completed_flag"] = o.order_status.eq("completed").astype(int)
    o["cancelled_flag"] = o.order_status.eq("cancelled").astype(int)
    o["actual_min"] = pd.to_numeric(o.tiempo_real, errors="coerce") / 60
    o["promised_min"] = pd.to_numeric(o.tiempo_estimado, errors="coerce") / 60
    o["service_eligible"] = o.completed_flag.eq(1) & o.actual_min.ge(0) & np.isfinite(o.actual_min)
    o["late_eligible"] = o.service_eligible & o.promised_min.ge(0) & np.isfinite(o.promised_min)
    o["gap_min"] = (o.actual_min - o.promised_min).where(o.late_eligible)
    for col, cutoff in [("tardio", 0), ("tardio_5min", 5), ("muy_tardio", 15)]:
        o[col] = o.gap_min.gt(cutoff).astype(float).where(o.late_eligible)
    pairs = {
        "t_created_to_notify_min": ("rider_notified_at", "fecha_creacion"),
        "t_notify_to_accept_min": ("rider_accepted_at", "rider_notified_at"),
        "t_accept_to_pu_arrival_min": ("rider_at_pu", "rider_accepted_at"),
        "t_wait_at_pu_min": ("rider_picked_up", "rider_at_pu"),
        "t_last_mile_min": ("rider_at_do", "rider_picked_up"),
        "t_creacion_a_envio_min": ("sent_to_vendor_at", "fecha_creacion"),
        "t_vendor_response_min": ("vendor_accepted_at", "sent_to_vendor_at"),
        "t_espera_asignacion_min": ("rider_notified_at", "vendor_accepted_at"),
        "t_entrega_final_min": ("rider_droped_off", "rider_at_do"),
        "t_total_from_created_min": ("rider_droped_off", "fecha_creacion"),
    }
    for col, (end, start) in pairs.items():
        o[col] = (o[end] - o[start]).dt.total_seconds() / 60
    stage_ok = o[list(STAGES)].notna().all(axis=1) & o[list(STAGES)].ge(0).all(axis=1)
    o["process_eligible"] = o.completed_flag.eq(1) & stage_ok
    o["dispatch_paralelo"] = o.t_espera_asignacion_min.lt(0).astype(float).where(o.t_espera_asignacion_min.notna())
    o["service_timestamp_min"] = (o.rider_at_do - o.fecha_creacion).dt.total_seconds() / 60
    o["service_residual_seconds"] = (o.actual_min - o.service_timestamp_min) * 60
    for prefix, raw_col in [("pre", "pre_accept_undispatchs"), ("post", "post_accept_undispatchs")]:
        x = pd.to_numeric(o[raw_col], errors="coerce").astype("float64")
        x = x.where(x.ge(0) & x.mod(1).eq(0))
        o[f"{prefix}_undispatches"] = x
        o[f"{prefix}_any"] = x.gt(0).astype(float).where(x.notna())
    o["total_undispatches"] = o.pre_undispatches + o.post_undispatches
    o["any_undispatch"] = o.total_undispatches.gt(0).astype(float).where(o.total_undispatches.notna())
    o["segmento_undispatch"] = np.select(
        [o.pre_any.eq(0) & o.post_any.eq(0), o.pre_any.eq(1) & o.post_any.eq(0),
         o.pre_any.eq(0) & o.post_any.eq(1), o.pre_any.eq(1) & o.post_any.eq(1)],
        ["None", "Pre only", "Post only", "Pre and post"], default="Unknown")
    o["cpo"] = o.cpo_total
    o["order_value"] = pd.to_numeric(o.get("f0_"), errors="coerce")
    o["pu_km"] = pd.to_numeric(o.get("pu_distance"), errors="coerce") / 1000
    o["do_km"] = pd.to_numeric(o.get("do_distance"), errors="coerce") / 1000
    o["dist_total_km"] = o.pu_km + o.do_km
    o["distance_outlier"] = o.pu_km.gt(15) | o.do_km.gt(15) | o.pu_km.lt(0) | o.do_km.lt(0)
    o["dist_bucket"] = pd.cut(o.dist_total_km.where(o.dist_total_km.ge(0)), [-np.inf,1,2,3,5,np.inf],
                                 labels=["<1km", "1-2km", "2-3km", "3-5km", ">5km"], right=False).astype("string").fillna("Unknown")
    o["prep_bucket"] = pd.cut(o.t_wait_at_pu_min.where(o.t_wait_at_pu_min.ge(0)), [-np.inf,3,7,12,20,np.inf],
                                 labels=["<3 min", "3-7 min", "7-12 min", "12-20 min", ">=20 min"], right=False).astype("string").fillna("Unknown")
    o["ticket_bucket"], _ = band(o.order_value)
    o["prep_time_min"] = o.t_wait_at_pu_min.where(o.t_wait_at_pu_min.ge(0))
    audit = {
        "raw_rows": len(df), "unique_orders": len(o), "principal_rows": len(main),
        "reason_bearing_rows": int(df.cost_record_type.eq("Reason-bearing").sum()),
        "exact_duplicate_rows": int(raw.duplicated().sum()),
        "raw_cost_total": float(df.cpo.sum()), "order_cost_total": float(o.cpo_total.sum()),
        "cost_reconciliation_error": float(o.cpo_total.sum() - df.cpo.sum()),
        "status_counts": o.order_status.value_counts(dropna=False).to_dict(),
        "invalid_process_orders": int((~o.process_eligible & o.completed_flag.eq(1)).sum()),
        "source_cost_records_are_not_event_histories": True,
    }
    repeated = df[df.duplicated("id_pedido", keep=False)]
    audit["orders_with_varying_final_assignment_fields"] = repeated.groupby("id_pedido")[["id_repartidor"] + TIMESTAMPS].nunique(dropna=False).gt(1).sum().to_dict()
    return o.sort_values("id_pedido").reset_index(drop=True), df, audit


def expand_events(raw, calendar):
    """Preserve overlaps as independent flags/counts; deduplicate exact inputs."""
    e = raw.copy()
    e["date"] = parse_datetime(e.date)
    duplicates = int(e.duplicated(["date", "event_type"]).sum())
    e = e.drop_duplicates(["date", "event_type"])
    rows = []
    for row in e.dropna(subset=["date", "event_type"]).itertuples():
        start = row.date.normalize() if row.event_type == "country_holiday" else row.date.floor("h") - pd.Timedelta(hours=1)
        for offset in range(24 if row.event_type == "country_holiday" else 5):
            rows.append((start + pd.Timedelta(hours=offset), str(row.event_type)))
    events = pd.DataFrame(rows, columns=["date_hour", "event_type"])
    result = calendar[["date_hour"]].copy()
    if not events.empty:
        counts = events.groupby(["date_hour", "event_type"]).size().unstack(fill_value=0)
        for category in sorted(set(e.event_type.dropna().astype(str)) | {"football_match", "country_holiday"}):
            mapping = counts[category] if category in counts else pd.Series(dtype=int)
            result[category + "_count"] = result.date_hour.map(mapping).fillna(0).astype(int)
            result[category] = result[category + "_count"].gt(0)
        labels = events.groupby("date_hour").event_type.agg(lambda x: " | ".join(sorted(set(x))))
        result["event_type"] = result.date_hour.map(labels).fillna("No event")
    else:
        for category in ["football_match", "country_holiday"]:
            result[category] = False
            result[category + "_count"] = 0
        result["event_type"] = "No event"
    return result, {"raw_events": len(raw), "exact_duplicate_events": duplicates,
                    "unparseable_event_dates": int(e.date.isna().sum()),
                    "event_window_assumption": "Football: floor(event time)-1h through +3h inclusive; holiday: recorded calendar day."}


def weather_context(raw, calendar):
    w = raw.copy()
    w["date_hour"] = parse_datetime(w.date).dt.floor("h")
    cols = ["date_hour", "temperature", "precip_mm", "wind", "condition"]
    w = w[cols].drop_duplicates()
    if w.date_hour.duplicated().any():
        raise ValueError("Conflicting weather observations for one hour; cannot select an arbitrary first record.")
    out = calendar[["date_hour"]].merge(w.dropna(subset=["date_hour"]), on="date_hour", how="left", validate="one_to_one")
    out["lluvia"] = np.select([out.precip_mm.isna(), out.precip_mm.eq(0), out.precip_mm.gt(0) & out.precip_mm.lt(.5), out.precip_mm.ge(.5)],
                              ["Unknown", "Dry", "Drizzle", "Rain"], default="Unknown")
    out["condition"] = out.condition.fillna("Unknown")
    return out


def build_rider_hours(raw, lower, upper):
    required = ["shift_id", "rider_id", "fecha_inicio", "hora_inicio", "fecha_fin", "hora_fin"]
    if not set(required).issubset(raw):
        raise ValueError("Missing shift columns")
    if raw.shift_id.duplicated().any():
        raise ValueError("Duplicate shift IDs require source resolution.")
    t = raw.copy()
    t["rider_id"] = t.rider_id.astype("string")
    complete = t[required].notna().all(axis=1)
    t = t.loc[complete].copy()
    a = parse_datetime(t.fecha_inicio).dt.strftime("%Y-%m-%d") + " " + t.hora_inicio.astype(str)
    b = parse_datetime(t.fecha_fin).dt.strftime("%Y-%m-%d") + " " + t.hora_fin.astype(str)
    legacy_bad = pd.to_datetime(a, errors="coerce").isna() | pd.to_datetime(b, errors="coerce").isna()
    t["ini"], t["fin"] = parse_datetime(a), parse_datetime(b)
    unparsed = t[["ini", "fin"]].isna().any(axis=1)
    duration = (t.fin - t.ini).dt.total_seconds() / 3600
    invalid = unparsed | duration.le(0)
    long = duration.gt(16)
    audit = {"raw_shifts": len(raw), "missing_shift_datetime_rows": int((~complete).sum()),
             "complete_shift_rows": int(complete.sum()), "mixed_parse_failures": int(unparsed.sum()),
             "legacy_parse_failures": int(legacy_bad.sum()), "nonpositive_durations": int(duration.le(0).sum()),
             "long_shifts_gt16h": int(long.sum()), "long_shift_policy": "Retain positive durations; report <=16h sensitivity."}
    t["long_shift"] = long
    t = t[~invalid & t.fin.gt(lower) & t.ini.lt(upper)].copy()
    t["ini"] = t.ini.clip(lower=lower)
    t["fin"] = t.fin.clip(upper=upper)
    t = t.sort_values(["rider_id", "ini", "fin"]).reset_index(drop=True)
    # Subtract previously covered parts before hourly expansion: cumulative max
    # handles nested intervals and intervals that overlap more than one predecessor.
    previous_end = t.groupby("rider_id").fin.cummax().groupby(t.rider_id).shift()
    effective_start = t.ini.where(previous_end.isna() | t.ini.ge(previous_end), previous_end)
    t["effective_ini"] = effective_start
    audit["overlapping_shift_rows"] = int(t.ini.lt(previous_end).sum())
    audit["valid_window_shifts"] = len(t)
    audit["unmerged_window_hours"] = float((t.fin - t.ini).dt.total_seconds().sum()/3600)
    audit["window_hours_excluding_long_shifts_unmerged"] = float((t.loc[~t.long_shift, "fin"] - t.loc[~t.long_shift, "ini"]).dt.total_seconds().sum()/3600)
    segments = t[t.fin.gt(t.effective_ini)].copy()
    if segments.empty:
        rider_hours = pd.DataFrame(columns=["rider_id", "date_hour", "rider_hours"])
    else:
        first = segments.effective_ini.dt.floor("h")
        counts = ((segments.fin.dt.ceil("h") - first).dt.total_seconds()/3600).astype(int)
        pos = np.repeat(np.arange(len(segments)), counts.to_numpy())
        offsets = np.concatenate([np.arange(n) for n in counts])
        expanded = segments.iloc[pos].reset_index(drop=True)
        expanded["date_hour"] = first.iloc[pos].reset_index(drop=True) + pd.to_timedelta(offsets, unit="h")
        start = expanded.effective_ini.where(expanded.effective_ini.gt(expanded.date_hour), expanded.date_hour)
        end_hour = expanded.date_hour + pd.Timedelta(hours=1)
        end = expanded.fin.where(expanded.fin.lt(end_hour), end_hour)
        expanded["rider_hours"] = (end-start).dt.total_seconds()/3600
        rider_hours = expanded.groupby(["rider_id", "date_hour"], as_index=False).rider_hours.sum()
        rider_hours = rider_hours[rider_hours.rider_hours.gt(0)]
        if rider_hours.rider_hours.gt(1 + 1e-9).any():
            raise ValueError("A rider cannot contribute more than one observed hour per calendar hour.")
    audit["union_window_rider_hours"] = float(rider_hours.rider_hours.sum())
    audit["overlap_hours_removed"] = audit["unmerged_window_hours"] - audit["union_window_rider_hours"]
    audit["dated_window_riders"] = int(rider_hours.rider_id.nunique())
    excluded = raw.loc[~complete, required].copy()
    excluded["exclusion_reason"] = "Missing shift identity or date/time; cannot place in analysis window"
    return rider_hours, t, excluded, audit


def hourly_data(orders, rider_hours, context):
    hours = context.copy()
    _calendar(hours)
    o = orders.assign(_actual=orders.actual_min.where(orders.service_eligible))
    agg = o.groupby("date_hour").agg(
        pedidos=("id_pedido", "size"), completed=("completed_flag", "sum"),
        late_count=("tardio", "sum"), late_eligible_count=("tardio", "count"),
        pre_affected=("pre_any", "sum"), pre_eligible_count=("pre_any", "count"),
        post_affected=("post_any", "sum"), post_eligible_count=("post_any", "count"),
        cpo_total=("cpo_total", "sum"), mean_actual_min=("_actual", "mean"),
        p90_actual_min=("_actual", lambda x: x.quantile(.9)),
        mean_pre_undispatches=("pre_undispatches", "mean"), mean_post_undispatches=("post_undispatches", "mean"))
    hours = hours.merge(agg, on="date_hour", how="left", validate="one_to_one")
    counts = ["pedidos", "completed", "late_count", "late_eligible_count", "pre_affected", "pre_eligible_count", "post_affected", "post_eligible_count", "cpo_total"]
    hours[counts] = hours[counts].fillna(0)
    supply = rider_hours.groupby("date_hour").agg(rider_hours_total=("rider_hours", "sum"), observed_riders=("rider_id", "nunique"))
    hours = hours.merge(supply, on="date_hour", how="left", validate="one_to_one")
    hours["rider_hours_total"] = hours.rider_hours_total.astype("float64")
    hours["observed_riders"] = hours.observed_riders.astype("float64")
    hours["supply_observed"] = hours.rider_hours_total.notna()
    hours["utr_proxy"] = hours.pedidos / hours.rider_hours_total.where(hours.rider_hours_total.gt(0))
    cuts = {}
    for name, column in [("demand_band", "pedidos"), ("supply_band", "rider_hours_total"), ("pressure_band", "utr_proxy")]:
        hours[name], cuts[name] = band(hours[column])
    for name, column in [("relative_demand_band", "pedidos"), ("relative_supply_band", "rider_hours_total")]:
        hours[name] = "Unknown"
        cuts[name] = {}
        for clock_hour, group in hours.groupby("hora_num"):
            labels, boundaries = band(group[column])
            hours.loc[group.index, name] = labels
            cuts[name][int(clock_hour)] = boundaries
    profile = hours.groupby("hora_num").pedidos.mean()
    peak_cutoff = profile.quantile(.75)
    hours["peak_hour"] = hours.hora_num.map(profile).ge(peak_cutoff)
    first, last = orders.fecha_creacion.min(), orders.fecha_creacion.max()
    hours["partial_boundary_day"] = hours.fecha.eq(first.normalize()) | hours.fecha.eq(last.normalize())
    return hours.sort_values("date_hour").reset_index(drop=True), {"bands": cuts, "band_method": "Full-period empirical tertiles; tied values stay together; <=lower is Low, <=upper is Medium, otherwise High.", "peak_hour_cutoff_mean_orders": float(peak_cutoff)}


def data_dictionary(frames):
    meanings = {
        "id_pedido": ("Unique order identifier", "identifier", "source"),
        "id_comercio": ("Merchant identifier", "identifier", "source"),
        "id_repartidor": ("Retained/final rider identifier; not the identity of a prior rejecting rider", "identifier", "source"),
        "rider_id": ("Rider identifier in recorded shifts", "identifier", "source"),
        "shift_id": ("Recorded shift identifier", "identifier", "source"),
        "fecha_creacion": ("Recorded order creation time", "timestamp, timezone undocumented", "source"),
        "sent_to_vendor_at": ("Recorded order sent to merchant", "timestamp", "source"),
        "vendor_accepted_at": ("Recorded merchant acceptance; may follow rider notification", "timestamp", "source"),
        "rider_notified_at": ("Recorded final rider notification", "timestamp", "source"),
        "rider_accepted_at": ("Recorded final rider acceptance", "timestamp", "source"),
        "rider_at_pu": ("Recorded rider arrival at pickup", "timestamp", "source"),
        "rider_picked_up": ("Recorded pickup", "timestamp", "source"),
        "rider_at_do": ("Recorded destination arrival; endpoint matched by tiempo_real", "timestamp", "verified against elapsed time"),
        "rider_droped_off": ("Recorded final handoff; source spelling retained", "timestamp", "source"),
        "tiempo_real": ("Declared elapsed time; compare creation to destination arrival", "seconds", "timestamp-verified, rounding tolerance 1 second"),
        "tiempo_estimado": ("Declared promised elapsed time", "seconds", "source interpretation; promise endpoint not independently documented"),
        "demora_local": ("Opaque platform merchant-delay field; not equivalent to total pickup waiting", "source units undocumented", "unverified"),
        "f0_": ("Opaque recorded order-value field", "source monetary units undocumented", "inferred interpretation"),
        "order_value": ("Raw f0_ retained as order-value proxy; does not measure physical parcel size", "source monetary units undocumented", "inferred interpretation"),
        "cpo": ("Raw per-record cost in source; total recorded order cost in derived orders", "source monetary units undocumented", "source/derived according to dataset"),
        "cpo_entrega": ("Cost on principal order record, including non-completed order statuses", "recorded cost units", "derived"),
        "cpo_undispatch": ("Sum of costs on reason-bearing records for this order", "recorded cost units", "derived; not guaranteed savings"),
        "cpo_total": ("Sum of all recorded cost rows for order/hour", "recorded cost units", "derived and reconciled"),
        "pre_accept_undispatchs": ("Recorded pre-acceptance undispatch count", "events", "source"),
        "post_accept_undispatchs": ("Recorded post-acceptance undispatch count", "events", "source"),
        "undispatch_impact": ("Opaque platform undispatch-impact field; not used as a causal estimate", "undocumented", "unverified"),
        "undispatch_reason": ("Reason recorded on additional cost record; not a complete dispatch-event history", "category", "source"),
        "pu_distance": ("Recorded final-rider approach distance", "assumed metres", "inferred; final assignment descriptor"),
        "do_distance": ("Recorded pickup-to-destination distance", "assumed metres", "inferred"),
        "temperature": ("Hourly recorded temperature", "assumed degrees Celsius", "source interpretation"),
        "precip_mm": ("Hourly recorded precipitation", "mm", "source column label"),
        "wind": ("Hourly recorded wind magnitude", "unit undocumented", "source"),
        "condition": ("Hourly weather condition label", "category", "source"),
        "event_type": ("Source event type or union of active event-window categories", "category", "source/derived"),
        "vertical": ("Order/service vertical", "category", "source"),
        "vehicle": ("Retained rider vehicle; availability at earlier dispatch attempts is unobserved", "category", "source"),
        "order_status": ("Recorded final snapshot status", "category", "source"),
        "rider_hours_total": ("Union of dated rider shift intervals within hour; missing means no usable recorded supply", "observed rider-hours", "derived; not total actual capacity"),
        "rider_hours": ("Non-overlapping recorded time for one rider within one hour", "hours", "derived"),
        "utr_proxy": ("Recorded orders / observed rider-hours over matching calendar hours", "orders per observed rider-hour", "derived throughput proxy; not busy-time utilization"),
        "t_espera_asignacion_min": ("Signed merchant acceptance to final notification interval; overlap is allowed", "minutes", "timestamp-derived; not pure assignment queue"),
        "service_eligible": ("Completed order with finite nonnegative declared service duration", "boolean", "cohort rule"),
        "late_eligible": ("Service-eligible order with finite nonnegative promised duration", "boolean", "cohort rule"),
        "process_eligible": ("Completed order with all five additive stages present and nonnegative", "boolean", "cohort rule"),
        "tardio": ("Declared service duration exceeds declared promise; unknown if ineligible", "0/1", "derived, strict >0 minute gap"),
        "tardio_5min": ("Declared service duration exceeds promise by more than 5 minutes", "0/1", "derived"),
        "muy_tardio": ("Declared service duration exceeds promise by more than 15 minutes", "0/1", "derived"),
        "lluvia": ("Dry=0mm; Drizzle=(0,0.5)mm; Rain>=0.5mm; Unknown=missing/invalid", "category", "declared segmentation"),
        "cost_record_count": ("Number of source records for an order; not all dispatch attempts", "rows", "derived"),
    }
    meanings.update({k: (v, "minutes", "timestamp-derived") for k,v in STAGES.items()})
    rows = []
    for name, frame in frames.items():
        for col in frame.columns:
            meaning, unit, status = meanings.get(col, (col.replace("_", " "), "minutes" if col.endswith("_min") else "see metric/field name", "derived" if not name.startswith("raw_") else "source meaning undocumented"))
            if col.startswith("hora_"): unit = "time of day"
            if col.startswith("fecha_") and name == "raw_shifts": unit = "calendar date"
            rows.append({"dataset": name, "variable": col, "meaning": meaning, "unit": unit,
                         "type": str(frame[col].dtype), "missing_values": int(frame[col].isna().sum()),
                         "missing_fraction": float(frame[col].isna().mean()), "unique_values": int(frame[col].nunique()),
                         "semantic_status": status, "source": SOURCES.get(name.replace("raw_", ""), "Canonical pipeline"),
                         "business_interpretation": meaning})
    return pd.DataFrame(rows)


def build_data(config: Config):
    config.output_dir.mkdir(parents=True, exist_ok=True)
    provenance = {name: {"file": filename, "sha256": sha256(config.data_dir / filename), "bytes": (config.data_dir / filename).stat().st_size} for name,filename in SOURCES.items()}
    raw_orders = pd.read_csv(config.data_dir / SOURCES["orders"], dtype={"id_pedido":"string", "id_comercio":"string", "id_repartidor":"string"}, low_memory=False)
    raw_weather = pd.read_excel(config.data_dir / SOURCES["weather"])
    raw_events = pd.read_excel(config.data_dir / SOURCES["events"])
    raw_shifts = pd.read_excel(config.data_dir / SOURCES["shifts"])
    orders, records, order_qa = reconstruct_orders(raw_orders)
    lower, upper = orders.date_hour.min(), orders.date_hour.max() + pd.Timedelta(hours=1)
    calendar = pd.DataFrame({"date_hour": pd.date_range(lower, upper, freq="h", inclusive="left")})
    weather = weather_context(raw_weather, calendar)
    events, event_qa = expand_events(raw_events, calendar)
    context = weather.merge(events, on="date_hour", validate="one_to_one")
    riders, shifts, excluded, shift_qa = build_rider_hours(raw_shifts, lower, upper)
    hours, segmentation = hourly_data(orders, riders, context)
    enrich = hours.drop(columns=["fecha", "hora_num", "dia_semana", "cpo_total"])
    orders = orders.merge(enrich, on="date_hour", how="left", validate="many_to_one")
    shift_qa["orders_final_rider_without_dated_window_shift"] = int((~orders.id_repartidor.isin(riders.rider_id)).sum())
    qa = {"orders": order_qa, "shifts": shift_qa, "events": event_qa,
          "coverage": {"calendar_hours": len(hours), "hours_with_orders": int(hours.pedidos.gt(0).sum()),
                       "hours_with_supply": int(hours.supply_observed.sum()),
                       "zero_recorded_demand_supply_hours": int((hours.pedidos.eq(0)&hours.supply_observed).sum()),
                       "order_hours_without_supply": int((hours.pedidos.gt(0)&~hours.supply_observed).sum()),
                       "orders_without_hourly_supply": int(hours.loc[~hours.supply_observed,"pedidos"].sum()),
                       "weather_hours": int(hours.precip_mm.notna().sum()),
                       "orders_with_weather": int(orders.precip_mm.notna().sum())}, "segmentation": segmentation}
    frames = {"raw_orders": raw_orders, "raw_weather": raw_weather, "raw_events": raw_events, "raw_shifts": raw_shifts,
              "orders": orders, "cost_records": records, "rider_hours": riders, "hours": hours}
    dictionary = data_dictionary(frames)
    for name, frame in {"orders":orders,"cost_records":records,"rider_hours":riders,"hours":hours}.items():
        frame.to_parquet(config.output_dir / f"{name}.parquet", index=False)
    hours.to_csv(config.output_dir / "hours.csv", index=False)
    dictionary.to_csv(config.output_dir / "data_dictionary.csv", index=False)
    # Only lineage and exclusion information; raw workbook remains the source.
    excluded.astype("string").to_parquet(config.output_dir / "excluded_shifts.parquet", index=False)
    write_json(config.output_dir / "data_audit.json", qa)
    manifest = {"schema_version": SCHEMA_VERSION, "seed": config.seed, "bootstrap_samples": config.bootstrap_samples,
                "sources": provenance, "window_start_inclusive": str(lower), "window_end_exclusive": str(upper),
                "timestamp_policy": "Preserve source wall-clock timestamps; timezone not documented, no offset inferred.",
                "monetary_policy": "Recorded cost units; currency and accounting completeness unverified.",
                "row_counts": {name:len(frame) for name,frame in frames.items()}, "segmentation":segmentation}
    write_json(config.output_dir / "manifest.json", manifest)
    return {"orders":orders,"cost_records":records,"rider_hours":riders,"hours":hours,"audit":qa,"manifest":manifest,"dictionary":dictionary}
