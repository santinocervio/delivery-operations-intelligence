"""Compatibility entrypoint for canonical analysis; original code is in legacy/."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if __name__ == "__main__":
    from delivery_ops.__main__ import main
    raise SystemExit(main(["analyze", *sys.argv[1:]]))
