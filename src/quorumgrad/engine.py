"""Compose complete deterministic QuorumGrad receipts."""

from __future__ import annotations

from quorumgrad.aggregate import aggregate
from quorumgrad.canonical import sha256_value
from quorumgrad.ledger import build_ledger
from quorumgrad.model import parse_round

RECEIPT_FORMAT = "quorumgrad.receipt.v1"


def aggregate_document(document: object) -> dict[str, object]:
    """Validate one round and return its complete aggregation receipt."""

    round_spec = parse_round(document)
    coordinates, summary = aggregate(round_spec)
    ledger, root = build_ledger(round_spec, coordinates)
    core: dict[str, object] = {
        "format": RECEIPT_FORMAT,
        "round": round_spec.to_dict(),
        "round_sha256": sha256_value(round_spec.to_dict()),
        "coordinates": coordinates,
        "summary": summary,
        "ledger": ledger,
        "ledger_root_sha256": root,
    }
    return {**core, "receipt_sha256": sha256_value(core)}
