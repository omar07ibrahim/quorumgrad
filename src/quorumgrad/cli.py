"""Offline QuorumGrad command-line interface."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from quorumgrad.canonical import (
    MAX_RECEIPT_BYTES,
    MAX_ROUND_BYTES,
    load_json,
    pretty_json,
)
from quorumgrad.engine import aggregate_document
from quorumgrad.errors import QuorumGradError
from quorumgrad.verify import verify_receipt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="quorumgrad",
        description="Create and independently replay exact robust-aggregation receipts.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    aggregate_parser = commands.add_parser("aggregate", help="aggregate one round")
    aggregate_parser.add_argument("round", type=Path)
    aggregate_parser.add_argument("--output", type=Path, required=True)

    verify_parser = commands.add_parser("verify", help="independently replay a receipt")
    verify_parser.add_argument("receipt", type=Path)

    inspect_parser = commands.add_parser("inspect", help="print coordinate witnesses")
    inspect_parser.add_argument("receipt", type=Path)

    report_parser = commands.add_parser("report", help="write a verified HTML report")
    report_parser.add_argument("receipt", type=Path)
    report_parser.add_argument("--output", type=Path, required=True)
    return parser


def _write_new(path: Path, content: str) -> None:
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
    except FileExistsError as exc:
        raise QuorumGradError(f"refusing to replace existing file: {path}") from exc
    except OSError as exc:
        raise QuorumGradError(f"cannot write {path}") from exc


def _load_receipt(path: Path) -> dict[str, object]:
    document = load_json(path, max_bytes=MAX_RECEIPT_BYTES)
    verify_receipt(document)
    return cast(dict[str, object], document)


def _ratio_text(value: object) -> str:
    ratio = cast(dict[str, int], value)
    if ratio["denominator"] == 1:
        return str(ratio["numerator"])
    return f"{ratio['numerator']}/{ratio['denominator']}"


def _aggregate(round_path: Path, output: Path) -> None:
    document = load_json(round_path, max_bytes=MAX_ROUND_BYTES)
    receipt = aggregate_document(document)
    _write_new(output, pretty_json(receipt))
    summary = cast(dict[str, object], receipt["summary"])
    print(
        f"aggregated {summary['clients']} clients / {summary['dimensions']} dimensions / "
        f"trim {summary['trim_each_side']} each side"
    )
    print(
        f"included {summary['included_cells']} cells; "
        f"excluded {summary['excluded_cells']} coordinate cells"
    )
    print(f"round sha256       {receipt['round_sha256']}")
    print(f"coordinates sha256 {summary['coordinate_commitment_sha256']}")
    print(f"ledger root        {receipt['ledger_root_sha256']}")
    print(f"receipt sha256     {receipt['receipt_sha256']}")


def _verify(path: Path) -> None:
    receipt = _load_receipt(path)
    summary = cast(dict[str, object], receipt["summary"])
    print(
        f"verified {summary['dimensions']} coordinates by pairwise ranks; "
        f"{summary['included_cells']} included; {summary['excluded_cells']} excluded"
    )
    print(f"coordinates sha256 {summary['coordinate_commitment_sha256']}")
    print(f"ledger root        {receipt['ledger_root_sha256']}")
    print(f"receipt sha256     {receipt['receipt_sha256']}")


def _inspect(path: Path) -> None:
    receipt = _load_receipt(path)
    coordinates = cast(list[dict[str, object]], receipt["coordinates"])
    print("DIMENSION        MEAN          TRIMMED       MEDIAN        LOW / HIGH")
    print("-" * 96)
    for coordinate in coordinates:
        arithmetic = cast(dict[str, object], coordinate["arithmetic"])
        low = cast(list[dict[str, object]], coordinate["low_excluded"])
        high = cast(list[dict[str, object]], coordinate["high_excluded"])
        low_ids = ",".join(str(item["client_id"]) for item in low) or "none"
        high_ids = ",".join(str(item["client_id"]) for item in high) or "none"
        print(
            f"{coordinate['dimension']!s:<16} "
            f"{_ratio_text(arithmetic['mean']):<13} "
            f"{_ratio_text(arithmetic['trimmed_mean']):<13} "
            f"{_ratio_text(arithmetic['median']):<13} "
            f"{low_ids} / {high_ids}"
        )


def _report(path: Path, output: Path) -> None:
    from quorumgrad.report import render_report

    receipt = _load_receipt(path)
    _write_new(output, render_report(receipt))
    print(f"wrote verified report {output}")
    print(f"receipt sha256 {receipt['receipt_sha256']}")


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        if arguments.command == "aggregate":
            _aggregate(arguments.round, arguments.output)
        elif arguments.command == "verify":
            _verify(arguments.receipt)
        elif arguments.command == "inspect":
            _inspect(arguments.receipt)
        else:
            _report(arguments.receipt, arguments.output)
    except (QuorumGradError, OSError) as exc:
        print(f"quorumgrad: {exc}", file=sys.stderr)
        return 2
    return 0
