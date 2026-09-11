"""Synthetic regression fixtures; these values are not business findings."""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from delivery_ops.powerbi import ORDER_DIMENSIONS, export_powerbi, validate_powerbi


def fixture():
    times = pd.date_range("2024-07-01", periods=3, freq="h")
    orders = pd.DataFrame({
        "id_pedido": ["001", "002", "003", "004"],
        "id_comercio": ["01", "01", "02", None],
        "id_repartidor": ["003", "004", "003", None],
        "date_hour": [times[0], times[0], times[1], times[1]],
        "actual_min": [10., 20., 30., -5.],
        "service_eligible": [True, True, True, False],
        "late_eligible": [True, True, False, False],
        "process_eligible": [True, True, True, False],
        "tardio": [0., 1., np.nan, np.nan],
        "pre_any": [0., 1., np.nan, 0.], "post_any": [1., 1., 0., np.nan],
        "pre_undispatches": [0., 4., np.nan, 0.],
        "post_undispatches": [2., 1., 0., np.nan],
        "cpo_total": [10.125, 0.1, np.nan, 3.],
        "completed_flag": [1, 1, 1, 0], "cancelled_flag": [0, 0, 0, 1],
        "segmento_undispatch": ["Post only", "Pre and post", "Unknown", "Unknown"],
        "vertical": ["Restaurant", "Restaurant", "Market", "Market"],
        "t_wait_at_pu_min": [1., 2., 3., np.nan],
    })
    hours = pd.DataFrame({
        "date_hour": times, "fecha": times.normalize(), "hora_num": times.hour,
        "dia_semana": ["Monday"] * 3, "pedidos": [2, 2, 0],
        "rider_hours_total": [1.25, np.nan, .5],
        "supply_observed": [True, False, True],
        "pressure_band": ["Medium", "Unknown", "Low"],
        "lluvia": ["Dry", "Dry", "Dry"],
    })
    return orders, hours


class PowerBIExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.orders, self.hours = fixture()

    def tearDown(self):
        self.temp.cleanup()

    def export(self):
        return export_powerbi(self.orders, self.hours, self.root)

    def test_independent_arithmetic_denominators_and_precision(self):
        result = self.export()
        validation = result["validation"]
        self.assertEqual(validation["status"], "passed", validation["errors"])
        metrics = {key: row["actual"] for key, row in validation["kpi_reconciliation"].items()}
        self.assertEqual(metrics["orders"], 4)
        self.assertEqual(metrics["hours"], 3)
        self.assertEqual(metrics["late_eligible_orders"], 2)
        self.assertEqual(metrics["late_rate"], .5)
        self.assertAlmostEqual(metrics["pre_affected_rate"], 1 / 3)
        self.assertEqual(metrics["pre_events"], 4)
        self.assertEqual(metrics["post_events"], 3)
        self.assertEqual(metrics["mean_delivery_minutes"], 20)
        self.assertEqual(metrics["p90_delivery_minutes"], 28)
        self.assertAlmostEqual(metrics["recorded_cost"], 13.225)
        self.assertEqual(metrics["orders_with_known_cost"], 3)
        self.assertEqual(metrics["recorded_rider_hours"], 1.75)
        # Only two orders fall in hours with observed supply; two have unknown supply.
        self.assertAlmostEqual(metrics["orders_per_recorded_rider_hour"], 2 / 1.75)
        self.assertEqual(validation["native_check"]["status"], "blocked")

    def test_leading_zero_ids_and_missing_values_survive(self):
        self.export()
        data = pd.read_csv(self.root / "powerbi/fact_orders.csv", dtype="string", keep_default_na=False)
        self.assertEqual(data.id_pedido.tolist(), ["001", "002", "003", "004"])
        self.assertEqual(data.id_repartidor.iloc[0], "003")
        self.assertEqual(data.cpo_total.iloc[2], "")
        self.assertEqual(data.pre_any.iloc[2], "")
        self.assertEqual(data.id_comercio.iloc[3], "Unknown")
        hourly = pd.read_csv(self.root / "powerbi/fact_hours.csv")
        self.assertTrue(pd.isna(hourly.rider_hours_total.iloc[1]))

    def test_shared_hour_filters_and_comprehensive_supply_guard(self):
        self.export()
        schema = json.loads((self.root / "powerbi/schema.json").read_text())
        relationships = schema["relationships"]
        self.assertIn(["fact_orders", "hour_id", "dim_hour", "hour_id"], relationships)
        self.assertIn(["fact_hours", "hour_id", "dim_hour", "hour_id"], relationships)
        self.assertIn("pressure_band", schema["tables"]["dim_hour"]["columns"])
        guard = next(row["expression"] for row in schema["measures"] if row["name"] == "Order only filter active")
        self.assertIn("ISFILTERED ( fact_orders )", guard)
        for name in ORDER_DIMENSIONS:
            self.assertIn(f"ISFILTERED ( {name} )", guard)
        self.assertNotIn("ISFILTERED ( dim_hour )", guard)
        self.assertFalse(any("recover" in row["name"].lower() or "saved" in row["name"].lower() for row in schema["measures"]))

    def test_existing_visuals_and_project_settings_are_byte_preserved(self):
        self.export()
        project = self.root / "powerbi/PanelDelivery"
        report = project / "PanelDelivery.Report"
        authored = {"config": "{}", "sections": [{"config": "{}", "visualContainers": [{"name": "authored", "config": "unchanged"}]}]}
        (report / "report.json").write_text(json.dumps(authored), encoding="utf-8")
        (report / "custom.bin").write_bytes(b"\x00\xffauthored asset")
        pointer = project / "PanelDelivery.pbip"
        pointer.write_text('{"version":"1.0","user_setting":"preserve"}', encoding="utf-8")
        before = {path: path.read_bytes() for path in report.rglob("*") if path.is_file()}
        pointer_before = pointer.read_bytes()
        result = self.export()
        self.assertEqual(result["report_preservation"]["status"], "preserved")
        self.assertEqual(pointer.read_bytes(), pointer_before)
        self.assertTrue(all(path.read_bytes() == value for path, value in before.items()))

    def test_validator_is_read_only_and_detects_changed_numbers(self):
        self.export()
        before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in self.root.rglob("*") if path.is_file()}
        self.assertEqual(validate_powerbi(self.root)["status"], "passed")
        self.assertTrue(all(hashlib.sha256(path.read_bytes()).hexdigest() == digest for path, digest in before.items()))
        path = self.root / "powerbi/fact_orders.csv"
        data = pd.read_csv(path, dtype="string", keep_default_na=False)
        data.loc[0, "cpo_total"] = "999"
        data.to_csv(path, index=False, encoding="utf-8-sig")
        validation = validate_powerbi(self.root)
        self.assertEqual(validation["status"], "failed")
        self.assertTrue(any("recorded_cost" in error for error in validation["errors"]))
        self.assertTrue(any("hash differs" in error for error in validation["errors"]))

    def test_rejects_duplicated_or_missing_hour_spine_and_mismatched_demand(self):
        with self.assertRaisesRegex(ValueError, "duplicate hours"):
            export_powerbi(self.orders, pd.concat([self.hours, self.hours.iloc[[0]]]), self.root)
        bad = self.hours.copy()
        bad.loc[2, "date_hour"] += pd.Timedelta(hours=1)
        with self.assertRaisesRegex(ValueError, "missing calendar hours"):
            export_powerbi(self.orders, bad, self.root)
        bad = self.hours.copy()
        bad.loc[0, "pedidos"] = 3
        with self.assertRaisesRegex(ValueError, "does not reconcile"):
            export_powerbi(self.orders, bad, self.root)

    def test_all_unknown_supply_and_outcomes_remain_unknown(self):
        self.orders["pre_any"] = np.nan
        self.orders["pre_undispatches"] = np.nan
        self.orders["tardio"] = np.nan
        self.orders["late_eligible"] = False
        self.hours["rider_hours_total"] = np.nan
        self.hours["supply_observed"] = False
        result = self.export()
        self.assertEqual(result["validation"]["status"], "passed", result["validation"]["errors"])
        metrics = result["validation"]["kpi_reconciliation"]
        self.assertIsNone(metrics["pre_affected_rate"]["actual"])
        self.assertIsNone(metrics["recorded_rider_hours"]["actual"])
        self.assertIsNone(metrics["orders_per_recorded_rider_hour"]["actual"])
        self.assertIsNone(metrics["late_rate"]["actual"])

    def test_missing_export_returns_failure_without_creating_files(self):
        result = validate_powerbi(self.root)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(list(self.root.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
