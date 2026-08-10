"""Hash-chain round metadata, client updates, and coordinate receipts."""

from __future__ import annotations

from quorumgrad.canonical import sha256_value
from quorumgrad.model import AggregationRound


def build_ledger(
    round_spec: AggregationRound,
    coordinates: list[dict[str, object]],
) -> tuple[list[dict[str, object]], str]:
    """Build a canonical append-only ledger and return its final root."""

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
