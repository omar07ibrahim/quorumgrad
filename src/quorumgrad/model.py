"""Strict bounded contract for one fixed-point aggregation round."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import cast

from quorumgrad.errors import ContractError

ROUND_FORMAT = "quorumgrad.round.v1"
MIN_CLIENTS = 3
MAX_CLIENTS = 31
MAX_DIMENSIONS = 16
MAX_TRIM = 10
MAX_SCALE = 10**9
MAX_ABS_UPDATE = 10**9
_NAME = re.compile(r"^[a-z][a-z0-9._-]{0,63}$")
_ROUND_KEYS = {"format", "round_id", "scale", "trim", "dimensions", "clients"}
_CLIENT_KEYS = {"client_id", "update"}


@dataclass(frozen=True, slots=True)
class ClientUpdate:
    client_id: str
    update: tuple[int, ...]

    def to_dict(self) -> dict[str, object]:
        return {"client_id": self.client_id, "update": list(self.update)}


@dataclass(frozen=True, slots=True)
class AggregationRound:
    round_id: str
    scale: int
    trim: int
    dimensions: tuple[str, ...]
    clients: tuple[ClientUpdate, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "format": ROUND_FORMAT,
            "round_id": self.round_id,
            "scale": self.scale,
            "trim": self.trim,
            "dimensions": list(self.dimensions),
            "clients": [client.to_dict() for client in self.clients],
        }


def _as_object(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ContractError(f"{label} must be an object")
    return cast(dict[str, object], value)


def _exact_keys(value: dict[str, object], expected: set[str], label: str) -> None:
    actual = set(value)
    if actual != expected:
        raise ContractError(f"{label} fields differ: {sorted(actual ^ expected)}")


def _name(value: object, label: str) -> str:
    if not isinstance(value, str) or _NAME.fullmatch(value) is None:
        raise ContractError(f"{label} must match {_NAME.pattern}")
    return value


def _bounded_int(
    value: object,
    label: str,
    *,
    minimum: int,
    maximum: int,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ContractError(f"{label} must be an integer in {minimum}..{maximum}")
    return value


def parse_round(document: object) -> AggregationRound:
    """Validate and deterministically normalize a complete aggregation round."""

    root = _as_object(document, "round")
    _exact_keys(root, _ROUND_KEYS, "round")
    if root["format"] != ROUND_FORMAT:
        raise ContractError(f"round format must be {ROUND_FORMAT}")
    round_id = _name(root["round_id"], "round_id")
    scale = _bounded_int(root["scale"], "scale", minimum=1, maximum=MAX_SCALE)
    trim = _bounded_int(root["trim"], "trim", minimum=0, maximum=MAX_TRIM)

    raw_dimensions = root["dimensions"]
    if not isinstance(raw_dimensions, list) or not 1 <= len(raw_dimensions) <= MAX_DIMENSIONS:
        raise ContractError(f"dimensions must contain 1..{MAX_DIMENSIONS} entries")
    dimensions = tuple(
        _name(value, f"dimensions[{index}]") for index, value in enumerate(raw_dimensions)
    )
    if len(set(dimensions)) != len(dimensions):
        raise ContractError("dimension names must be unique")

    raw_clients = root["clients"]
    if not isinstance(raw_clients, list) or not MIN_CLIENTS <= len(raw_clients) <= MAX_CLIENTS:
        raise ContractError(f"clients must contain {MIN_CLIENTS}..{MAX_CLIENTS} entries")
    if 2 * trim >= len(raw_clients):
        raise ContractError("trim requires 2 * trim < client count")

    clients: list[ClientUpdate] = []
    for client_index, raw_client in enumerate(raw_clients):
        client = _as_object(raw_client, f"clients[{client_index}]")
        _exact_keys(client, _CLIENT_KEYS, f"clients[{client_index}]")
        raw_update = client["update"]
        if not isinstance(raw_update, list) or len(raw_update) != len(dimensions):
            raise ContractError(
                f"clients[{client_index}].update must contain {len(dimensions)} coordinates"
            )
        update = tuple(
            _bounded_int(
                value,
                f"clients[{client_index}].update[{coordinate_index}]",
                minimum=-MAX_ABS_UPDATE,
                maximum=MAX_ABS_UPDATE,
            )
            for coordinate_index, value in enumerate(raw_update)
        )
        clients.append(
            ClientUpdate(
                client_id=_name(
                    client["client_id"],
                    f"clients[{client_index}].client_id",
                ),
                update=update,
            )
        )

    client_ids = [client.client_id for client in clients]
    if len(set(client_ids)) != len(client_ids):
        raise ContractError("client_id values must be unique")

    return AggregationRound(
        round_id=round_id,
        scale=scale,
        trim=trim,
        dimensions=dimensions,
        clients=tuple(sorted(clients, key=lambda client: client.client_id)),
    )
