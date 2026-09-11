"""Compatibility entrypoint for the canonical Power BI build; legacy files are preserved."""
from pathlib import Path
import runpy
import sys


def main() -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    sys.argv = ["delivery_ops", "validate-powerbi", *sys.argv[1:]]
    runpy.run_module("delivery_ops", run_name="__main__")


if __name__ == "__main__":
    main()
