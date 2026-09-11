"""Regression tests for metric populations and real Streamlit interactions."""
from datetime import date
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from delivery_ops.dashboard import (
    SECTIONS, STAGES, Selection, aggregate_orders, capacity_summary,
    filter_frames, options, order_summary, stage_table,
)


@pytest.fixture
def frames():
    times = pd.to_datetime(["2024-07-01 10:00", "2024-07-01 10:00", "2024-07-01 11:00",
                            "2024-07-02 10:00", "2024-07-02 11:00", "2024-07-02 11:00"])
    orders = pd.DataFrame({
        "id_pedido": [str(i) for i in range(6)], "id_comercio": ["a", "a", "b", "b", "a", "a"],
        "date_hour": times, "service_eligible": [True, True, False, True, True, False],
        "process_eligible": [True, True, False, True, True, False],
        "actual_min": [20., 40., 300., 30., 50., 400.], "tardio": [0., 1., np.nan, 0., 1., np.nan],
        "cpo_total": [5., 10., np.nan, 7., 11., np.nan],
        "pre_any": [0., 1., np.nan, 1., 0., np.nan], "post_any": [0., 0., np.nan, 1., 0., np.nan],
        "pre_undispatches": [0., 3., np.nan, 2., 0., np.nan], "post_undispatches": [0., 0., np.nan, 2., 0., np.nan],
        "order_status": ["completed", "completed", "cancelled", "completed", "completed", "pending"],
        "vertical": ["food", "food", "market", "market", "food", "food"],
        "vehicle": ["bike", "bike", "car", "car", "bike", "bike"],
        "dist_bucket": pd.Categorical(["<1km", "1-2km", "<1km", "3-5km", "<1km", "<1km"],
                                       categories=["<1km", "1-2km", "2-3km", "3-5km", ">5km", "Unknown"]),
        "segmento_undispatch": ["None", "Pre only", "Unknown", "Pre and post", "None", "Unknown"],
        "lluvia": ["Dry", "Dry", "Dry", "Rain", "Dry", "Dry"],
        "event_type": ["None", "None", "None", "football | holiday", "football", "football"],
        "football_match": [False, False, False, True, True, True],
        "country_holiday": [False, False, False, True, False, False],
    })
    orders["hora_num"] = times.hour
    orders["dia_semana"] = times.day_name()
    for column in STAGES:
        orders[column] = orders["actual_min"] / 5
    orders["t_entrega_final_min"] = 1.
    hours = pd.DataFrame({
        "date_hour": pd.to_datetime(["2024-07-01 10:00", "2024-07-01 11:00", "2024-07-01 12:00", "2024-07-02 10:00", "2024-07-02 11:00"]),
        "pedidos": [2, 1, 0, 1, 2], "rider_hours_total": [1., np.nan, .5, .25, 2.],
        "p90_actual_min": [38., np.nan, np.nan, 30., 50.],
    })
    return orders, hours


def test_service_status_unknown_counts_and_cost_denominators(frames):
    orders, _ = frames
    result = order_summary(orders)
    assert result["orders"] == 6
    assert result["service_eligible_orders"] == 4
    assert result["mean_min"] == 35
    assert result["late_rate"] == .5
    assert result["late_eligible_orders"] == 4
    assert result["pre_events"] == 5
    assert result["pre_affected_orders"] == 2
    assert result["pre_rate"] == .5
    assert result["pre_events_per_known_order"] == 1.25
    assert result["recorded_cost"] == 33
    assert result["recorded_cpo"] == 8.25


def test_unknown_and_empty_are_not_zero(frames):
    orders, _ = frames
    unknown = order_summary(orders.loc[~orders.service_eligible])
    assert pd.isna(unknown["late_rate"])
    assert pd.isna(unknown["pre_events"])
    assert pd.isna(unknown["recorded_cost"])
    empty = order_summary(orders.iloc[:0])
    assert empty["orders"] == 0
    assert pd.isna(empty["mean_min"])


def test_ratio_of_sums_uses_matching_observed_hours(frames):
    _, hours = frames
    result = capacity_summary(hours)
    assert result["calendar_hours"] == 5
    assert result["hours_without_observed_capacity"] == 1
    assert result["orders_at_observed_capacity"] == 5
    assert result["observed_rider_hours"] == 3.75
    assert result["utr_proxy"] == pytest.approx(5 / 3.75)
    assert pd.isna(capacity_summary(hours, has_order_filters=True)["utr_proxy"])


def test_zero_capacity_does_not_divide_by_zero():
    hours = pd.DataFrame({"pedidos": [7, 3], "rider_hours_total": [0., np.nan]})
    result = capacity_summary(hours)
    assert result["hours_with_observed_capacity"] == 1
    assert pd.isna(result["utr_proxy"])


def test_time_selection_aligns_grains_and_retains_zero_demand(frames):
    orders, hours = frames
    selection = Selection(date(2024, 7, 1), date(2024, 7, 1), hours=(10, 12))
    selected_orders, selected_hours = filter_frames(orders, hours, selection)
    assert len(selected_orders) == 3
    assert len(selected_hours) == 3
    assert selected_hours.pedidos.sum() == len(selected_orders)
    assert selected_hours.iloc[-1].pedidos == 0
    narrow = Selection(date(2024, 7, 1), date(2024, 7, 1), order_filters={"dist_bucket": "<1km"})
    filtered, supply = filter_frames(orders, hours, narrow)
    assert len(filtered) == 2
    assert len(supply) == 3
    assert narrow.has_order_filters


def test_absent_distance_bins_and_unknown_options(frames):
    orders, _ = frames
    narrow = orders.loc[orders.dist_bucket.eq("<1km")]
    table = aggregate_orders(narrow, "dist_bucket")
    assert table.dist_bucket.tolist() == ["<1km"]
    assert table.orders.tolist() == [4]
    assert aggregate_orders(narrow, "dist_bucket", minimum=5).empty
    assert options(narrow, "dist_bucket") == ["All", "<1km"]
    assert options(pd.DataFrame({"vertical": [None, "food"]}), "vertical") == ["All", "Unknown", "food"]


def test_process_comparison_uses_common_valid_cohort(frames):
    orders, _ = frames
    orders.loc[0, "t_wait_at_pu_min"] = np.nan
    table = stage_table(orders)
    assert table.orders.tolist() == [3] * len(STAGES)
    assert table.on_time_orders.tolist() == [1] * len(STAGES)
    assert table.late_orders.tolist() == [2] * len(STAGES)
    assert table.mean_min.sum() == 40
    assert table.late_minus_on_time_min.sum() == 15


@pytest.fixture
def app(frames, tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest
    orders, hours = frames
    orders.to_parquet(tmp_path / "orders.parquet", index=False)
    hours.to_parquet(tmp_path / "hours.parquet", index=False)
    analysis = {"findings": [{"id": "F_TEST", "title": "Fixture finding", "observation": "Fixed full-period finding.",
                               "evidence": {"orders": 6}, "confidence": "descriptive", "source_table": "fixture.csv"}],
                "priorities": [{"priority": 1, "issue": "Fixture action", "action": "Measure", "monitoring_kpi": "P90"}],
                "limitations": ["Synthetic fixture; not a business conclusion."]}
    (tmp_path / "analysis_results.json").write_text(json.dumps(analysis), encoding="utf-8")
    (tmp_path / "manifest.json").write_text(json.dumps({"source_hashes": {}, "fixture": True}), encoding="utf-8")
    monkeypatch.setenv("DELIVERY_OPS_OUTPUT_DIR", str(tmp_path))
    wrapper = Path(__file__).resolve().parents[1] / "v16" / "dashboard_v16.py"
    return AppTest.from_file(str(wrapper), default_timeout=30).run()


def test_streamlit_all_sections_and_short_distance_regression(app):
    assert not app.exception
    assert app.metric[0].value == "6"
    app.selectbox(key="dist_bucket").select("<1km").run()
    assert not app.exception
    assert app.metric[0].value == "4"
    for section in SECTIONS:
        app.radio(key="section").set_value(section).run()
        assert not app.exception, f"{section}: {app.exception}"
    app.radio(key="section").set_value("Demand and capacity").run()
    assert not any("Throughput proxy" in metric.label for metric in app.metric)
    assert any("ratios are unavailable" in info.value for info in app.info)


def test_streamlit_empty_and_combined_filters(app):
    app.selectbox(key="dist_bucket").select("<1km").run()
    app.selectbox(key="vehicle").select("car").run()
    app.selectbox(key="order_status").select("completed").run()
    assert not app.exception
    assert any("No orders match" in warning.value for warning in app.warning)
    app.radio(key="section").set_value("Demand and capacity").run()
    assert not app.exception
    app.multiselect(key="weekdays").set_value([]).run()
    assert not app.exception
    assert any("No orders match" in warning.value for warning in app.warning)


def test_streamlit_missing_outputs_is_actionable(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv("DELIVERY_OPS_OUTPUT_DIR", str(tmp_path))
    wrapper = Path(__file__).resolve().parents[1] / "v16" / "dashboard_v16.py"
    result = AppTest.from_file(str(wrapper)).run()
    assert not result.exception
    assert "Canonical outputs are not ready" in result.error[0].value
    assert "python -m delivery_ops run" in result.code[0].value
