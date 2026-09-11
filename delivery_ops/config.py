"""Explicit pipeline configuration and source contracts."""
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES = {
    "orders": "Base de Pedidos (1).csv",
    "weather": "Base de Clima.xlsx",
    "events": "Base de Eventos Especiales.xlsx",
    "shifts": "Base de Turnos.xlsx",
}
STAGES = {
    "t_created_to_notify_min": "Creation to final rider notification",
    "t_notify_to_accept_min": "Rider notification to acceptance",
    "t_accept_to_pu_arrival_min": "Rider approach to pickup",
    "t_wait_at_pu_min": "Rider waiting at pickup",
    "t_last_mile_min": "Pickup to destination arrival",
}
SCHEMA_VERSION = "1.0.0"


@dataclass(frozen=True)
class Config:
    data_dir: Path = ROOT
    output_dir: Path = ROOT / "outputs"
    seed: int = 42
    bootstrap_samples: int = 500
