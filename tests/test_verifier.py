from __future__ import annotations

import inspect
from copy import deepcopy
from typing import Callable

import pytest

import quorumgrad.verify as verifier
from quorumgrad.errors import VerificationError
from quorumgrad.verify import verify_receipt

Mutation = Callable[[dict[str, object]], None]


def _set_format(receipt: dict[str, object]) -> None:
    receipt["format"] = "other"


def _set_round_hash(receipt: dict[str, object]) -> None:
    receipt["round_sha256"] = "0" * 64


def _set_coordinate_value(receipt: dict[str, object]) -> None:
    coordinates = receipt["coordinates"]
    assert isinstance(coordinates, list)
    coordinates[0]["ranked"][0]["value_fixed"] += 1


def _drop_low_witness(receipt: dict[str, object]) -> None:
    coordinates = receipt["coordinates"]
    assert isinstance(coordinates, list)
    coordinates[0]["low_excluded"].pop()


def _set_trimmed_mean(receipt: dict[str, object]) -> None:
    coordinates = receipt["coordinates"]
    assert isinstance(coordinates, list)
    coordinates[0]["arithmetic"]["trimmed_mean"]["numerator"] += 1


def _set_coordinate_hash(receipt: dict[str, object]) -> None:
    coordinates = receipt["coordinates"]
    assert isinstance(coordinates, list)
    coordinates[0]["coordinate_sha256"] = "0" * 64


def _set_summary(receipt: dict[str, object]) -> None:
    summary = receipt["summary"]
    assert isinstance(summary, dict)
    summary["included_cells"] = 0


def _set_ledger(receipt: dict[str, object]) -> None:
    ledger = receipt["ledger"]
    assert isinstance(ledger, list)
    ledger[0]["payload_sha256"] = "0" * 64


def _set_ledger_root(receipt: dict[str, object]) -> None:
    receipt["ledger_root_sha256"] = "0" * 64


def _set_receipt_hash(receipt: dict[str, object]) -> None:
    receipt["receipt_sha256"] = "0" * 64


@pytest.mark.parametrize(
    "mutation",
    [
        _set_format,
        _set_round_hash,
        _set_coordinate_value,
        _drop_low_witness,
        _set_trimmed_mean,
        _set_coordinate_hash,
        _set_summary,
        _set_ledger,
        _set_ledger_root,
        _set_receipt_hash,
    ],
)
def test_every_receipt_layer_is_replayed(
    receipt: dict[str, object],
    mutation: Mutation,
) -> None:
    changed = deepcopy(receipt)
    mutation(changed)
    with pytest.raises(VerificationError):
        verify_receipt(changed)


def test_extra_receipt_field_is_rejected(receipt: dict[str, object]) -> None:
    changed = deepcopy(receipt)
    changed["extra"] = True
    with pytest.raises(VerificationError, match="fields differ"):
        verify_receipt(changed)


def test_missing_receipt_field_is_rejected(receipt: dict[str, object]) -> None:
    changed = deepcopy(receipt)
    del changed["summary"]
    with pytest.raises(VerificationError, match="fields differ"):
        verify_receipt(changed)


@pytest.mark.parametrize("value", [None, [], "receipt", 7])
def test_receipt_must_be_an_object(value: object) -> None:
    with pytest.raises(VerificationError, match="object"):
        verify_receipt(value)


def test_invalid_embedded_round_is_bounded(receipt: dict[str, object]) -> None:
    changed = deepcopy(receipt)
    embedded = changed["round"]
    assert isinstance(embedded, dict)
    embedded["scale"] = 0
    with pytest.raises(VerificationError, match="round is invalid"):
        verify_receipt(changed)


def test_verifier_is_structurally_independent() -> None:
    source = inspect.getsource(verifier)
    assert "from quorumgrad.aggregate" not in source
    assert "from quorumgrad.engine" not in source
    assert "from quorumgrad.ledger" not in source
    assert "sorted(" not in source
    assert "_pairwise_ranks" in source


def test_pairwise_replay_matches_complete_receipt(receipt: dict[str, object]) -> None:
    assert verify_receipt(receipt) == receipt["summary"]
