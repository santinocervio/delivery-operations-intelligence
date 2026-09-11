"""Evidence-led Streamlit interface with import-safe descriptive helpers."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ALL, UNKNOWN = "All", "Unknown"
DISTANCES = ["<1km", "1-2km", "2-3km", "3-5km", ">5km", UNKNOWN]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
STAGES = {
    "t_created_to_notify_min": "Creation → final rider notification",
    "t_notify_to_accept_min": "Notification → acceptance",
    "t_accept_to_pu_arrival_min": "Acceptance → pickup arrival",
    "t_wait_at_pu_min": "Pickup arrival → pickup",
    "t_last_mile_min": "Pickup → destination arrival",
}
SECTIONS = ["Executive overview", "Demand and capacity", "Process bottlenecks", "Service tails",
            "Weather and events", "Recorded cost", "Segments and actions", "Evidence and data quality"]


@dataclass(frozen=True)
class Selection:
    """Date/hour filters apply to both grains; order filters disable UTR."""
    start: date
    end: date
    hours: tuple[int, int] = (0, 23)
    weekdays: tuple[str, ...] = tuple(DAYS)
    order_filters: dict[str, str] = field(default_factory=dict)

    @property
    def has_order_filters(self) -> bool:
        return any(value not in (ALL, "", None) for value in self.order_filters.values())


def numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame:
        return pd.Series(np.nan, index=frame.index, dtype=float)
    return pd.to_numeric(frame[column], errors="coerce")


def safe_ratio(numerator: float, denominator: float) -> float:
    return float(numerator / denominator) if pd.notna(denominator) and denominator > 0 else np.nan


def labels(values: pd.Series) -> pd.Series:
    return values.astype("string").fillna(UNKNOWN)


def options(frame: pd.DataFrame, column: str) -> list[str]:
    if column not in frame:
        return [ALL]
    present = labels(frame[column]).unique().tolist()
    ordered = [value for value in DISTANCES if value in present] if column == "dist_bucket" else sorted(present)
    return [ALL, *ordered]


def filter_frames(orders: pd.DataFrame, hours: pd.DataFrame, selection: Selection) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Filter canonical grains by the same clock before order-only slicing."""
    def by_clock(frame: pd.DataFrame) -> pd.DataFrame:
        clock = pd.to_datetime(frame["date_hour"])
        keep = (clock.dt.date.between(selection.start, selection.end)
                & clock.dt.hour.between(*selection.hours)
                & clock.dt.day_name().isin(selection.weekdays))
        return frame.loc[keep].copy()
    selected_orders, selected_hours = by_clock(orders), by_clock(hours)
    for column, value in selection.order_filters.items():
        if value not in (ALL, "", None):
            if column not in selected_orders:
                raise ValueError(f"Unsupported order filter: {column}")
            selected_orders = selected_orders.loc[labels(selected_orders[column]).eq(value)].copy()
    return selected_orders, selected_hours


def order_summary(frame: pd.DataFrame) -> dict[str, Any]:
    """Use eligible denominators; keep events and affected orders distinct."""
    service = numeric(frame, "actual_min").where(frame.get("service_eligible", pd.Series(False, index=frame.index)).fillna(False))
    result: dict[str, Any] = {
        "orders": len(frame), "hours_with_orders": frame["date_hour"].nunique(),
        "dates_with_orders": pd.to_datetime(frame["date_hour"]).dt.date.nunique(),
        "service_eligible_orders": int(service.notna().sum()),
        "service_coverage": safe_ratio(service.notna().sum(), len(frame)),
        "mean_min": service.mean(), "median_min": service.median(), "p75_min": service.quantile(.75),
        "p90_min": service.quantile(.90), "p95_min": service.quantile(.95), "variance_min2": service.var(),
    }
    for short, column in (("late", "tardio"), ("pre", "pre_any"), ("post", "post_any")):
        values = numeric(frame, column)
        result[f"{short}_eligible_orders"] = int(values.notna().sum())
        result[f"{short}_affected_orders"] = values.sum(min_count=1)
        result[f"{short}_rate"] = safe_ratio(values.sum(min_count=1), values.notna().sum())
    for short in ("pre", "post"):
        values = numeric(frame, f"{short}_undispatches")
        result[f"{short}_events"] = values.sum(min_count=1)
        result[f"{short}_event_eligible_orders"] = int(values.notna().sum())
        result[f"{short}_events_per_known_order"] = safe_ratio(values.sum(min_count=1), values.notna().sum())
    cost = numeric(frame, "cpo_total")
    result.update(recorded_cost=cost.sum(min_count=1), cost_eligible_orders=int(cost.notna().sum()), recorded_cpo=cost.mean())
    return result


def aggregate_orders(frame: pd.DataFrame, by: str, minimum: int = 1) -> pd.DataFrame:
    """Only observed groups are emitted, so narrow distance filters are safe."""
    if by not in frame:
        return pd.DataFrame()
    records = [{by: value, **order_summary(subset)}
               for value, subset in frame.groupby(labels(frame[by]), observed=True, sort=False)
               if len(subset) >= minimum]
    result = pd.DataFrame(records)
    if result.empty:
        return result
    ordering = DISTANCES if by == "dist_bucket" else DAYS if by == "dia_semana" else None
    if ordering:
        result = result.assign(_rank=result[by].map({v: i for i, v in enumerate(ordering)})).sort_values("_rank").drop(columns="_rank")
    else:
        result = result.sort_values("orders", ascending=False)
    return result.reset_index(drop=True)


def capacity_summary(hours: pd.DataFrame, has_order_filters: bool = False) -> dict[str, Any]:
    """Ratio of sums on hours with positive observed capacity, never mean UTR."""
    supply = numeric(hours, "rider_hours_total")
    observed, ratio_eligible = supply.notna() & supply.ge(0), supply.gt(0)
    demand_at_observed_supply = numeric(hours, "pedidos").where(ratio_eligible).sum(min_count=1)
    capacity = supply.where(ratio_eligible).sum(min_count=1)
    return {
        "calendar_hours": len(hours), "hours_with_observed_capacity": int(observed.sum()),
        "hours_without_observed_capacity": int((~observed).sum()),
        "observed_rider_hours": supply.where(observed).sum(min_count=1),
        "ratio_eligible_hours": int(ratio_eligible.sum()), "orders_at_observed_capacity": demand_at_observed_supply,
        "utr_proxy": np.nan if has_order_filters else safe_ratio(demand_at_observed_supply, capacity),
        "capacity_ratios_available": not has_order_filters,
    }


def stage_table(orders: pd.DataFrame) -> pd.DataFrame:
    """Stage means and late/on-time differences share one valid cohort."""
    if any(column not in orders for column in STAGES):
        return pd.DataFrame()
    values = orders[list(STAGES)].apply(pd.to_numeric, errors="coerce")
    valid = orders.get("process_eligible", pd.Series(False, index=orders.index)).fillna(False)
    valid = valid & values.notna().all(axis=1) & values.ge(0).all(axis=1)
    subset = orders.loc[valid]
    late = numeric(subset, "tardio")
    rows = []
    for column, name in STAGES.items():
        stage = numeric(subset, column)
        ontime_mean, late_mean = stage.loc[late.eq(0)].mean(), stage.loc[late.eq(1)].mean()
        rows.append({"stage": name, "orders": len(subset), "mean_min": stage.mean(),
                     "on_time_orders": int(late.eq(0).sum()), "late_orders": int(late.eq(1).sum()),
                     "on_time_mean_min": ontime_mean, "late_mean_min": late_mean,
                     "late_minus_on_time_min": late_mean - ontime_mean})
    return pd.DataFrame(rows)


def read_outputs(output_dir: str, signature: tuple = ()) -> tuple[pd.DataFrame, pd.DataFrame, dict, dict]:
    """Read-only canonical boundary; signature invalidates Streamlit cache."""
    directory = Path(output_dir)
    orders = pd.read_parquet(directory / "orders.parquet")
    hours = pd.read_parquet(directory / "hours.parquet")
    analysis = json.loads((directory / "analysis_results.json").read_text(encoding="utf-8"))
    if (directory / "executive_findings.json").exists():
        analysis["findings"] = json.loads((directory / "executive_findings.json").read_text(encoding="utf-8"))
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    for frame, required, name in (
        (orders, ["id_pedido", "date_hour", "service_eligible", "actual_min", "tardio", "cpo_total"], "orders"),
        (hours, ["date_hour", "pedidos", "rider_hours_total"], "hours"),
    ):
        missing = set(required) - set(frame.columns)
        if missing:
            raise ValueError(f"Canonical {name} output is missing: {', '.join(sorted(missing))}")
    return orders, hours, analysis, manifest


def fmt(value: Any, precision: int = 1, percent: bool = False) -> str:
    if pd.isna(value):
        return "Unavailable"
    return f"{value:.{precision}%}" if percent else f"{value:,.{precision}f}"


def _plot(st: Any, figure: Any) -> None:
    figure.update_layout(template="plotly_white", font={"family": "Arial, sans-serif", "size": 13, "color": "#263746"},
                         margin={"l": 16, "r": 16, "t": 56, "b": 24}, legend={"orientation": "h", "y": -0.25})
    st.plotly_chart(figure, width="stretch", config={"displaylogo": False})


def _table(st: Any, frame: pd.DataFrame) -> None:
    if frame.empty:
        st.info("No eligible observations for this comparison. Broaden the filters or lower the minimum group size.")
    else:
        st.dataframe(frame, width="stretch", hide_index=True)


def _findings(st: Any, analysis: dict, maximum: int | None = None) -> None:
    findings = analysis.get("findings", [])
    if not findings:
        st.info("No generated findings are available. Re-run the analysis pipeline to create the evidence register.")
    for finding in findings[:maximum] if maximum else findings:
        with st.expander(f"{finding.get('id', '')} · {finding.get('title', 'Finding')}"):
            st.write(finding.get("observation", "Observation unavailable."))
            for key, label in (("interpretation", "Interpretation"), ("action", "Operational test")):
                if finding.get(key):
                    st.write(f"{label}: {finding[key]}")
            if finding.get("limitation"):
                st.caption(f"Limit: {finding['limitation']}")
            st.caption(f"Confidence: {finding.get('confidence', 'Not assessed')} · Evidence: {finding.get('source_table', 'analysis_results.json')}")
            if finding.get("evidence"):
                st.json(finding["evidence"], expanded=False)


def main() -> None:
    import plotly.express as px
    import streamlit as st

    st.set_page_config(page_title="Delivery Operations Intelligence", layout="wide")
    st.markdown("""<style>
    .stApp { background: #ffffff; color: #263746; }
    [data-testid="stSidebar"] { background: #f2f5f7; }
    h1 { font-size: 2rem !important; letter-spacing: -0.02em; }
    h2 { font-size: 1.45rem !important; } h3 { font-size: 1.15rem !important; }
    p { text-wrap: pretty; } [data-testid="stCaptionContainer"] { color: #46596a; }
    [data-testid="stMetricValue"] { font-size: 1.65rem; }
    @media (max-width: 700px) { h1 { font-size: 1.6rem !important; } }
    </style>""", unsafe_allow_html=True)
    st.title("Delivery Operations Intelligence")
    st.caption("Service, dispatch friction and observed capacity — one order per row, with the evidence behind each decision.")
    directory = Path(os.environ.get("DELIVERY_OPS_OUTPUT_DIR", str(ROOT / "outputs")))
    files = [directory / name for name in ("orders.parquet", "hours.parquet", "analysis_results.json", "manifest.json")]
    if (directory / "executive_findings.json").exists():
        files.append(directory / "executive_findings.json")
    missing = [path.name for path in files if not path.exists()]
    if missing:
        st.error(f"Canonical outputs are not ready: {', '.join(missing)}.")
        st.code("python -m delivery_ops run", language="shell")
        st.caption("Run the pipeline from the repository root, then refresh this page.")
        return
    cached_load = st.cache_data(show_spinner="Reading canonical outputs…")(read_outputs)
    try:
        orders, hours, analysis, manifest = cached_load(str(directory), tuple((p.stat().st_mtime_ns, p.stat().st_size) for p in files))
    except (OSError, ValueError, KeyError) as error:
        st.error(f"Unable to read canonical outputs: {error}")
        st.caption("Re-run the pipeline to regenerate a consistent output set.")
        return
    if hours.empty:
        st.info("The canonical calendar has no hours. Check source coverage in the pipeline audit.")
        return
    clock = pd.to_datetime(hours["date_hour"])
    min_date, max_date = clock.min().date(), clock.max().date()
    st.sidebar.title("Explore the operation")
    section = st.sidebar.radio("View", SECTIONS, key="section")
    st.sidebar.subheader("Shared time window")
    dates = st.sidebar.date_input("Date range", (min_date, max_date), min_value=min_date, max_value=max_date, key="dates")
    if not isinstance(dates, (tuple, list)) or len(dates) != 2:
        st.info("Select an end date to complete the reporting window.")
        return
    hour_range = st.sidebar.slider("Hours of day", 0, 23, (0, 23), key="hour_range")
    weekdays = st.sidebar.multiselect("Weekdays", DAYS, default=DAYS, key="weekdays")
    st.sidebar.subheader("Order characteristics")
    order_filters = {}
    for column, label in (("order_status", "Order status"), ("vertical", "Vertical"), ("vehicle", "Vehicle"),
                          ("dist_bucket", "Distance"), ("segmento_undispatch", "Undispatch segment")):
        order_filters[column] = st.sidebar.selectbox(label, options(orders, column), key=column)
    merchant = st.sidebar.text_input("Merchant ID (exact match)", key="merchant").strip()
    if merchant:
        order_filters["id_comercio"] = merchant
    selection = Selection(dates[0], dates[1], hour_range, tuple(weekdays), order_filters)
    selected, selected_hours = filter_frames(orders, hours, selection)
    metrics = order_summary(selected)
    capacity = capacity_summary(selected_hours, selection.has_order_filters)
    st.caption(f"Selected population: {dates[0]:%d %b %Y}–{dates[1]:%d %b %Y}, {hour_range[0]:02d}:00–{hour_range[1]:02d}:59 · "
               f"{len(selected):,} orders · {len(selected_hours):,} calendar hours. Source timestamps have no documented timezone.")
    if selection.has_order_filters:
        st.info("An order characteristic filter is active. Rider capacity is shared across orders, so throughput and capacity ratios are unavailable for this selection.")
    if selected.empty:
        st.warning("No orders match these filters. Broaden the date range, select a weekday, or reset an order characteristic to All. Calendar-hour coverage remains available under Demand and capacity.")
        if section not in ("Demand and capacity", "Evidence and data quality"):
            return
    st.subheader(section)

    if section == "Executive overview":
        tiles = st.columns(4)
        for tile, label, value, percent in zip(tiles, ["Selected orders", "Mean service (min)", "P90 service (min)", "Late / eligible orders"],
                                               [metrics["orders"], metrics["mean_min"], metrics["p90_min"], metrics["late_rate"]], [False, False, False, True]):
            tile.metric(label, fmt(value, 0 if label == "Selected orders" else 1, percent))
        st.caption(f"Service: {metrics['service_eligible_orders']:,} eligible orders; lateness: {metrics['late_eligible_orders']:,} eligible orders. Cancelled and pending orders do not enter service metrics.")
        if "order_status" in selected:
            _table(st, selected.groupby(labels(selected["order_status"]), observed=True).size().rename("orders").reset_index())
        daily = selected.assign(day=pd.to_datetime(selected["date_hour"]).dt.normalize()).groupby("day").size().rename("orders").reset_index()
        _plot(st, px.bar(daily, x="day", y="orders", title="When was recorded order demand concentrated?", color_discrete_sequence=["#397e88"]))
        st.markdown("### Findings from the complete study period")
        st.caption("The findings below come from the saved analysis and remain fixed when filters change. The charts and metrics above describe your selection.")
        _findings(st, analysis, maximum=6)

    elif section == "Demand and capacity":
        st.caption("Observed shift coverage is a capacity proxy. Orders per rider-hour does not measure riders’ busy-time utilization or establish adequate staffing.")
        _table(st, pd.DataFrame([{k: v for k, v in capacity.items() if k not in ("utr_proxy", "capacity_ratios_available")}]))
        if not selection.has_order_filters:
            st.metric("Throughput proxy: orders / observed rider-hour", fmt(capacity["utr_proxy"], 2))
            st.caption("Ratio of total orders to rider-hours on the same selected hours with positive observed capacity. Hours with unknown capacity are excluded from both sides of this ratio.")
            profile = selected_hours.groupby(pd.to_datetime(selected_hours["date_hour"]).dt.hour).agg(orders=("pedidos", "sum"), rider_hours=("rider_hours_total", lambda v: v.sum(min_count=1))).reset_index(names="hour")
            left, right = st.columns(2)
            with left:
                _plot(st, px.bar(profile, x="hour", y="orders", title="At what hours does demand arrive?", color_discrete_sequence=["#397e88"]))
            with right:
                _plot(st, px.bar(profile, x="hour", y="rider_hours", title="At what hours is rider capacity observed?", color_discrete_sequence=["#687f96"]))
            chart = selected_hours.loc[numeric(selected_hours, "rider_hours_total").gt(0)].copy()
            if not chart.empty and "p90_actual_min" in chart:
                chart["orders_per_rider_hour"] = chart["pedidos"] / chart["rider_hours_total"]
                _plot(st, px.scatter(chart, x="orders_per_rider_hour", y="p90_actual_min", hover_data=["date_hour", "pedidos"], title="How does hourly throughput co-vary with service tails?", color_discrete_sequence=["#397e88"]))
        st.markdown("### Capacity tests from the complete study period")
        st.caption("Discovery and temporal confirmation results below remain fixed under filters.")
        st.json(analysis.get("capacity", {}), expanded=False)

    elif section == "Process bottlenecks":
        table = stage_table(selected)
        eligible = int(table["orders"].iloc[0]) if not table.empty else 0
        st.caption(f"All additive stages use the same {eligible:,} orders with valid chronological process timestamps. The merchant branch is parallel; final handoff follows destination arrival.")
        if eligible:
            left, right = st.columns(2)
            with left:
                _plot(st, px.bar(table, x="mean_min", y="stage", orientation="h", title="Which stage occupies the most service time?", color_discrete_sequence=["#397e88"]).update_yaxes(autorange="reversed"))
            with right:
                _plot(st, px.bar(table, x="late_minus_on_time_min", y="stage", orientation="h", title="Which stage contributes most to late-order deterioration?", color_discrete_sequence=["#ae4254"]).update_yaxes(autorange="reversed"))
            _table(st, table)
        else:
            st.info("No complete valid process chains in this selection. Broaden the filters to compare stage timing.")
        extra = []
        for column, label in (("t_creacion_a_envio_min", "Merchant branch: creation → sent"), ("t_vendor_response_min", "Merchant branch: sent → acceptance"), ("t_entrega_final_min", "Final handoff: destination arrival → delivery")):
            values = numeric(selected, column).where(numeric(selected, column).ge(0))
            if values.notna().any():
                extra.append({"parallel_or_following_stage": label, "valid_orders": int(values.notna().sum()), "mean_min": values.mean(), "p90_min": values.quantile(.9)})
        if extra:
            st.markdown("### Separate timing context")
            st.caption("These stages have their own valid populations and are not added to the process comparison above.")
            _table(st, pd.DataFrame(extra))

    elif section == "Service tails":
        _table(st, pd.DataFrame([{key: metrics[key] for key in ("orders", "service_eligible_orders", "service_coverage", "mean_min", "median_min", "p75_min", "p90_min", "p95_min", "variance_min2")}]))
        eligible = selected.loc[selected["service_eligible"].fillna(False)]
        if not eligible.empty:
            _plot(st, px.histogram(eligible, x="actual_min", nbins=70, title="How wide is the service-time distribution?", labels={"actual_min": "Service time (minutes)"}, color_discrete_sequence=["#397e88"]))
        distance = aggregate_orders(selected, "dist_bucket")
        if not distance.empty:
            _plot(st, px.bar(distance, x="dist_bucket", y="p90_min", title="Which observed distance groups have the longest P90?", labels={"dist_bucket": "Distance", "p90_min": "P90 service (min)"}, color_discrete_sequence=["#397e88"]))
            _table(st, distance)
        st.caption("All available groups remain visible; no category is required to exist after filtering. These are descriptive comparisons, with eligible-order denominators in the table.")

    elif section == "Weather and events":
        st.caption("Orders share hourly weather and event exposures. Thousands of orders in one weather episode do not create independent weather observations. Combined event labels preserve overlap.")
        dimensions = [c for c in ("lluvia", "event_type", "football_match", "country_holiday") if c in selected]
        if dimensions:
            grouping = st.selectbox("External condition", dimensions, key="external_group")
            comparison = aggregate_orders(selected, grouping)
            if not comparison.empty:
                _plot(st, px.bar(comparison, x=grouping, y="p90_min", title="How does observed service vary across external conditions?", labels={"p90_min": "P90 service (min)"}, color_discrete_sequence=["#397e88"]))
                _table(st, comparison)
        st.markdown("### Weather support in the complete study period")
        st.caption("Full-period assessment; it is not re-estimated for the selected orders.")
        st.json(analysis.get("weather", {}), expanded=False)

    elif section == "Recorded cost":
        left, middle, right = st.columns(3)
        left.metric("Recorded cost total", fmt(metrics["recorded_cost"], 2))
        middle.metric("Recorded CPO / known-cost order", fmt(metrics["recorded_cpo"], 2))
        right.metric("Orders with known cost", fmt(metrics["cost_eligible_orders"], 0))
        st.caption("Currency is undocumented. Recorded CPO includes source cost/reason records attributed to each unique order; it is not a profit, incentive, waste or recoverable-savings estimate.")
        dimensions = [c for c in ("segmento_undispatch", "vertical", "dist_bucket", "order_status") if c in selected]
        if dimensions:
            grouping = st.selectbox("Compare recorded cost by", dimensions, key="cost_group")
            table = aggregate_orders(selected, grouping)
            if not table.empty:
                _plot(st, px.bar(table, x=grouping, y="recorded_cpo", title="Where is recorded cost per known-cost order higher?", color_discrete_sequence=["#397e88"]))
                _table(st, table)

    elif section == "Segments and actions":
        dimensions = [c for c in ("vertical", "vehicle", "dist_bucket", "id_comercio", "hora_num", "dia_semana", "segmento_undispatch") if c in selected]
        if dimensions:
            grouping = st.selectbox("Segment", dimensions, key="segment_group")
            minimum = st.number_input("Minimum orders per segment", min_value=1, max_value=max(len(orders), 1), value=min(100, max(len(orders), 1)), step=1, key="segment_minimum")
            table = aggregate_orders(selected, grouping, int(minimum))
            _table(st, table.head(200))
            if not table.empty:
                st.download_button("Download all selected segment metrics", table.to_csv(index=False).encode("utf-8"), "selected_segment_metrics.csv", "text/csv")
        st.caption("Ranks describe observed burden. Final rider identifiers do not reconstruct previous dispatch attempts or establish rider responsibility.")
        st.markdown("### Operational priorities from the complete study period")
        st.caption("Saved priorities remain fixed under filters. Actions are tests to monitor, with no assumed improvement percentage.")
        _table(st, pd.DataFrame(analysis.get("priorities", [])))

    else:
        st.markdown("### How to read this dashboard")
        st.markdown("""
        - Order metrics use unique orders; recorded costs retain their source-record lineage.
        - Service and late rates use eligible orders. Unknown counters do not become zero.
        - Rider-hours come from clipped, non-overlapping observed shifts; missing capacity remains unknown.
        - Time filters apply to orders and capacity together. Order-characteristic filters disable capacity ratios.
        - Charted subsets are descriptive. Saved findings, intervals and models describe the complete study period.
        - Observational associations suggest operational tests; they do not identify causal savings or staffing sufficiency.
        """)
        st.markdown("### Reproducibility manifest")
        st.json(manifest, expanded=False)
        st.markdown("### Limitations")
        for limitation in analysis.get("limitations", []):
            st.write(limitation)
        with st.expander("Model diagnostics and hypothesis tests"):
            st.json({"models": analysis.get("models", {}), "hypotheses": analysis.get("hypotheses", {}), "contrasts": analysis.get("contrasts", {})}, expanded=False)
        st.markdown("### Evidence register")
        _findings(st, analysis)
        st.download_button("Download complete study evidence", json.dumps(analysis, indent=2, ensure_ascii=False).encode("utf-8"), "analysis_results.json", "application/json")


if __name__ == "__main__":
    main()
