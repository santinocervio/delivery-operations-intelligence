"""Import-safe, lossless Power BI exports and read-only static validation.

The Streamlit application is the authored report. This module builds a semantic
model and a PBIP report scaffold; it never claims to execute DAX or Power Query.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


SCHEMA_VERSION = "1.0"
PROJECT = "PanelDelivery"
ORDER_DIMENSIONS = {
    "dim_vertical": "vertical", "dim_vehicle": "vehicle",
    "dim_merchant": "id_comercio", "dim_rider": "id_repartidor",
    "dim_status": "order_status", "dim_undispatch": "segmento_undispatch",
    "dim_distance": "dist_bucket", "dim_preparation": "prep_bucket",
    "dim_ticket": "ticket_bucket",
}
ORDER_TYPES = {
    "id_pedido": "string", "hour_id": "string", "id_comercio": "string",
    "id_repartidor": "string", "vertical": "string", "vehicle": "string",
    "order_status": "string", "segmento_undispatch": "string",
    "dist_bucket": "string", "prep_bucket": "string", "ticket_bucket": "string",
    "actual_min": "double", "promised_min": "double", "gap_min": "double",
    "completed_flag": "int64", "cancelled_flag": "int64",
    "service_eligible": "int64", "late_eligible": "int64", "process_eligible": "int64",
    "tardio": "double", "tardio_5min": "double", "muy_tardio": "double",
    "pre_undispatches": "double", "post_undispatches": "double",
    "pre_any": "double", "post_any": "double", "any_undispatch": "double",
    "total_undispatches": "double", "cpo_total": "double",
    "cpo_entrega": "double", "cpo_undispatch": "double", "order_value": "double",
    "dist_total_km": "double", "pu_km": "double", "do_km": "double",
    "t_created_to_notify_min": "double", "t_notify_to_accept_min": "double",
    "t_accept_to_pu_arrival_min": "double", "t_wait_at_pu_min": "double",
    "t_last_mile_min": "double",
}
HOUR_TYPES = {
    "hour_id": "string", "pedidos": "int64", "completed": "int64",
    "late_count": "int64", "late_eligible_count": "int64",
    "pre_affected": "int64", "pre_eligible_count": "int64",
    "post_affected": "int64", "post_eligible_count": "int64",
    "cpo_total": "double", "mean_actual_min": "double", "p90_actual_min": "double",
    "rider_hours_total": "double", "observed_riders": "double",
    "supply_observed": "int64", "utr_proxy": "double",
}
SHARED_TYPES = {
    "hour_id": "string", "date_hour": "dateTime", "fecha": "dateTime",
    "hora_num": "int64", "dia_semana": "string", "partial_boundary_day": "int64",
    "temperature": "double", "precip_mm": "double", "wind": "double",
    "condition": "string", "lluvia": "string", "event_type": "string",
    "football_match": "int64", "country_holiday": "int64",
    "demand_band": "string", "supply_band": "string", "pressure_band": "string",
    "peak_hour": "int64",
}
ORDERS = {
    "segmento_undispatch": ["None", "Pre only", "Post only", "Pre and post", "Unknown"],
    "dist_bucket": ["<1km", "1-2km", "2-3km", "3-5km", ">5km", "Unknown"],
}
REQUIRED_ORDERS = {
    "id_pedido", "date_hour", "actual_min", "service_eligible", "late_eligible",
    "process_eligible", "tardio", "pre_any", "post_any", "pre_undispatches",
    "post_undispatches", "cpo_total", "completed_flag", "cancelled_flag",
}
REQUIRED_HOURS = {"date_hour", "pedidos", "rider_hours_total", "supply_observed"}


def _json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _number(value: Any) -> float | int | None:
    return None if pd.isna(value) or not np.isfinite(value) else float(value)


def _hour_ids(frame: pd.DataFrame) -> pd.Series:
    dates = pd.to_datetime(frame["date_hour"], errors="raise", format="mixed")
    if dates.isna().any() or dates.dt.tz is not None:
        raise ValueError("Power BI requires non-null canonical local-naive date_hour values.")
    if not dates.eq(dates.dt.floor("h")).all():
        raise ValueError("date_hour must be aligned to calendar hours.")
    return dates.dt.strftime("%Y-%m-%dT%H:00:00")


def _table(frame: pd.DataFrame, types: dict[str, str]) -> tuple[pd.DataFrame, dict[str, str]]:
    """Use declared types; never infer identifiers or numeric types from a sample."""
    types = {name: kind for name, kind in types.items() if name in frame}
    out = frame[list(types)].copy()
    for name, kind in types.items():
        if kind == "string":
            out[name] = out[name].astype("string").fillna("Unknown")
        elif kind == "dateTime":
            out[name] = pd.to_datetime(out[name], errors="raise", format="mixed").dt.strftime("%Y-%m-%dT%H:%M:%S")
        else:
            values = pd.to_numeric(out[name], errors="raise")
            if np.isinf(values.to_numpy(dtype=float, na_value=np.nan)).any():
                raise ValueError(f"Non-finite value in {name}")
            out[name] = values.astype("Int64" if kind == "int64" else "Float64")
    return out, types


def _metrics(orders: pd.DataFrame, hours: pd.DataFrame) -> dict[str, Any]:
    service = orders.loc[orders.service_eligible.eq(1), "actual_min"]
    late = orders.loc[orders.late_eligible.eq(1), "tardio"]
    observed = hours.loc[hours.supply_observed.eq(1), "rider_hours_total"]
    total_hours = observed.sum(min_count=1)
    return {
        "orders": int(len(orders)), "hours": int(len(hours)),
        "completed_orders": _number(orders.completed_flag.sum(min_count=1)),
        "cancelled_orders": _number(orders.cancelled_flag.sum(min_count=1)),
        "service_eligible_orders": int(orders.service_eligible.eq(1).sum()),
        "mean_delivery_minutes": _number(service.mean()),
        "p90_delivery_minutes": _number(service.quantile(.9)),
        "late_eligible_orders": int(late.count()), "late_orders": _number(late.sum(min_count=1)),
        "late_rate": _number(late.mean()),
        "pre_known_orders": int(orders.pre_any.count()), "post_known_orders": int(orders.post_any.count()),
        "pre_affected_orders": _number(orders.pre_any.sum(min_count=1)),
        "post_affected_orders": _number(orders.post_any.sum(min_count=1)),
        "pre_events": _number(orders.pre_undispatches.sum(min_count=1)),
        "post_events": _number(orders.post_undispatches.sum(min_count=1)),
        "pre_affected_rate": _number(orders.pre_any.mean()),
        "post_affected_rate": _number(orders.post_any.mean()),
        "recorded_cost": _number(orders.cpo_total.sum(min_count=1)),
        "orders_with_known_cost": int(orders.cpo_total.count()),
        "observed_supply_hours": int(hours.supply_observed.eq(1).sum()),
        "recorded_rider_hours": _number(total_hours),
        "orders_per_recorded_rider_hour": _number(hours.loc[hours.supply_observed.eq(1), "pedidos"].sum() / total_hours) if pd.notna(total_hours) and total_hours > 0 else None,
    }


def _measures(order_columns: set[str]) -> list[dict[str, str]]:
    # ISFILTERED on the whole fact also detects direct filters on any fact column.
    # Shared hour/weather/event/band filters arrive through dim_hour and remain valid.
    guard = " || ".join(["ISFILTERED ( fact_orders )"] + [f"ISFILTERED ( {table} )" for table in ORDER_DIMENSIONS])
    rows = [
        ("Orders", "COUNTROWS ( fact_orders )", "#,0", "01 Volume"),
        ("Completed orders", "SUM ( fact_orders[completed_flag] )", "#,0", "01 Volume"),
        ("Cancelled orders", "SUM ( fact_orders[cancelled_flag] )", "#,0", "01 Volume"),
        ("Cancellation rate", "DIVIDE ( [Cancelled orders], [Orders] )", "0.0%", "01 Volume"),
        ("Service eligible orders", "CALCULATE ( [Orders], KEEPFILTERS ( fact_orders[service_eligible] = 1 ) )", "#,0", "02 Service"),
        ("Mean delivery minutes", "CALCULATE ( AVERAGE ( fact_orders[actual_min] ), KEEPFILTERS ( fact_orders[service_eligible] = 1 ) )", "0.00", "02 Service"),
        ("P90 delivery minutes", "PERCENTILEX.INC ( FILTER ( fact_orders, fact_orders[service_eligible] = 1 ), fact_orders[actual_min], 0.90 )", "0.00", "02 Service"),
        ("Late eligible orders", "CALCULATE ( COUNT ( fact_orders[tardio] ), KEEPFILTERS ( fact_orders[late_eligible] = 1 ) )", "#,0", "02 Service"),
        ("Late orders", "CALCULATE ( SUM ( fact_orders[tardio] ), KEEPFILTERS ( fact_orders[late_eligible] = 1 ) )", "#,0", "02 Service"),
        ("Late rate", "DIVIDE ( [Late orders], [Late eligible orders] )", "0.0%", "02 Service"),
        ("Orders with known cost", "COUNT ( fact_orders[cpo_total] )", "#,0", "04 Recorded cost"),
        ("Recorded order cost", "SUM ( fact_orders[cpo_total] )", "#,0.00", "04 Recorded cost"),
        ("Mean recorded cost", "DIVIDE ( [Recorded order cost], [Orders with known cost] )", "#,0.00", "04 Recorded cost"),
        ("Calendar hours", "COUNTROWS ( dim_hour )", "#,0", "05 Recorded supply"),
        ("Hours with recorded supply", "SUM ( fact_hours[supply_observed] )", "#,0", "05 Recorded supply"),
        ("Recorded supply coverage", "DIVIDE ( [Hours with recorded supply], [Calendar hours] )", "0.0%", "05 Recorded supply"),
        ("Recorded rider hours", "CALCULATE ( SUM ( fact_hours[rider_hours_total] ), KEEPFILTERS ( fact_hours[supply_observed] = 1 ) )", "#,0.00", "05 Recorded supply"),
        ("Order only filter active", f"INT ( {guard} )", "0", "05 Recorded supply"),
        ("Orders in recorded supply hours", "CALCULATE ( SUM ( fact_hours[pedidos] ), KEEPFILTERS ( fact_hours[supply_observed] = 1 ) )", "#,0", "05 Recorded supply"),
        ("Orders per recorded rider hour", "IF ( [Order only filter active] = 1, BLANK (), DIVIDE ( [Orders in recorded supply hours], [Recorded rider hours] ) )", "0.00", "05 Recorded supply"),
        ("Supply interpretation", 'IF ( [Order only filter active] = 1, "Load is unavailable: this selection filters orders without filtering the shared supply population.", "Coverage-limited descriptive ratio: orders in hours with recorded supply divided by those same recorded rider hours. Undated shifts are excluded; missing supply is not zero. This is not measured rider utilization or recoverable capacity." )', "", "06 Interpretation"),
        ("Analysis interpretation", '"Observational associations only. f0 has unverified units and is not established physical order size or revenue. Rider IDs describe the recorded final assignment, not necessarily the rider who rejected an order."', "", "06 Interpretation"),
    ]
    for part in ("pre", "post"):
        label = part.capitalize()
        rows += [
            (f"{label} known orders", f"COUNT ( fact_orders[{part}_any] )", "#,0", "03 Undispatch"),
            (f"{label} affected orders", f"SUM ( fact_orders[{part}_any] )", "#,0", "03 Undispatch"),
            (f"{label} events", f"SUM ( fact_orders[{part}_undispatches] )", "#,0", "03 Undispatch"),
            (f"{label} affected rate", f"DIVIDE ( [{label} affected orders], [{label} known orders] )", "0.0%", "03 Undispatch"),
        ]
    if "cpo_undispatch" in order_columns:
        rows.append(("Recorded aborted cost", "SUM ( fact_orders[cpo_undispatch] )", "#,0.00", "04 Recorded cost"))
    if "order_value" in order_columns:
        rows.append(("Mean f0 value (units unverified)", "AVERAGE ( fact_orders[order_value] )", "#,0.00", "04 Recorded cost"))
    for column, label in [
        ("t_created_to_notify_min", "Creation to final notification"),
        ("t_notify_to_accept_min", "Final notification to acceptance"),
        ("t_accept_to_pu_arrival_min", "Acceptance to pickup arrival"),
        ("t_wait_at_pu_min", "Pickup waiting"), ("t_last_mile_min", "Pickup to destination arrival"),
    ]:
        if column in order_columns:
            rows.append((f"Mean {label.lower()} minutes", f"CALCULATE ( AVERAGE ( fact_orders[{column}] ), KEEPFILTERS ( fact_orders[process_eligible] = 1 ) )", "0.00", "02 Service"))
    return [{"name": n, "expression": e, "format": fmt, "folder": folder} for n, e, fmt, folder in rows]


def _tmdl_table(name: str, types: dict[str, str], measures: list[dict[str, str]] | None = None) -> str:
    lines = [f"table {name}", ""]
    for measure in measures or []:
        lines += [f"\tmeasure '{measure['name']}' = {measure['expression']}"]
        if measure["format"]:
            lines.append(f"\t\tformatString: {measure['format']}")
        lines += [f"\t\tdisplayFolder: {measure['folder']}", ""]
    for column, kind in types.items():
        lines += [f"\tcolumn {column}", f"\t\tdataType: {kind}", "\t\tsummarizeBy: none", f"\t\tsourceColumn: {column}"]
        if name.startswith("fact_") or column in {"hour_id", "sort_order", "technical"}:
            lines.append("\t\tisHidden")
        if name in ORDER_DIMENSIONS and column == ORDER_DIMENSIONS[name]:
            lines.append("\t\tsortByColumn: sort_order")
        if kind == "dateTime":
            lines.append("\t\tformatString: yyyy-mm-dd hh:mm")
        lines.append("")
    lines += [f"\tpartition {name} = m", "\t\tmode: import", "\t\tsource ="]
    m_types = {"string": "type text", "int64": "Int64.Type", "double": "type number", "dateTime": "type datetime"}
    pairs = ", ".join(f'{{"{column}", {m_types[kind]}}}' for column, kind in types.items())
    numeric = ", ".join(f'"{column}"' for column, kind in types.items() if kind != "string")
    query = ["let", f'    Source = Csv.Document(File.Contents(DataFolder & "/{name}.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),',
             '    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),',
             f'    Missing = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, {{{numeric}}}),',
             f'    Typed = Table.TransformColumnTypes(Missing, {{{pairs}}}, "en-US")', "in", "    Typed"]
    lines += ["\t\t\t\t" + line for line in query]
    return "\n".join(lines) + "\n"


def _report_snapshot(report: Path) -> dict[str, str]:
    if not report.exists():
        return {}
    return {path.relative_to(report).as_posix(): _hash(path) for path in report.rglob("*") if path.is_file()}


def export_powerbi(orders: pd.DataFrame, hours: pd.DataFrame, output_dir: Path) -> dict[str, Any]:
    """Export canonical frames without modifying the legacy Power BI project.

    Amounts retain source precision and missing values. Any existing report tree
    is byte-preserved. This function writes only below output_dir/powerbi.
    """
    missing = {"orders": sorted(REQUIRED_ORDERS - set(orders)), "hours": sorted(REQUIRED_HOURS - set(hours))}
    if any(missing.values()):
        raise ValueError(f"Missing canonical Power BI columns: {missing}")
    orders, hours = orders.copy(), hours.copy()
    if orders.id_pedido.isna().any() or orders.id_pedido.astype("string").duplicated().any():
        raise ValueError("Order IDs must be non-null and unique.")
    orders["hour_id"], hours["hour_id"] = _hour_ids(orders), _hour_ids(hours)
    if hours.hour_id.duplicated().any():
        raise ValueError("Hourly spine has duplicate hours.")
    if not set(orders.hour_id).issubset(set(hours.hour_id)):
        raise ValueError("Orders reference hours outside the canonical hourly spine.")
    if len(hours):
        dates = pd.to_datetime(hours.date_hour, format="mixed").sort_values()
        if len(pd.date_range(dates.min(), dates.max(), freq="h")) != len(hours):
            raise ValueError("The canonical hourly spine has missing calendar hours.")
    counts = orders.groupby("hour_id").size().reindex(hours.hour_id, fill_value=0).to_numpy()
    if not np.array_equal(counts, pd.to_numeric(hours.pedidos).to_numpy()):
        raise ValueError("Hourly demand does not reconcile with canonical orders.")
    # Ensure every categorical dimension has a known missing member; no fact rows disappear.
    for column in ORDER_DIMENSIONS.values():
        if column not in orders:
            orders[column] = "Unknown"
    export = Path(output_dir).resolve() / "powerbi"
    export.mkdir(parents=True, exist_ok=True)
    project = export / PROJECT
    model = project / f"{PROJECT}.SemanticModel"
    report = project / f"{PROJECT}.Report"
    existed = report.exists()
    snapshot_error = None
    try:
        before = _report_snapshot(report)
    except OSError as error:
        before, snapshot_error = {}, str(error)
    tables: dict[str, tuple[pd.DataFrame, dict[str, str]]] = {
        "fact_orders": _table(orders.sort_values("id_pedido", key=lambda s: s.astype(str)), ORDER_TYPES),
        "fact_hours": _table(hours.sort_values("hour_id"), HOUR_TYPES),
        "dim_hour": _table(hours.sort_values("hour_id"), SHARED_TYPES),
    }
    relationships = [("fact_orders", "hour_id", "dim_hour", "hour_id"), ("fact_hours", "hour_id", "dim_hour", "hour_id")]
    for name, column in ORDER_DIMENSIONS.items():
        values = sorted(orders[column].astype("string").fillna("Unknown").unique().tolist())
        preferred = ORDERS.get(column, [])
        values = [value for value in preferred if value in values] + [value for value in values if value not in preferred]
        tables[name] = (pd.DataFrame({column: values, "sort_order": range(len(values))}), {column: "string", "sort_order": "int64"})
        relationships.append(("fact_orders", column, name, column))
    tables["_Measures"] = (pd.DataFrame({"technical": [""]}), {"technical": "string"})
    measures = _measures(set(tables["fact_orders"][0]))
    definition = model / "definition"
    (definition / "tables").mkdir(parents=True, exist_ok=True)
    schema: dict[str, Any] = {
        "version": SCHEMA_VERSION, "tables": {}, "relationships": relationships,
        "measures": measures, "expected_metrics": _metrics(orders, hours),
        "shared_filter_table": "dim_hour", "order_only_dimensions": ORDER_DIMENSIONS,
        "load_proxy_definition": "Orders in selected calendar hours with recorded supply / recorded rider hours in those same hours; missing supply is not zero.",
    }
    for name, (frame, types) in tables.items():
        path = export / f"{name}.csv"
        frame.to_csv(path, index=False, encoding="utf-8-sig")
        key = "id_pedido" if name == "fact_orders" else "hour_id" if name in {"fact_hours", "dim_hour"} else ORDER_DIMENSIONS.get(name)
        schema["tables"][name] = {"columns": types, "rows": len(frame), "sha256": _hash(path), "primary_key": key}
        (definition / "tables" / f"{name}.tmdl").write_text(_tmdl_table(name, types, measures if name == "_Measures" else None), encoding="utf-8")
    relationship_text = []
    for index, (source, source_col, target, target_col) in enumerate(relationships):
        relationship_text += [f"relationship rel_{index:02d}", f"\tfromColumn: {source}.{source_col}", f"\ttoColumn: {target}.{target_col}", "\tfromCardinality: many", "\ttoCardinality: one", "\tcrossFilteringBehavior: oneDirection", ""]
    (definition / "relationships.tmdl").write_text("\n".join(relationship_text), encoding="utf-8")
    refs = [f"ref table {name}" for name in tables] + ["ref expression DataFolder"]
    (definition / "model.tmdl").write_text("model Model\n\tculture: en-US\n\tdefaultPowerBIDataSourceVersion: powerBI_V3\n\tsourceQueryCulture: en-US\n\n" + "\n".join(refs) + "\n", encoding="utf-8")
    # One relocatable parameter; never bake a separate absolute path into each query.
    folder = export.as_posix().replace('"', '""')
    (definition / "expressions.tmdl").write_text(f'expression DataFolder = "{folder}" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]\n', encoding="utf-8")
    (definition / "database.tmdl").write_text("database\n\tcompatibilityLevel: 1550\n", encoding="utf-8")
    _json(model / "definition.pbism", {"version": "4.2", "settings": {}})
    if not existed:
        report.mkdir(parents=True, exist_ok=True)
        _json(report / "definition.pbir", {"version": "4.0", "datasetReference": {"byPath": {"path": f"../{PROJECT}.SemanticModel"}}})
        _json(report / "report.json", {"config": json.dumps({"version": "5.43", "themeCollection": {}}), "layoutOptimization": 0, "resourcePackages": [], "sections": [{"name": "overview", "displayName": "Semantic model - author visuals in Desktop", "filters": "[]", "ordinal": 0, "visualContainers": [], "config": "{}", "displayOption": 1, "width": 1280, "height": 720}]})
    # An existing project pointer can contain authored settings and is preserved too.
    pointer = project / f"{PROJECT}.pbip"
    if not pointer.exists():
        _json(pointer, {"version": "1.0", "artifacts": [{"report": {"path": f"{PROJECT}.Report"}}], "settings": {"enableAutoRecovery": True}})
    preservation = {"existing_report": existed, "status": "preserved" if existed else "new_scaffold", "error": snapshot_error}
    if existed and snapshot_error is None:
        if before != _report_snapshot(report):
            raise RuntimeError("Existing Power BI report files changed during semantic export.")
        preservation["files_checked"] = len(before)
    elif snapshot_error:
        preservation["status"] = "preserved_unverified_read_denied"
    schema["report_preservation"] = preservation
    (export / "measures.dax").write_text("\n\n".join(f"{m['name']} = {m['expression']}" for m in measures) + "\n", encoding="utf-8")
    _json(export / "schema.json", schema)
    validation = validate_powerbi(Path(output_dir))
    _json(export / "validation.json", validation)
    return {"path": str(export), "project": str(pointer), "tables": len(tables), "measures": len(measures), "validation": validation, "report_preservation": preservation}


def _read_table(path: Path, columns: dict[str, str]) -> pd.DataFrame:
    # Explicit strings preserve leading zero identifiers and the literal segment "None".
    frame = pd.read_csv(path, dtype="string", keep_default_na=False, encoding="utf-8-sig")
    if frame.columns.tolist() != list(columns):
        raise ValueError(f"{path.name}: CSV columns differ from the schema")
    for name, kind in columns.items():
        if kind in {"double", "int64"}:
            values = pd.to_numeric(frame[name].replace("", pd.NA), errors="raise")
            frame[name] = values.astype("Int64" if kind == "int64" else "Float64")
            if np.isinf(frame[name].to_numpy(dtype=float, na_value=np.nan)).any():
                raise ValueError(f"{path.name}: non-finite numeric value")
        elif kind == "dateTime":
            pd.to_datetime(frame[name].replace("", pd.NA), format="mixed", errors="raise")
    return frame


def validate_powerbi(output_dir: Path) -> dict[str, Any]:
    """Read-only structural and arithmetic checks; never regenerates artifacts."""
    export = Path(output_dir).resolve() / "powerbi"
    errors: list[str] = []
    warnings: list[str] = []
    result: dict[str, Any] = {
        "status": "failed", "errors": errors, "warnings": warnings,
        "native_check": {"status": "blocked", "reason": "Native Power BI / Analysis Services execution is not available in this validation command. DAX and M have not been executed; Desktop open and refresh remain unverified."},
    }
    try:
        schema = json.loads((export / "schema.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        errors.append(f"Cannot read export schema: {error}")
        return result
    if schema.get("version") != SCHEMA_VERSION:
        errors.append("Unsupported export schema version")
    project = export / PROJECT
    definition = project / f"{PROJECT}.SemanticModel" / "definition"
    tables = {}
    for name, spec in schema.get("tables", {}).items():
        try:
            path = export / f"{name}.csv"
            if _hash(path) != spec["sha256"]:
                errors.append(f"{name}: source CSV hash differs from the exported canonical input")
            frame = _read_table(path, spec["columns"])
            tables[name] = frame
            if len(frame) != spec["rows"]:
                errors.append(f"{name}: row count differs from export metadata")
            key = spec.get("primary_key")
            if key and (frame[key].isna().any() or frame[key].eq("").any() or frame[key].duplicated().any()):
                errors.append(f"{name}: primary key {key} is null, empty or duplicated")
            text = (definition / "tables" / f"{name}.tmdl").read_text(encoding="utf-8")
            if not text.startswith(f"table {name}\n"):
                errors.append(f"{name}: invalid TMDL table declaration")
            declared = dict(re.findall(r"\tcolumn (\w+)\n\t\tdataType: (\w+)", text))
            if declared != spec["columns"]:
                errors.append(f"{name}: TMDL types/columns differ from the explicit schema")
            if f'DataFolder & "/{name}.csv"' not in text:
                errors.append(f"{name}: M source does not use the shared data-folder parameter")
        except (OSError, ValueError, TypeError, KeyError) as error:
            errors.append(f"{name}: {error}")
    for source, source_col, target, target_col in schema.get("relationships", []):
        if source not in tables or target not in tables:
            errors.append(f"Missing relationship table: {source} -> {target}")
            continue
        if source_col not in tables[source] or target_col not in tables[target]:
            errors.append(f"Missing relationship column: {source}.{source_col} -> {target}.{target_col}")
            continue
        if not set(tables[source][source_col].dropna()).issubset(set(tables[target][target_col].dropna())):
            errors.append(f"Unmatched relationship keys: {source}.{source_col} -> {target}.{target_col}")
        if tables[target][target_col].duplicated().any():
            errors.append(f"Duplicate one-side relationship keys: {target}.{target_col}")
    try:
        model_text = (definition / "model.tmdl").read_text(encoding="utf-8")
        refs = set(re.findall(r"^ref table (\w+)$", model_text, re.M))
        if refs != set(schema["tables"]):
            errors.append("Model table declarations differ from schema")
        relation_text = (definition / "relationships.tmdl").read_text(encoding="utf-8")
        pairs = re.findall(r"\tfromColumn: (\w+)\.(\w+)\n\ttoColumn: (\w+)\.(\w+)", relation_text)
        if set(pairs) != {tuple(r) for r in schema["relationships"]}:
            errors.append("TMDL relationships differ from schema")
        actual_measure_text = (definition / "tables" / "_Measures.tmdl").read_text(encoding="utf-8")
        definitions = re.findall(r"\tmeasure '([^']+)' = (.+)", actual_measure_text)
        expected = [(m["name"], m["expression"]) for m in schema["measures"]]
        if definitions != expected or len({name for name, _ in definitions}) != len(definitions):
            errors.append("Generated measures are missing, duplicated or differ from the source definitions")
        measure_names = {name for name, _ in definitions}
        for name, expression in definitions:
            # Remove text literals before scanning DAX references.
            expression = re.sub(r'"(?:[^"]|"")*"', '""', expression)
            for table, column in re.findall(r"\b(\w+)\[([^]]+)\]", expression):
                if table not in schema["tables"] or column not in schema["tables"][table]["columns"]:
                    errors.append(f"{name}: unresolved column {table}[{column}]")
            for referenced in re.findall(r"(?<![\w\]])\[([^]]+)\]", expression):
                if referenced not in measure_names:
                    errors.append(f"{name}: unresolved measure [{referenced}]")
        parameters = (definition / "expressions.tmdl").read_text(encoding="utf-8")
        if "expression DataFolder =" not in parameters or "ref expression DataFolder" not in model_text:
            errors.append("Missing shared M data-folder parameter")
    except (OSError, ValueError, KeyError) as error:
        errors.append(f"Semantic model structure: {error}")
    if "fact_orders" in tables and "fact_hours" in tables:
        try:
            actual = _metrics(tables["fact_orders"], tables["fact_hours"])
            checks = {}
            for name, expected in schema["expected_metrics"].items():
                value = actual.get(name)
                equal = value is None if expected is None else value is not None and math.isclose(value, expected, rel_tol=1e-10, abs_tol=1e-8)
                checks[name] = {"expected": expected, "actual": value, "passed": equal}
                if not equal:
                    errors.append(f"KPI reconciliation failed: {name}")
            result["kpi_reconciliation"] = checks
            counts = tables["fact_orders"].groupby("hour_id").size().reindex(tables["fact_hours"].hour_id, fill_value=0)
            if not np.array_equal(counts.to_numpy(), tables["fact_hours"].pedidos.to_numpy()):
                errors.append("Fact orders do not reconcile with hourly demand")
        except (KeyError, ValueError, TypeError) as error:
            errors.append(f"Arithmetic validation: {error}")
    json_files = [project / f"{PROJECT}.pbip", project / f"{PROJECT}.SemanticModel" / "definition.pbism", project / f"{PROJECT}.Report" / "definition.pbir"]
    for path in json_files:
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            errors.append(f"Project JSON {path.name}: {error}")
    report = project / f"{PROJECT}.Report"
    legacy_report = report / "report.json"
    if legacy_report.exists():
        try:
            report_json = json.loads(legacy_report.read_text(encoding="utf-8"))
            json.loads(report_json.get("config", "{}"))
            for page in report_json.get("sections", []):
                json.loads(page.get("config", "{}"))
            result["report_visual_count"] = sum(len(page.get("visualContainers", [])) for page in report_json.get("sections", []))
            if result["report_visual_count"] == 0:
                warnings.append("The PBIP report is a semantic-model scaffold with no authored visuals. Use the Streamlit report or author visuals in Power BI Desktop.")
        except (OSError, ValueError, TypeError) as error:
            warnings.append(f"Existing report preserved but could not be inspected: {error}")
    else:
        warnings.append("Existing report layout is not legacy report.json; it was preserved and its visuals were not validated.")
    warnings.append("Existing report field bindings require a native Desktop check after schema changes; report files are never rewritten by semantic regeneration.")
    result.update(status="passed" if not errors else "failed", tables=len(tables), measures=len(schema.get("measures", [])), report_preservation=schema.get("report_preservation", {}))
    return result
