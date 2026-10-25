import os
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from fileorganizer.config import Config, parse_config

FIXED_NOW = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)

SAMPLE_RULES = {
    "fallback": "Unsorted",
    "ignore_suffixes": [".crdownload", ".part"],
    "rule": [
        {"name": "Invoices", "pattern": "*invoice*", "destination": "Finance/Invoices"},
        {"name": "Images", "extensions": [".jpg", ".png"], "destination": "Media/Images"},
        {
            "name": "Old installers",
            "extensions": [".exe"],
            "older_than_days": 30,
            "destination": "Archive/Installers",
        },
    ],
}


@pytest.fixture
def now() -> datetime:
    return FIXED_NOW


@pytest.fixture
def config() -> Config:
    return parse_config(SAMPLE_RULES)


@pytest.fixture
def make_file(now: datetime) -> Callable[..., Path]:
    """Create a file whose modification time is `age_days` before the fixed clock."""

    def _make(path: Path, age_days: float = 0.0) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"x")
        modified = (now - timedelta(days=age_days)).timestamp()
        os.utime(path, (modified, modified))
        return path

    return _make
