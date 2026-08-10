"""Analyzer-side coordinate-wise robust aggregation."""

from __future__ import annotations

import math
from typing import cast

from quorumgrad.canonical import sha256_value
from quorumgrad.model import AggregationRound


def _ratio(numerator: int, denominator: int) -> dict[str, int]:
    if denominator <= 0:
        raise ValueError("ratio denominator must be positive")
    divisor = math.gcd(abs(numerator), denominator)
    return {
        "numerator": numerator // divisor,
        "denominator": denominator // divisor,
    }


def _subtract(left: dict[str, int], right: dict[str, int]) -> dict[str, int]:
    numerator = (
        left["numerator"] * right["denominator"]
        - right["numerator"] * left["denominator"]
    )
    denominator = left["denominator"] * right["denominator"]
    return _ratio(numerator, denominator)


def _absolute_greater(
    left: dict[str, int],
    right: dict[str, int],
) -> bool:
    return (
        abs(left["numerator"]) * right["denominator"]
        > abs(right["numerator"]) * left["denominator"]
    )


def aggregate(
    round_spec: AggregationRound,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    """Aggregate every coordinate and retain exact rank and arithmetic witnesses."""

    coordinates: list[dict[str, object]] = []
    excluded_clients: set[str] = set()
    maximum_shift = _ratio(0, 1)
    maximum_shift_dimension = round_spec.dimensions[0]
    nonzero_mean_shifts = 0
    nonzero_median_gaps = 0
    client_count = len(round_spec.clients)

    for index, dimension in enumerate(round_spec.dimensions):
        ranked = sorted(
            (
                {
                    "client_id": client.client_id,
                    "value_fixed": client.update[index],
                }
                for client in round_spec.clients
            ),
            key=lambda item: (cast(int, item["value_fixed"]), str(item["client_id"])),
        )
        if round_spec.trim:
            low = ranked[: round_spec.trim]
            included = ranked[round_spec.trim : -round_spec.trim]
            high = ranked[-round_spec.trim :]
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
        mean_shift = _subtract(trimmed_mean, mean)
        median_gap = _subtract(trimmed_mean, median)
        if mean_shift["numerator"]:
            nonzero_mean_shifts += 1
        if median_gap["numerator"]:
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
