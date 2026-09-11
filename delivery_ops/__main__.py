"""Run with python -m delivery_ops run; all paths are project-relative by default."""
import argparse
import json
import sys
from pathlib import Path
import pandas as pd

from .config import Config, ROOT
from .io import write_json


def main(argv=None):
    parser=argparse.ArgumentParser(description="Reproducible delivery operations intelligence")
    parser.add_argument("command",choices=["run","etl","analyze","powerbi","validate-powerbi","validate","report","compare"])
    parser.add_argument("--data-dir",type=Path,default=ROOT)
    parser.add_argument("--output-dir",type=Path,default=ROOT/"outputs")
    parser.add_argument("--compare-dir",type=Path,default=ROOT/"outputs_repro")
    parser.add_argument("--seed",type=int,default=42)
    parser.add_argument("--bootstrap-samples",type=int,default=500)
    args=parser.parse_args(argv)
    cfg=Config(args.data_dir.resolve(),args.output_dir.resolve(),args.seed,args.bootstrap_samples)
    command=args.command
    result={}
    if command in ("run","etl"):
        from .data import build_data
        print("Reconstructing raw sources, orders and observed capacity...",flush=True)
        data=build_data(cfg)
        print(f"Built {len(data['orders']):,} orders and {len(data['hours']):,} calendar hours.",flush=True)
    if command in ("run","analyze","powerbi"):
        orders=pd.read_parquet(cfg.output_dir/"orders.parquet")
        hours=pd.read_parquet(cfg.output_dir/"hours.parquet")
    if command in ("run","analyze"):
        from .analysis import analyze
        print("Computing segments, uncertainty, models and evidence...",flush=True)
        result=analyze(orders,hours,cfg.output_dir,cfg.seed,cfg.bootstrap_samples)
        write_json(cfg.output_dir/"analysis_results.json",result)
    if command in ("run","powerbi"):
        from .powerbi import export_powerbi
        print("Exporting Power BI data and semantic model...",flush=True)
        powerbi=export_powerbi(orders,hours,cfg.output_dir)
        write_json(cfg.output_dir/"powerbi_status.json",powerbi)
    if command in ("run","validate","etl"):
        from .validation import validate_outputs
        validation=validate_outputs(cfg.output_dir,cfg.data_dir)
        print(f"Data validation: {validation['passed']} passed; {validation['failed']} failed.",flush=True)
        if validation["status"]!="passed":
            return 1
    if command=="validate-powerbi":
        from .powerbi import validate_powerbi
        result=validate_powerbi(cfg.output_dir)
        write_json(cfg.output_dir/"powerbi_validation.json",result)
        print(json.dumps(result,indent=2,default=str))
    if command in ("run","report"):
        from .reporting import write_reports
        print("Writing evidence-linked English reports...",flush=True)
        write_reports(cfg.output_dir,ROOT)
    if command=="compare":
        from .validation import compare_runs
        result=compare_runs(cfg.output_dir,args.compare_dir.resolve())
        print(f"Reproducibility: {result['status']}")
        return 0 if result["status"]=="passed" else 1
    print(f"Completed {command}: {cfg.output_dir}",flush=True)
    return 0


if __name__=="__main__":
    sys.exit(main())
