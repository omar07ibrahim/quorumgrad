from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from quorumgrad.cli import main
from quorumgrad.report import render_report


def test_complete_cli_workflow(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    scenario = Path(__file__).resolve().parents[1] / "scenarios" / "sign-flip-round.json"
    receipt_path = tmp_path / "receipt.json"
    report_path = tmp_path / "report.html"

    assert main(["aggregate", str(scenario), "--output", str(receipt_path)]) == 0
    aggregate_output = capsys.readouterr().out
    assert "aggregated 11 clients / 6 dimensions / trim 2 each side" in aggregate_output
    assert "included 42 cells; excluded 24 coordinate cells" in aggregate_output

    assert main(["verify", str(receipt_path)]) == 0
    verify_output = capsys.readouterr().out
    assert "verified 6 coordinates by pairwise ranks; 42 included; 24 excluded" in verify_output

    assert main(["inspect", str(receipt_path)]) == 0
    inspect_output = capsys.readouterr().out
    assert "encoder.bias" in inspect_output
    assert "attack-negative" in inspect_output
    assert "attack-positive" in inspect_output

    assert main(["report", str(receipt_path), "--output", str(report_path)]) == 0
    report_output = capsys.readouterr().out
    assert "wrote verified report" in report_output
    assert report_path.read_text(encoding="utf-8").startswith("<!doctype html>")


@pytest.mark.parametrize("command", ["aggregate", "report"])
def test_outputs_are_exclusive(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    command: str,
    receipt: dict[str, object],
) -> None:
    output = tmp_path / "exists"
    output.write_text("keep", encoding="utf-8")
    if command == "aggregate":
        source = Path(__file__).resolve().parents[1] / "scenarios" / "sign-flip-round.json"
    else:
        source = tmp_path / "receipt.json"
        source.write_text(json.dumps(receipt), encoding="utf-8")
    assert main([command, str(source), "--output", str(output)]) == 2
    assert output.read_text(encoding="utf-8") == "keep"
    assert "refusing to replace" in capsys.readouterr().err


def test_invalid_round_returns_two(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "bad.json"
    source.write_text("{}", encoding="utf-8")
    assert main(["aggregate", str(source), "--output", str(tmp_path / "out")]) == 2
    assert "fields differ" in capsys.readouterr().err


def test_tampered_receipt_returns_two(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    receipt: dict[str, object],
) -> None:
    receipt["receipt_sha256"] = "0" * 64
    source = tmp_path / "receipt.json"
    source.write_text(json.dumps(receipt), encoding="utf-8")
    assert main(["verify", str(source)]) == 2
    assert "does not replay" in capsys.readouterr().err


def test_report_is_self_contained_and_explicit(receipt: dict[str, object]) -> None:
    report = render_report(receipt)
    assert "<script" not in report.lower()
    assert "http://" not in report
    assert "https://" not in report
    assert 'id="witnesses"' in report
    assert 'id="updates"' in report
    assert 'id="receipt"' in report
    assert "does not identify attackers" in report
    assert str(receipt["receipt_sha256"]) in report
    assert "attack-negative" in report
    assert "attack-positive" in report


def test_report_replays_before_rendering(receipt: dict[str, object]) -> None:
    receipt["ledger_root_sha256"] = "0" * 64
    with pytest.raises(Exception, match="does not replay"):
        render_report(receipt)


def test_report_has_all_coordinate_rows(receipt: dict[str, object]) -> None:
    report = render_report(receipt)
    round_doc = cast(dict[str, object], receipt["round"])
    dimensions = cast(list[str], round_doc["dimensions"])
    for dimension in dimensions:
        assert report.count(f"<h3>{dimension}</h3>") == 1
