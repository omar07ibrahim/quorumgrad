from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from quorumgrad.errors import ContractError
from quorumgrad.model import (
    MAX_ABS_UPDATE,
    MAX_CLIENTS,
    MAX_DIMENSIONS,
    MAX_SCALE,
    MAX_TRIM,
    parse_round,
)


def _valid() -> dict[str, Any]:
    return {
        "format": "quorumgrad.round.v1",
        "round_id": "round-a",
        "scale": 1000,
        "trim": 1,
        "dimensions": ["x", "y"],
        "clients": [
            {"client_id": "client-c", "update": [3, 30]},
            {"client_id": "client-a", "update": [1, 10]},
            {"client_id": "client-b", "update": [2, 20]},
        ],
    }


def test_round_is_normalized_by_client_id() -> None:
    parsed = parse_round(_valid())
    assert [client.client_id for client in parsed.clients] == [
        "client-a",
        "client-b",
        "client-c",
    ]
    assert parsed.dimensions == ("x", "y")
    assert parsed.to_dict()["format"] == "quorumgrad.round.v1"


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("format", "other"),
        ("round_id", "Bad ID"),
        ("scale", 0),
        ("scale", MAX_SCALE + 1),
        ("scale", True),
        ("trim", -1),
        ("trim", MAX_TRIM + 1),
        ("trim", True),
        ("dimensions", []),
        ("dimensions", "x"),
        ("clients", []),
        ("clients", "clients"),
    ],
)
def test_invalid_root_values_are_rejected(key: str, value: object) -> None:
    document = _valid()
    document[key] = value
    with pytest.raises(ContractError):
        parse_round(document)


@pytest.mark.parametrize(
    "missing",
    ["format", "round_id", "scale", "trim", "dimensions", "clients"],
)
def test_missing_root_fields_are_rejected(missing: str) -> None:
    document = _valid()
    del document[missing]
    with pytest.raises(ContractError, match="fields differ"):
        parse_round(document)


def test_extra_root_field_is_rejected() -> None:
    document = _valid()
    document["extra"] = 1
    with pytest.raises(ContractError, match="fields differ"):
        parse_round(document)


@pytest.mark.parametrize(
    "dimensions",
    [
        ["x", "x"],
        ["Bad ID"],
        [str(index) for index in range(MAX_DIMENSIONS + 1)],
        [1],
    ],
)
def test_invalid_dimensions_are_rejected(dimensions: list[object]) -> None:
    document = _valid()
    document["dimensions"] = dimensions
    with pytest.raises(ContractError):
        parse_round(document)


@pytest.mark.parametrize(
    "clients",
    [
        [{"client_id": "a", "update": [1, 2]}] * 2,
        [{"client_id": f"c-{index}", "update": [1, 2]} for index in range(MAX_CLIENTS + 1)],
    ],
)
def test_client_count_is_bounded(clients: list[dict[str, object]]) -> None:
    document = _valid()
    document["clients"] = clients
    with pytest.raises(ContractError):
        parse_round(document)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("client_id", "Bad ID"),
        ("client_id", 3),
        ("update", [1]),
        ("update", [1, 2, 3]),
        ("update", [True, 2]),
        ("update", [1.5, 2]),
        ("update", [MAX_ABS_UPDATE + 1, 2]),
        ("update", [-MAX_ABS_UPDATE - 1, 2]),
        ("update", "12"),
    ],
)
def test_invalid_client_fields_are_rejected(field: str, value: object) -> None:
    document = _valid()
    clients = deepcopy(document["clients"])
    clients[0][field] = value
    document["clients"] = clients
    with pytest.raises(ContractError):
        parse_round(document)


def test_duplicate_client_ids_are_rejected() -> None:
    document = _valid()
    clients = document["clients"]
    clients[1]["client_id"] = clients[0]["client_id"]
    with pytest.raises(ContractError, match="unique"):
        parse_round(document)


def test_client_fields_are_exact() -> None:
    document = _valid()
    document["clients"][0]["extra"] = 1
    with pytest.raises(ContractError, match="fields differ"):
        parse_round(document)


@pytest.mark.parametrize(("count", "trim"), [(3, 2), (4, 2), (5, 3)])
def test_trim_requires_a_nonempty_center(count: int, trim: int) -> None:
    document = _valid()
    document["trim"] = trim
    document["clients"] = [
        {"client_id": f"client-{index}", "update": [index, index]} for index in range(count)
    ]
    with pytest.raises(ContractError, match=r"2 \* trim"):
        parse_round(document)


def test_round_must_be_an_object() -> None:
    with pytest.raises(ContractError, match="object"):
        parse_round([])
