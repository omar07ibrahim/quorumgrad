from __future__ import annotations

from pathlib import Path

import pytest

from quorumgrad.canonical import (
    MAX_ROUND_BYTES,
    canonical_bytes,
    parse_json_bytes,
    pretty_json,
    sha256_value,
)
from quorumgrad.errors import ContractError


def test_duplicate_keys_are_rejected() -> None:
    with pytest.raises(ContractError, match="duplicate JSON key"):
        parse_json_bytes(b'{"format":"a","format":"b"}', max_bytes=100)


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_non_finite_constants_are_rejected(constant: str) -> None:
    with pytest.raises(ContractError, match="non-finite"):
        parse_json_bytes(f'{{"value":{constant}}}'.encode(), max_bytes=100)


def test_invalid_utf8_is_rejected() -> None:
    with pytest.raises(ContractError, match="UTF-8"):
        parse_json_bytes(b'{"x":"\xff"}', max_bytes=100)


def test_oversized_document_is_rejected() -> None:
    with pytest.raises(ContractError, match="exceeds"):
        parse_json_bytes(b"x" * (MAX_ROUND_BYTES + 1), max_bytes=MAX_ROUND_BYTES)


def test_invalid_json_is_bounded_error() -> None:
    with pytest.raises(ContractError, match="invalid JSON"):
        parse_json_bytes(b'{"x":', max_bytes=100)


def test_canonical_encoding_is_order_independent() -> None:
    left = {"b": [2, 1], "a": {"z": True}}
    right = {"a": {"z": True}, "b": [2, 1]}
    assert canonical_bytes(left) == canonical_bytes(right)
    assert sha256_value(left) == sha256_value(right)


def test_pretty_json_is_stable_and_terminated() -> None:
    rendered = pretty_json({"b": 2, "a": 1})
    assert rendered == '{\n  "a": 1,\n  "b": 2\n}\n'


def test_non_serializable_value_is_rejected() -> None:
    with pytest.raises(ContractError, match="not canonical JSON"):
        canonical_bytes({Path("x")})


def test_recursive_value_is_rejected() -> None:
    value: list[object] = []
    value.append(value)
    with pytest.raises(ContractError):
        canonical_bytes(value)
