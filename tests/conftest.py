from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, cast

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from quorumgrad.engine import aggregate_document  # noqa: E402

SCENARIO = ROOT / "scenarios" / "sign-flip-round.json"


@pytest.fixture
def round_document() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(SCENARIO.read_text(encoding="utf-8")))


@pytest.fixture
def receipt(round_document: dict[str, Any]) -> dict[str, object]:
    return aggregate_document(round_document)
