"""Independent reconciliations of canonical datasets and evidence artifacts."""
import json
from pathlib import Path
import numpy as np
import pandas as pd

from .config import STAGES, SOURCES
from .io import sha256, write_json


def validate_data(orders, hours, rider_hours, cost_records, audit, manifest, data_dir=None):
    checks = []

    def check(name, passed, observed=None, expected=None):
        checks.append({"check":name,"status":"passed" if bool(passed) else "failed","observed":observed,"expected":expected})

    check("unique_order_grain", orders.id_pedido.is_unique and orders.id_pedido.notna().all(), len(orders))
    check("order_count_matches_raw_unique_ids", len(orders)==cost_records.id_pedido.nunique(),len(orders),cost_records.id_pedido.nunique())
    check("unique_hour_grain", hours.date_hour.is_unique)
    check("full_calendar_hour_spine", len(hours)==len(pd.date_range(hours.date_hour.min(),hours.date_hour.max(),freq="h")),len(hours))
    check("order_to_hour_integrity", orders.date_hour.isin(hours.date_hour).all())
    check("hourly_demand_reconciles", hours.pedidos.sum()==len(orders),float(hours.pedidos.sum()),len(orders))
    check("recorded_cost_reconciles_to_raw", np.isclose(orders.cpo_total.sum(),cost_records.cpo.sum(),rtol=0,atol=1e-6),float(orders.cpo_total.sum()),float(cost_records.cpo.sum()))
    check("hourly_cost_reconciles",np.isclose(orders.cpo_total.sum(),hours.cpo_total.sum(),rtol=0,atol=1e-6))
    check("cost_components_reconcile_per_order", np.allclose(orders.cpo_total,orders.cpo_entrega+orders.cpo_undispatch,rtol=0,atol=1e-8))
    check("unique_rider_hour_grain",not rider_hours.duplicated(["rider_id","date_hour"]).any())
    check("rider_hour_bounds",rider_hours.rider_hours.gt(0).all() and rider_hours.rider_hours.le(1+1e-9).all())
    check("rider_hours_reconcile",np.isclose(rider_hours.rider_hours.sum(),hours.rider_hours_total.sum(),rtol=0,atol=1e-7),float(hours.rider_hours_total.sum()),float(rider_hours.rider_hours.sum()))
    check("mixed_shift_parser_loses_no_complete_timestamp",audit["shifts"]["mixed_parse_failures"]==0,audit["shifts"]["mixed_parse_failures"],0)
    check("missing_supply_has_no_throughput",hours.loc[~hours.supply_observed,"utr_proxy"].isna().all())
    valid=hours.supply_observed & hours.rider_hours_total.gt(0)
    check("hourly_throughput_arithmetic",np.allclose(hours.loc[valid,"utr_proxy"],hours.loc[valid,"pedidos"]/hours.loc[valid,"rider_hours_total"]))
    p=orders.loc[orders.process_eligible]
    elapsed=(p.rider_at_do-p.fecha_creacion).dt.total_seconds()/60
    error=(p[list(STAGES)].sum(axis=1,skipna=False)-elapsed).abs()
    check("additive_process_matches_timestamp_endpoint",error.le(1e-8).all(),float(error.max()) if len(error) else None,"<=1e-8 minute")
    check("nonnegative_complete_process_cohort",p[list(STAGES)].ge(0).all().all() and p[list(STAGES)].notna().all().all())
    check("ineligible_lateness_is_unknown",orders.loc[~orders.late_eligible,["tardio","tardio_5min","muy_tardio"]].isna().all().all())
    check("cancelled_and_pending_excluded_from_service",not orders.loc[~orders.order_status.eq("completed"),"service_eligible"].any())
    check("pre_unknown_preserved",orders.loc[orders.pre_undispatches.isna(),"pre_any"].isna().all())
    check("post_unknown_preserved",orders.loc[orders.post_undispatches.isna(),"post_any"].isna().all())
    check("affected_orders_vs_events",orders.pre_any.sum()<=orders.pre_undispatches.sum() and orders.post_any.sum()<=orders.post_undispatches.sum())
    if data_dir is not None:
        for name,filename in SOURCES.items():
            current=sha256(Path(data_dir)/filename)
            check(f"source_unchanged_{name}",current==manifest["sources"][name]["sha256"],current,manifest["sources"][name]["sha256"])
    return {"status":"passed" if all(x["status"]=="passed" for x in checks) else "failed", "checks":checks,
            "passed":sum(x["status"]=="passed" for x in checks),"failed":sum(x["status"]=="failed" for x in checks)}


def validate_outputs(output_dir:Path, data_dir=None):
    frames={name:pd.read_parquet(output_dir/f"{name}.parquet") for name in ["orders","hours","rider_hours","cost_records"]}
    audit=json.loads((output_dir/"data_audit.json").read_text(encoding="utf-8"))
    manifest=json.loads((output_dir/"manifest.json").read_text(encoding="utf-8"))
    result=validate_data(**frames,audit=audit,manifest=manifest,data_dir=data_dir)
    write_json(output_dir/"validation.json",result)
    return result


def compare_runs(first:Path, second:Path):
    checks=[]
    for name in ["orders","hours","rider_hours","cost_records"]:
        a=pd.read_parquet(first/f"{name}.parquet")
        b=pd.read_parquet(second/f"{name}.parquet")
        try:
            pd.testing.assert_frame_equal(a,b,check_exact=True)
            status="passed"
        except AssertionError:
            status="failed"
        checks.append({"artifact":name+".parquet","status":status})
    for a in sorted((first/"analysis").glob("*.csv")):
        b=second/"analysis"/a.name
        checks.append({"artifact":"analysis/"+a.name,"status":"passed" if b.exists() and sha256(a)==sha256(b) else "failed"})
    for name in ["manifest.json","data_audit.json","analysis_results.json","data_dictionary.csv"]:
        a,b=first/name,second/name
        checks.append({"artifact":name,"status":"passed" if a.exists() and b.exists() and sha256(a)==sha256(b) else "failed"})
    result={"status":"passed" if all(c["status"]=="passed" for c in checks) else "failed","checks":checks}
    write_json(first/"reproducibility.json",result)
    return result
