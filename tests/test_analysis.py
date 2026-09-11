"""Behavioral checks for denominator, timeline and inference safeguards."""
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from delivery_ops.analysis import (
    STAGES, _capacity, _models, _prepare, _segments, _stages,
    analyze, date_bootstrap_contrast,
)


def fixture(days=24, hours_per_day=6, per_hour=20):
    rows, hours = [], []
    identifier = 0
    for day in range(days):
        for hour in range(hours_per_day):
            dt = pd.Timestamp("2024-07-01") + pd.Timedelta(days=day, hours=hour+10)
            high = hour % 2 == 1
            hours.append({"date_hour": dt, "rider_hours_total": 8.0 if high else 20.0,
                          "pedidos": per_hour, "partial_boundary_day": False,
                          "pressure_band": "High" if high else "Low", "demand_band": "Medium",
                          "supply_band": "Low" if high else "High", "peak_hour": high})
            for order in range(per_hour):
                identifier += 1
                # Effects vary by date: whole-date bootstrap must keep this shared component.
                initial = 9.0 + (5 if high else 0) + day % 4
                stage_values = [initial, 1.0, 3.0, 4.0, 7.0]
                actual = sum(stage_values)
                late = int(actual > 27)
                rows.append({"id_pedido": str(identifier), "id_comercio": str(order % 5),
                    "id_repartidor": str(order % 11), "date_hour": dt, "fecha": dt.normalize(),
                    "completed_flag": 1, "cancelled_flag": 0, "actual_min": actual, "promised_min": 27.0,
                    "service_eligible": True, "late_eligible": True, "process_eligible": True,
                    "tardio": late, "tardio_5min": int(actual > 32),
                    "pre_any": int(order % 4 == 0), "post_any": int(order % 10 == 0),
                    "pre_undispatches": 4 if order % 20 == 0 else int(order % 4 == 0),
                    "post_undispatches": int(order % 10 == 0),
                    "cpo_total": 300 + 10*high, "cpo_undispatch": 5 if order % 10 == 0 else 0,
                    "order_value": 1000, "vertical": "restaurant" if order % 2 else "store",
                    "vehicle": "bici", "do_km": .7 if order % 2 else 3.5,
                    "dist_bucket": "<1km" if order % 2 else "3-5km", "ticket_bucket": "Q1",
                    "lluvia": "Rain" if day == 0 and hour == 0 else "Dry",
                    "precip_mm": 1.0 if day == 0 and hour == 0 else 0.0,
                    "event_type": "None", **dict(zip(STAGES, stage_values))})
    return pd.DataFrame(rows), pd.DataFrame(hours)


class AnalysisTests(unittest.TestCase):
    def test_additive_timeline_uses_common_cohort_and_initial_stage(self):
        orders, hours = fixture(days=4)
        orders.loc[0, "t_wait_at_pu_min"] = np.nan
        d, _ = _prepare(orders, hours)
        stages, late, _, summary = _stages(d)
        self.assertEqual(summary["eligible_orders"], len(orders)-1)
        self.assertTrue((stages.orders == len(orders)-1).all())
        self.assertAlmostEqual(stages.share_total_time.sum(), 1)
        self.assertAlmostEqual(late.share_of_total_difference.sum(), 1)
        self.assertAlmostEqual(summary["reconciliation_max_abs_error_min"], 0)
        self.assertEqual(summary["main_stage"], "Creation to final rider notification")

    def test_unknown_and_ineligible_outcomes_are_excluded_not_zero(self):
        orders, hours = fixture(days=1)
        orders.loc[0, ["tardio", "tardio_5min", "pre_any"]] = np.nan
        orders.loc[1, "late_eligible"] = False
        orders.loc[2, "service_eligible"] = False
        d, _ = _prepare(orders, hours)
        self.assertEqual(d._late.count(), len(orders)-2)
        self.assertEqual(d._service.count(), len(orders)-1)
        self.assertTrue(pd.isna(d.loc[0, "pre_any"]))
        self.assertTrue(pd.isna(d.loc[1, "_late"]))

    def test_duplicate_order_or_hour_keys_fail_before_analysis(self):
        orders, hours = fixture(days=1)
        with self.assertRaisesRegex(ValueError, "unique id_pedido"):
            _prepare(pd.concat([orders, orders.iloc[:1]]), hours)
        with self.assertRaisesRegex(ValueError, "unique date_hour"):
            _prepare(orders, pd.concat([hours, hours.iloc[:1]]))

    def test_bootstrap_is_reproducible_and_sparse_rain_has_no_interval(self):
        orders, hours = fixture()
        d, _ = _prepare(orders, hours)
        wet = d.precip_mm.gt(0)
        rainy = date_bootstrap_contrast(d, "_service", wet, name="rain", samples=500)
        self.assertFalse(rainy["inference_eligible"])
        self.assertEqual(rainy["exposed_dates"], 1)
        self.assertTrue(np.isnan(rainy["ci_low"]))
        exposure = d.pressure_band.eq("High")
        a = date_bootstrap_contrast(d, "_service", exposure, name="pressure", seed=12, samples=500)
        b = date_bootstrap_contrast(d, "_service", exposure, name="pressure", seed=12, samples=500)
        self.assertEqual(a, b)
        self.assertTrue(a["inference_eligible"])
        self.assertEqual(a["bootstrap_samples"], 500)
        self.assertAlmostEqual(a["difference"], 5)
        self.assertGreater(a["ci_low"], 0)

    def test_segment_rates_pool_orders_instead_of_averaging_hours(self):
        orders, hours = fixture(days=1, hours_per_day=2, per_hour=10)
        # Keep ten low-rate orders at one hour and a single positive at the other.
        orders = orders.iloc[list(range(10)) + [10]].copy()
        orders["pre_any"] = [0]*10 + [1]
        orders["lluvia"] = "Dry"
        d, _ = _prepare(orders, hours)
        t = _segments(d)
        row = t[t.family.eq("weather")].iloc[0]
        self.assertAlmostEqual(row.pre_rate, 1/11)
        self.assertEqual(row.pre_eligible_orders, 11)

    def test_full_hour_spine_and_constant_pressure_do_not_create_thresholds(self):
        orders, hours = fixture(days=2)
        hours["rider_hours_total"] = 10.0
        zero = hours.iloc[:1].copy()
        zero["date_hour"] = pd.Timestamp("2024-07-01 00:00")
        zero["pedidos"] = 0
        hours = pd.concat([hours, zero], ignore_index=True)
        hours.loc[1, "rider_hours_total"] = np.nan
        d, h = _prepare(orders, hours)
        _, thresholds, _, summary = _capacity(d, h, 42, 10)
        self.assertEqual(summary["full_calendar_hours"], len(hours))
        self.assertEqual(summary["supply_hours_without_orders"], 1)
        self.assertEqual(summary["demand_hours_missing_supply"], 1)
        self.assertFalse(thresholds.validated_association.any())

    def test_capacity_boundaries_are_exact_and_relative_bands_keep_ties(self):
        orders, hours = fixture(days=12)
        hours["rider_hours_total"] = 8.123456789 + np.arange(len(hours)) * .317123456
        d, h = _prepare(orders, hours)
        bins, _, _, _ = _capacity(d, h, 42, 10)
        pressure = h.pedidos / h.rider_hours_total
        self.assertAlmostEqual(bins.iloc[0].lower, pressure.min(), places=12)
        self.assertAlmostEqual(bins.iloc[0].upper, pressure.quantile(.25), places=12)
        # Constant per-clock demand stays together; no artificial high group.
        self.assertEqual(set(d.relative_demand_band), {"Low"})
        self.assertEqual(set(d.relative_supply_band), {"Low", "Medium", "High"})

    def test_constant_outcomes_are_not_fitted(self):
        orders, hours = fixture()
        orders[["pre_any", "post_any", "tardio_5min"]] = 0
        d, h = _prepare(orders, hours)
        coeff, diagnostics, summary = _models(d, h)
        self.assertTrue(coeff.empty)
        self.assertNotEqual(summary["status"], "estimated")
        self.assertGreater(len(diagnostics), 0)

    def test_models_report_clustered_estimates_when_design_is_supported(self):
        try:
            import statsmodels  # noqa: F401
        except ImportError:
            self.skipTest("statsmodels is optional until environment installation")
        orders, hours = fixture()
        rng = np.random.default_rng(71)
        hours["rider_hours_total"] = rng.uniform(6, 25, len(hours))
        orders["do_km"] = rng.choice([.3, .8, 1.5, 2.5, 4.0], len(orders))
        orders["pre_any"] = rng.binomial(1, .25, len(orders))
        orders["post_any"] = rng.binomial(1, .12, len(orders))
        orders["tardio_5min"] = rng.binomial(1, .2, len(orders))
        d, h = _prepare(orders, hours)
        coeff, diagnostics, result = _models(d, h)
        self.assertEqual(result["status"], "estimated")
        self.assertTrue(diagnostics.status.eq("estimated").all())
        self.assertTrue(np.isfinite(coeff[["coefficient", "std_error", "odds_ratio"]]).all().all())
        self.assertIn("log_observed_rider_hours", set(coeff.term))
        self.assertTrue(coeff.inference.str.contains("date-clustered").all())
        self.assertEqual(set(coeff.loc[coeff.term.str.startswith("_distance_band_"), "reference_category"]), {"0.5-1km"})

    def test_public_result_is_strict_json_and_writes_reviewable_tables(self):
        orders, hours = fixture(days=2)
        with tempfile.TemporaryDirectory() as folder:
            result = analyze(orders, hours, Path(folder), bootstrap_samples=20)
            json.dumps(result, allow_nan=False)
            self.assertEqual(result["status"], "complete")
            self.assertIn("stage_by_segment", result["tables"])
            self.assertFalse(result["weather"]["inference_eligible"])
            self.assertEqual([h["id"] for h in result["hypotheses"][:5]], ["H1", "H2", "H3", "H4", "H5"])
            self.assertTrue(all("controllability" in p and "affected_late5_orders" in p for p in result["priorities"]))
            for relative in result["tables"].values():
                path = Path(folder) / relative
                self.assertTrue(path.exists(), str(path))
                self.assertGreater(len(pd.read_csv(path).columns), 0)
            self.assertNotIn("rider_hours_saved", result["costs"])
            self.assertNotIn("avoidable_cost", result["costs"])


if __name__ == "__main__":
    unittest.main()
