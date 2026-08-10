from __future__ import annotations

from copy import deepcopy
from typing import Any, cast

from quorumgrad.aggregate import aggregate
from quorumgrad.engine import aggregate_document
from quorumgrad.model import parse_round
from quorumgrad.verify import verify_receipt


def _ratio(numerator: int, denominator: int) -> dict[str, int]:
    return {"numerator": numerator, "denominator": denominator}


def test_reference_summary_is_exact(receipt: dict[str, object]) -> None:
    summary = cast(dict[str, object], receipt["summary"])
    assert summary == {
        "clients": 11,
        "dimensions": 6,
        "trim_each_side": 2,
        "client_update_cells": 66,
        "included_per_coordinate": 7,
        "included_cells": 42,
        "excluded_cells": 24,
        "distinct_excluded_clients": 4,
        "nonzero_mean_shift_coordinates": 6,
        "nonzero_median_gap_coordinates": 0,
        "maximum_abs_mean_shift": _ratio(119, 275),
        "maximum_shift_dimension": "encoder.bias",
        "coordinate_commitment_sha256": summary["coordinate_commitment_sha256"],
    }
    assert len(str(summary["coordinate_commitment_sha256"])) == 64


def test_reference_trimmed_means_are_exact(receipt: dict[str, object]) -> None:
    coordinates = cast(list[dict[str, object]], receipt["coordinates"])
    expected = [
        _ratio(3, 25),
        _ratio(-2, 25),
        _ratio(9, 200),
        _ratio(21, 100),
        _ratio(-3, 100),
        _ratio(3, 40),
    ]
    actual = [
        cast(dict[str, object], coordinate["arithmetic"])["trimmed_mean"]
        for coordinate in coordinates
    ]
    medians = [
        cast(dict[str, object], coordinate["arithmetic"])["median"]
        for coordinate in coordinates
    ]
    assert actual == expected
    assert medians == expected


def test_reference_mean_shifts_are_exact(receipt: dict[str, object]) -> None:
    coordinates = cast(list[dict[str, object]], receipt["coordinates"])
    expected = [
        _ratio(-119, 275),
        _ratio(217, 550),
        _ratio(-441, 1100),
        _ratio(98, 275),
        _ratio(-432, 1375),
        _ratio(63, 220),
    ]
    actual = [
        cast(dict[str, object], coordinate["arithmetic"])["trimmed_minus_mean"]
        for coordinate in coordinates
    ]
    assert actual == expected


def test_each_coordinate_exposes_complete_partition(receipt: dict[str, object]) -> None:
    coordinates = cast(list[dict[str, object]], receipt["coordinates"])
    for index, coordinate in enumerate(coordinates):
        ranked = cast(list[dict[str, object]], coordinate["ranked"])
        low = cast(list[dict[str, object]], coordinate["low_excluded"])
        included = cast(list[dict[str, object]], coordinate["included"])
        high = cast(list[dict[str, object]], coordinate["high_excluded"])
        assert coordinate["index"] == index
        assert len(ranked) == 11
        assert len(low) == 2
        assert len(included) == 7
        assert len(high) == 2
        assert ranked == low + included + high
        pairs = [(int(item["value_fixed"]), str(item["client_id"])) for item in ranked]
        assert pairs == sorted(pairs)
        assert len(str(coordinate["coordinate_sha256"])) == 64


def test_reference_ledger_has_round_clients_and_coordinates(
    receipt: dict[str, object],
) -> None:
    ledger = cast(list[dict[str, object]], receipt["ledger"])
    assert len(ledger) == 18
    assert [entry["kind"] for entry in ledger] == [
        "round",
        *(["client"] * 11),
        *(["coordinate"] * 6),
    ]
    assert ledger[0]["previous_sha256"] == "0" * 64
    assert ledger[-1]["entry_sha256"] == receipt["ledger_root_sha256"]


def test_input_order_does_not_change_receipt(round_document: dict[str, Any]) -> None:
    original = aggregate_document(round_document)
    shuffled = deepcopy(round_document)
    shuffled["clients"] = list(reversed(shuffled["clients"]))
    assert aggregate_document(shuffled) == original


def test_tie_membership_is_deterministic() -> None:
    document = {
        "format": "quorumgrad.round.v1",
        "round_id": "ties",
        "scale": 1,
        "trim": 1,
        "dimensions": ["x"],
        "clients": [
            {"client_id": "d", "update": [2]},
            {"client_id": "b", "update": [0]},
            {"client_id": "c", "update": [2]},
            {"client_id": "a", "update": [0]},
        ],
    }
    receipt = aggregate_document(document)
    coordinate = cast(list[dict[str, object]], receipt["coordinates"])[0]
    assert coordinate["low_excluded"] == [{"client_id": "a", "value_fixed": 0}]
    assert coordinate["included"] == [
        {"client_id": "b", "value_fixed": 0},
        {"client_id": "c", "value_fixed": 2},
    ]
    assert coordinate["high_excluded"] == [{"client_id": "d", "value_fixed": 2}]
    arithmetic = cast(dict[str, object], coordinate["arithmetic"])
    assert arithmetic["trimmed_mean"] == _ratio(1, 1)
    assert arithmetic["median"] == _ratio(1, 1)
    verify_receipt(receipt)


def test_trim_zero_keeps_every_cell() -> None:
    document = {
        "format": "quorumgrad.round.v1",
        "round_id": "no-trim",
        "scale": 10,
        "trim": 0,
        "dimensions": ["x"],
        "clients": [
            {"client_id": "a", "update": [1]},
            {"client_id": "b", "update": [2]},
            {"client_id": "c", "update": [6]},
        ],
    }
    round_spec = parse_round(document)
    coordinates, summary = aggregate(round_spec)
    arithmetic = cast(dict[str, object], coordinates[0]["arithmetic"])
    assert coordinates[0]["low_excluded"] == []
    assert coordinates[0]["high_excluded"] == []
    assert arithmetic["mean"] == arithmetic["trimmed_mean"] == _ratio(3, 10)
    assert arithmetic["median"] == _ratio(1, 5)
    assert summary["excluded_cells"] == 0


def test_receipt_digests_are_deterministic(receipt: dict[str, object]) -> None:
    assert len(str(receipt["round_sha256"])) == 64
    assert len(str(receipt["ledger_root_sha256"])) == 64
    assert len(str(receipt["receipt_sha256"])) == 64
    assert verify_receipt(receipt) == receipt["summary"]
