"""Shared test helpers."""

from collections.abc import Callable
from pathlib import Path

import pytest


@pytest.fixture
def write_csv(tmp_path: Path) -> Callable[[str, str], Path]:
    """Write a small CSV (with the byte-order mark Excel adds) and return its path."""

    def write(name: str, text: str) -> Path:
        path = tmp_path / name
        path.write_text("\ufeff" + text, encoding="utf-8")
        return path

    return write
