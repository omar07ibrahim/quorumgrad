"""Independent pairwise-rank replay for complete QuorumGrad receipts.

This module deliberately does not import the sorting analyzer, receipt engine,
or ledger implementation. It reconstructs every public field through pairwise
rank counts and an independent hash-chain implementation.
"""

from __future__ import annotations

import math
from typing import cast

from quorumgrad.canonical import sha256_value
from quorumgrad.errors import VerificationError
from quorumgrad.model import AggregationRound, parse_round

_RECEIPT_FORMAT = "quorumgrad.receipt.v1"


def _ratio(numerator: int, denominator: int) -> dict[str, int]:
    if denominator <= 0:
        raise VerificationError("receipt arithmetic has an invalid denominator")
    divisor = math.gcd(abs(numerator), denominator)
    return {
        "numerator": numerator // divisor,
        "denominator": denominator // divisor,
    }


def _difference(left: dict[str, int], right: dict[str, int]) -> dict[str, int]:
    return _ratio(
        left["numerator"] * right["denominator"] - right["numerator"] * left["denominator"],
        left["denominator"] * right["denominator"],
    )


def _absolute_greater(left: dict[str, int], right: dict[str, int]) -> bool:
    return (
        abs(left["numerator"]) * right["denominator"]
        > abs(right["numerator"]) * left["denominator"]
    )


def _pairwise_ranks(
    round_spec: AggregationRound,
    coordinate_index: int,
) -> list[dict[str, object]]:
    items = [
        {
            "client_id": client.client_id,
            "value_fixed": client.update[coordinate_index],
        }
        for client in round_spec.clients
    ]
    by_rank: list[dict[str, object] | None] = [None] * len(items)
    for item in items:
        pair = (cast(int, item["value_fixed"]), str(item["client_id"]))
        rank = 0
        for other in items:
            other_pair = (
                cast(int, other["value_fixed"]),
                str(other["client_id"]),
            )
            if other_pair < pair:
                rank += 1
        if by_rank[rank] is not None:
            raise VerificationError("pairwise rank reconstruction is ambiguous")
        by_rank[rank] = item
    if any(item is None for item in by_rank):
        raise VerificationError("pairwise rank reconstruction is incomplete")
    return [cast(dict[str, object], item) for item in by_rank]


def _coordinates(
    round_spec: AggregationRound,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    coordinates: list[dict[str, object]] = []
    excluded_clients: set[str] = set()
    maximum_shift = _ratio(0, 1)
    maximum_shift_dimension = round_spec.dimensions[0]
    nonzero_mean_shifts = 0
    nonzero_median_gaps = 0
    client_count = len(round_spec.clients)

    for index, dimension in enumerate(round_spec.dimensions):
        ranked = _pairwise_ranks(round_spec, index)
        if round_spec.trim:
            low = ranked[: round_spec.trim]
            included = ranked[round_spec.trim : client_count - round_spec.trim]
            high = ranked[client_count - round_spec.trim :]
        else:
            low = []
            included = ranked
            high = []
        excluded_clients.update(str(item["client_id"]) for item in low + high)

        all_sum = sum(cast(int, item["value_fixed"]) for item in ranked)
        included_sum = sum(cast(int, item["value_fixed"]) for item in included)
        mean = _ratio(all_sum, client_count * round_spec.scale)
        trimmed_mean = _ratio(
            included_sum,
            len(included) * round_spec.scale,
        )
        midpoint = client_count // 2
        if client_count % 2:
            median = _ratio(
                cast(int, ranked[midpoint]["value_fixed"]),
                round_spec.scale,
            )
        else:
            median = _ratio(
                cast(int, ranked[midpoint - 1]["value_fixed"])
                + cast(int, ranked[midpoint]["value_fixed"]),
                2 * round_spec.scale,
            )
        mean_shift = _difference(trimmed_mean, mean)
        median_gap = _difference(trimmed_mean, median)
        if mean_shift["numerator"] != 0:
            nonzero_mean_shifts += 1
        if median_gap["numerator"] != 0:
            nonzero_median_gaps += 1
        if _absolute_greater(mean_shift, maximum_shift):
            maximum_shift = mean_shift
            maximum_shift_dimension = dimension

        body: dict[str, object] = {
            "dimension": dimension,
            "index": index,
            "ranked": ranked,
            "low_excluded": low,
            "included": included,
            "high_excluded": high,
            "arithmetic": {
                "all_sum_fixed": all_sum,
                "included_sum_fixed": included_sum,
                "mean": mean,
                "trimmed_mean": trimmed_mean,
                "median": median,
                "trimmed_minus_mean": mean_shift,
                "trimmed_minus_median": median_gap,
            },
        }
        coordinates.append({**body, "coordinate_sha256": sha256_value(body)})

    dimension_count = len(round_spec.dimensions)
    included_per_coordinate = client_count - 2 * round_spec.trim
    summary: dict[str, object] = {
        "clients": client_count,
        "dimensions": dimension_count,
        "trim_each_side": round_spec.trim,
        "client_update_cells": client_count * dimension_count,
        "included_per_coordinate": included_per_coordinate,
        "included_cells": included_per_coordinate * dimension_count,
        "excluded_cells": 2 * round_spec.trim * dimension_count,
        "distinct_excluded_clients": len(excluded_clients),
        "nonzero_mean_shift_coordinates": nonzero_mean_shifts,
        "nonzero_median_gap_coordinates": nonzero_median_gaps,
        "maximum_abs_mean_shift": {
            "numerator": abs(maximum_shift["numerator"]),
            "denominator": maximum_shift["denominator"],
        },
        "maximum_shift_dimension": maximum_shift_dimension,
        "coordinate_commitment_sha256": sha256_value(coordinates),
    }
    return coordinates, summary


def _ledger(
    round_spec: AggregationRound,
    coordinates: list[dict[str, object]],
) -> tuple[list[dict[str, object]], str]:
    header = {
        "format": "quorumgrad.round-header.v1",
        "round_id": round_spec.round_id,
        "scale": round_spec.scale,
        "trim": round_spec.trim,
        "dimensions": list(round_spec.dimensions),
    }
    payloads: list[tuple[str, object]] = [("round", header)]
    payloads.extend(("client", client.to_dict()) for client in round_spec.clients)
    payloads.extend(("coordinate", coordinate) for coordinate in coordinates)

    entries: list[dict[str, object]] = []
    previous = "0" * 64
    for index, (kind, payload) in enumerate(payloads):
        material: dict[str, object] = {
            "index": index,
            "kind": kind,
            "previous_sha256": previous,
            "payload_sha256": sha256_value(payload),
        }
        digest = sha256_value(material)
        entries.append({**material, "entry_sha256": digest})
        previous = digest
    return entries, previous


def verify_receipt(document: object) -> dict[str, object]:
    """Replay every receipt field and return the independently derived summary."""

    if not isinstance(document, dict):
        raise VerificationError("receipt must be an object")
    receipt = cast(dict[str, object], document)
    if receipt.get("format") != _RECEIPT_FORMAT:
        raise VerificationError(f"receipt format must be {_RECEIPT_FORMAT}")
    try:
        round_spec = parse_round(receipt["round"])
    except (KeyError, ValueError, TypeError) as exc:
        raise VerificationError("receipt round is invalid") from exc

    coordinates, summary = _coordinates(round_spec)
    ledger, root = _ledger(round_spec, coordinates)
    core: dict[str, object] = {
        "format": _RECEIPT_FORMAT,
        "round": round_spec.to_dict(),
        "round_sha256": sha256_value(round_spec.to_dict()),
        "coordinates": coordinates,
        "summary": summary,
        "ledger": ledger,
        "ledger_root_sha256": root,
    }
    expected = {**core, "receipt_sha256": sha256_value(core)}
    if set(receipt) != set(expected):
        raise VerificationError("receipt fields differ")
    for key, value in expected.items():
        if receipt[key] != value:
            raise VerificationError(f"receipt {key} does not replay")
    return summary
