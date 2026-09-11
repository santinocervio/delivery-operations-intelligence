"""Compatibility entrypoint for the canonical Delivery Operations dashboard.

Launch: python -m streamlit run v16/dashboard_v16.py
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from delivery_ops.dashboard import main

if __name__ == "__main__":
    main()
