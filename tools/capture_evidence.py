"""Generate and verify source-bound QuorumGrad portfolio evidence."""

# ruff: noqa: E501 -- deterministic SVG, CSS, and evidence contracts stay reviewable

from __future__ import annotations

import argparse
import hashlib
import html
import json
import platform
import struct
import xml.etree.ElementTree as ET
from collections.abc import Sequence
from io import BytesIO
from pathlib import Path
from typing import Any, cast

FORMAT = "quorumgrad.evidence.v1"
EVIDENCE_DIRECTORY = Path("docs/evidence")
MANIFEST_NAME = "quorumgrad-evidence.json"
CONTAINER_IMAGE = (
    "mcr.microsoft.com/playwright/python@"
    "sha256:51d31fdfacb0cff99a1a724152e34ae408d2bd4e7da310ff157450f49261cc59"
)
EXPECTED_FILES = {
    "architecture.svg",
    "quorumgrad-cli.png",
    "quorumgrad-cli.txt",
    "quorumgrad-demo.gif",
    "quorumgrad-receipt.json",
    "quorumgrad-report-full.png",
    "quorumgrad-report-mobile.png",
    "quorumgrad-report.html",
    "quorumgrad-report.png",
    "rank-witness.svg",
    "shift-comparison.svg",
    "exclusion-map.svg",
}
MEDIA_TYPES = {
    ".gif": "image/gif",
    ".html": "text/html",
    ".json": "application/json",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".txt": "text/plain",
}
FORBIDDEN_TEXT = (
    "/home/",
    "/Users/",
    "github_pat_",
    "gho_",
    "ghp_",
    "sk-proj-",
    "BEGIN PRIVATE KEY",
    "Authorization: Bearer",
    "api.telegram.org/bot",
    "xoxb-",
    "AKIA",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)

    prepare_parser = commands.add_parser("prepare")
    prepare_parser.add_argument("--root", type=Path, required=True)
    prepare_parser.add_argument("--receipt", type=Path, required=True)
    prepare_parser.add_argument("--report", type=Path, required=True)
    prepare_parser.add_argument("--cli", type=Path, required=True)
    prepare_parser.add_argument("--output-root", type=Path, required=True)

    capture_parser = commands.add_parser("capture")
    capture_parser.add_argument("--output-root", type=Path, required=True)
    capture_parser.add_argument("--container-image", required=True)

    finalize_parser = commands.add_parser("finalize")
    finalize_parser.add_argument("--root", type=Path, required=True)
    finalize_parser.add_argument("--output-root", type=Path, required=True)
    finalize_parser.add_argument("--source-revision", required=True)
    finalize_parser.add_argument("--source-tree", required=True)
    finalize_parser.add_argument("--container-image", required=True)
    finalize_parser.add_argument("--browser", required=True)
    finalize_parser.add_argument("--playwright", required=True)
    finalize_parser.add_argument("--pillow", required=True)

    verify_parser = commands.add_parser("verify")
    verify_parser.add_argument("--root", type=Path, required=True)
    verify_parser.add_argument("--output-root", type=Path, required=True)
    verify_parser.add_argument("--source-revision", required=True)
    verify_parser.add_argument("--source-tree", required=True)
    verify_parser.add_argument("--container-image", required=True)

    visual_parser = commands.add_parser("verify-visuals")
    visual_parser.add_argument("--output-root", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    if arguments.command == "prepare":
        prepare(
            arguments.root,
            arguments.receipt,
            arguments.report,
            arguments.cli,
            arguments.output_root,
        )
    elif arguments.command == "capture":
        capture(arguments.output_root, arguments.container_image)
    elif arguments.command == "finalize":
        finalize(
            arguments.root,
            arguments.output_root,
            arguments.source_revision,
            arguments.source_tree,
            arguments.container_image,
            arguments.browser,
            arguments.playwright,
            arguments.pillow,
        )
    elif arguments.command == "verify":
        verify(
            arguments.root,
            arguments.output_root,
            arguments.source_revision,
            arguments.source_tree,
            arguments.container_image,
        )
    else:
        verify_visuals(arguments.output_root)
    return 0


def prepare(
    root: Path,
    receipt_path: Path,
    report_path: Path,
    cli_path: Path,
    output_root: Path,
) -> None:
    root = root.resolve()
    if output_root.exists():
        raise ValueError("evidence output root already exists")
    evidence = output_root / EVIDENCE_DIRECTORY
    evidence.mkdir(parents=True)

    from quorumgrad.canonical import MAX_RECEIPT_BYTES, load_json, pretty_json
    from quorumgrad.report import render_report
    from quorumgrad.verify import verify_receipt

    document = load_json(receipt_path, max_bytes=MAX_RECEIPT_BYTES)
    if not isinstance(document, dict):
        raise ValueError("evidence receipt must be an object")
    receipt = cast(dict[str, object], document)
    summary = verify_receipt(receipt)
    report = report_path.read_text(encoding="utf-8")
    if report != render_report(receipt):
        raise ValueError("CLI report differs from verified library rendering")
    cli = cli_path.read_text(encoding="utf-8")
    _reject_sensitive_text(cli)
    if not cli.startswith("$ quorumgrad aggregate round.json --output receipt.json"):
        raise ValueError("CLI transcript does not begin with the executed aggregate command")
    if str(receipt["receipt_sha256"]) not in cli:
        raise ValueError("CLI transcript does not expose the receipt digest")
    if (
        f"verified {summary['dimensions']} coordinates by pairwise ranks; "
        f"{summary['included_cells']} included; {summary['excluded_cells']} excluded" not in cli
    ):
        raise ValueError("CLI transcript does not include independent pairwise-rank replay")

    _write_text(evidence / "quorumgrad-receipt.json", pretty_json(receipt))
    _write_text(evidence / "quorumgrad-report.html", report)
    _write_text(evidence / "quorumgrad-cli.txt", cli)
    _write_text(evidence / "architecture.svg", _architecture_svg(receipt))
    _write_text(evidence / "rank-witness.svg", _rank_witness_svg(receipt))
    _write_text(evidence / "exclusion-map.svg", _exclusion_map_svg(receipt))
    _write_text(evidence / "shift-comparison.svg", _shift_comparison_svg(receipt))
    _write_text(output_root / "terminal.html", _terminal_html(cli))


def capture(output_root: Path, container_image: str) -> None:
    if container_image != CONTAINER_IMAGE:
        raise ValueError("unpinned evidence container")
    from PIL import Image
    from playwright.sync_api import sync_playwright

    evidence = output_root / EVIDENCE_DIRECTORY
    report_uri = (evidence / "quorumgrad-report.html").resolve().as_uri()
    terminal_uri = (output_root / "terminal.html").resolve().as_uri()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)

        desktop = browser.new_context(
            viewport={"width": 1440, "height": 1000},
            device_scale_factor=1,
            reduced_motion="reduce",
        )
        page = desktop.new_page()
        page.goto(report_uri, wait_until="load")
        page.screenshot(path=evidence / "quorumgrad-report.png")
        page.screenshot(path=evidence / "quorumgrad-report-full.png", full_page=True)
        desktop.close()

        mobile = browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=1,
            reduced_motion="reduce",
        )
        page = mobile.new_page()
        page.goto(report_uri, wait_until="load")
        page.screenshot(path=evidence / "quorumgrad-report-mobile.png")
        mobile.close()

        terminal = browser.new_context(
            viewport={"width": 1180, "height": 650},
            device_scale_factor=1,
            reduced_motion="reduce",
        )
        page = terminal.new_page()
        page.goto(terminal_uri, wait_until="load")
        page.screenshot(path=evidence / "quorumgrad-cli.png")
        terminal.close()

        demo = browser.new_context(
            viewport={"width": 1120, "height": 820},
            device_scale_factor=1,
            reduced_motion="reduce",
        )
        page = demo.new_page()
        page.goto(report_uri, wait_until="load")
        frames = []
        for selector in ("header", "#witnesses", "#receipt"):
            page.locator(selector).scroll_into_view_if_needed()
            image = Image.open(BytesIO(page.screenshot())).convert("RGB")
            frames.append(
                image.quantize(
                    colors=128,
                    method=Image.Quantize.MEDIANCUT,
                    dither=Image.Dither.NONE,
                )
            )
        frames[0].save(
            evidence / "quorumgrad-demo.gif",
            save_all=True,
            append_images=frames[1:],
            duration=(1400, 1700, 1700),
            loop=0,
            disposal=2,
            optimize=False,
        )
        demo.close()
        browser.close()


def finalize(
    root: Path,
    output_root: Path,
    source_revision: str,
    source_tree: str,
    container_image: str,
    browser: str,
    playwright: str,
    pillow: str,
) -> None:
    _validate_oid(source_revision, "source revision")
    _validate_oid(source_tree, "source tree")
    if container_image != CONTAINER_IMAGE:
        raise ValueError("evidence container mismatch")
    evidence = output_root / EVIDENCE_DIRECTORY
    receipt = json.loads((evidence / "quorumgrad-receipt.json").read_text(encoding="utf-8"))
    from quorumgrad.verify import verify_receipt

    summary = verify_receipt(receipt)
    manifest = {
        "format": FORMAT,
        "source_revision": source_revision,
        "source_tree": source_tree,
        "generation": {
            "container_image": container_image,
            "browser": browser,
            "playwright": playwright,
            "pillow": pillow,
            "python": platform.python_version(),
            "network": "disabled during browser capture",
            "filesystem": "read-only source mount",
        },
        "round_sha256": receipt["round_sha256"],
        "ledger_root_sha256": receipt["ledger_root_sha256"],
        "receipt_sha256": receipt["receipt_sha256"],
        "result": _result(summary),
        "sources": [_file_record(path, root) for path in _source_paths(root)],
        "files": [
            _evidence_record(path, output_root)
            for path in sorted(evidence.iterdir())
            if path.name != MANIFEST_NAME
        ],
    }
    _write_text(
        evidence / MANIFEST_NAME,
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )


def verify(
    root: Path,
    output_root: Path,
    source_revision: str,
    source_tree: str,
    container_image: str,
) -> None:
    _validate_oid(source_revision, "source revision")
    _validate_oid(source_tree, "source tree")
    evidence = output_root / EVIDENCE_DIRECTORY
    actual = {path.name for path in evidence.iterdir() if path.is_file()}
    expected = EXPECTED_FILES | {MANIFEST_NAME}
    if actual != expected:
        raise ValueError(f"evidence file set differs: {sorted(actual ^ expected)}")
    manifest = json.loads((evidence / MANIFEST_NAME).read_text(encoding="utf-8"))
    if manifest["format"] != FORMAT:
        raise ValueError("evidence format mismatch")
    if manifest["source_revision"] != source_revision or manifest["source_tree"] != source_tree:
        raise ValueError("evidence source binding mismatch")
    if manifest["generation"]["container_image"] != container_image:
        raise ValueError("evidence container mismatch")
    if manifest["generation"]["python"] != "3.14.6":
        raise ValueError("evidence Python runtime mismatch")
    if manifest["sources"] != [_file_record(path, root) for path in _source_paths(root)]:
        raise ValueError("evidence source hashes differ")
    expected_files = [
        _evidence_record(path, output_root)
        for path in sorted(evidence.iterdir())
        if path.name != MANIFEST_NAME
    ]
    if manifest["files"] != expected_files:
        raise ValueError("evidence file hashes or dimensions differ")

    from quorumgrad.canonical import MAX_RECEIPT_BYTES, load_json
    from quorumgrad.report import render_report
    from quorumgrad.verify import verify_receipt

    document = load_json(
        evidence / "quorumgrad-receipt.json",
        max_bytes=MAX_RECEIPT_BYTES,
    )
    if not isinstance(document, dict):
        raise ValueError("evidence receipt must be an object")
    receipt = cast(dict[str, object], document)
    summary = verify_receipt(receipt)
    if (evidence / "quorumgrad-report.html").read_text(encoding="utf-8") != render_report(receipt):
        raise ValueError("checked-in report does not replay")
    if manifest["result"] != _result(summary):
        raise ValueError("manifest result does not match independent replay")
    for key in ("round_sha256", "ledger_root_sha256", "receipt_sha256"):
        if manifest[key] != receipt[key]:
            raise ValueError(f"manifest {key} mismatch")

    for path in evidence.iterdir():
        if path.suffix in {".html", ".json", ".svg", ".txt"}:
            _reject_sensitive_text(path.read_text(encoding="utf-8"))
        if path.suffix == ".svg":
            _verify_svg(path)


def verify_visuals(output_root: Path) -> None:
    from PIL import Image, ImageSequence

    evidence = output_root / EVIDENCE_DIRECTORY
    expected_png = {
        "quorumgrad-report.png": (1440, 1000),
        "quorumgrad-report-mobile.png": (390, 844),
        "quorumgrad-cli.png": (1180, 650),
    }
    for name, dimensions in expected_png.items():
        with Image.open(evidence / name) as image:
            if image.format != "PNG" or image.size != dimensions:
                raise ValueError(
                    f"unexpected raster contract for {name}: {image.format} {image.size}"
                )
            _reject_blank_image(image, name)
    with Image.open(evidence / "quorumgrad-report-full.png") as image:
        if image.format != "PNG" or image.width != 1440 or image.height < 1_800:
            raise ValueError(f"unexpected full-page raster: {image.format} {image.size}")
        _reject_blank_image(image, "quorumgrad-report-full.png")
    with Image.open(evidence / "quorumgrad-demo.gif") as image:
        frames = [frame.convert("RGB") for frame in ImageSequence.Iterator(image)]
        if image.format != "GIF" or image.size != (1120, 820) or len(frames) != 3:
            raise ValueError(f"unexpected GIF contract: {image.format} {image.size} {len(frames)}")
        digests = set()
        for index, frame in enumerate(frames):
            _reject_blank_image(frame, f"quorumgrad-demo.gif frame {index}")
            digests.add(hashlib.sha256(frame.tobytes()).hexdigest())
        if len(digests) != 3:
            raise ValueError("GIF frames are not visually distinct")


def _reject_blank_image(image: Any, label: str) -> None:
    converted = image.convert("RGB")
    extrema = converted.getextrema()
    if all(low == high for low, high in extrema):
        raise ValueError(f"blank evidence image: {label}")
    colors = converted.resize((160, 100)).getcolors(maxcolors=20_000)
    if colors is None or len(colors) < 12:
        raise ValueError(f"insufficient visual detail: {label}")


def _ratio_text(value: object) -> str:
    ratio = cast(dict[str, int], value)
    if ratio["denominator"] == 1:
        return str(ratio["numerator"])
    return f"{ratio['numerator']}/{ratio['denominator']}"


def _ratio_float(value: object) -> float:
    ratio = cast(dict[str, int], value)
    return ratio["numerator"] / ratio["denominator"]


def _result(summary: dict[str, object]) -> dict[str, object]:
    keys = (
        "clients",
        "dimensions",
        "trim_each_side",
        "client_update_cells",
        "included_per_coordinate",
        "included_cells",
        "excluded_cells",
        "distinct_excluded_clients",
        "nonzero_mean_shift_coordinates",
        "nonzero_median_gap_coordinates",
        "maximum_abs_mean_shift",
        "maximum_shift_dimension",
        "coordinate_commitment_sha256",
    )
    return {key: summary[key] for key in keys}


def _architecture_svg(receipt: dict[str, object]) -> str:
    summary = cast(dict[str, object], receipt["summary"])
    ledger = cast(list[dict[str, object]], receipt["ledger"])
    stages = (
        (
            "01",
            "BOUNDED ROUND",
            f"{summary['clients']} clients · {summary['dimensions']} coordinates",
        ),
        ("02", "ANALYZER SORT", "ordered (value, client_id) pairs"),
        (
            "03",
            "RANK WITNESSES",
            f"{summary['included_cells']} included · {summary['excluded_cells']} excluded",
        ),
        ("04", "HASHED RECEIPT", f"{len(ledger)} append-only ledger entries"),
        ("05", "PAIRWISE REPLAY", "independent O(n²) rank counts"),
    )
    boxes = []
    for index, (number, title, detail) in enumerate(stages):
        x = 42 + index * 231
        stroke = "#ffb454" if index == 2 else "#65ded7"
        boxes.append(
            f"""<g transform="translate({x} 170)">
<rect width="198" height="194" rx="24" fill="#182445" stroke="{stroke}" stroke-width="2"/>
<text x="20" y="36" fill="#83eee5" font-size="13" font-weight="800">{number}</text>
<text x="20" y="79" fill="#ffffff" font-size="14" font-weight="800">{html.escape(title)}</text>
<text x="20" y="119" fill="#c7d3eb" font-size="11">{html.escape(detail)}</text>
</g>"""
        )
    arrows = "".join(
        f'<path d="M {240 + index * 231} 267 H {274 + index * 231}" stroke="#83eee5" stroke-width="3" marker-end="url(#arrow)"/>'
        for index in range(4)
    )
    round_digest = html.escape(str(receipt["round_sha256"])[:18])
    coordinate_digest = html.escape(str(summary["coordinate_commitment_sha256"])[:18])
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 530">
<defs><linearGradient id="bg" x2="1" y2="1"><stop stop-color="#0b1022"/><stop offset="1" stop-color="#253168"/></linearGradient><marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0 0L6 3L0 6Z" fill="#83eee5"/></marker></defs>
<rect width="1200" height="530" rx="28" fill="url(#bg)"/>
<text x="42" y="60" fill="#83eee5" font-size="14" font-weight="800" letter-spacing="2">QUORUMGRAD / DUAL-ALGORITHM WORKFLOW</text>
<text x="42" y="108" fill="#ffffff" font-size="34" font-weight="800">Every trimmed coordinate leaves a receipt</text>
{"".join(boxes)}{arrows}
<text x="42" y="438" fill="#b8c7e0" font-size="13">Round {round_digest}… · Coordinates {coordinate_digest}…</text>
<text x="42" y="474" fill="#e5eaf6" font-size="14">Analyzer sorting and verifier pairwise ranks share the contract—not aggregation code.</text>
</svg>
"""


def _rank_witness_svg(receipt: dict[str, object]) -> str:
    coordinates = cast(list[dict[str, object]], receipt["coordinates"])
    round_doc = cast(dict[str, object], receipt["round"])
    coordinate = coordinates[0]
    ranked = cast(list[dict[str, object]], coordinate["ranked"])
    low = cast(list[dict[str, object]], coordinate["low_excluded"])
    high = cast(list[dict[str, object]], coordinate["high_excluded"])
    low_ids = {str(item["client_id"]) for item in low}
    high_ids = {str(item["client_id"]) for item in high}
    cards = []
    for index, item in enumerate(ranked):
        client_id = str(item["client_id"])
        if client_id in low_ids:
            state, fill, stroke = "LOW", "#fff0f3", "#ef5f73"
        elif client_id in high_ids:
            state, fill, stroke = "HIGH", "#fff7e8", "#e8a23a"
        else:
            state, fill, stroke = "KEEP", "#eaf8f5", "#20a58f"
        x = 43 + index * 101
        cards.append(
            f"""<g transform="translate({x} 205)">
<rect width="88" height="205" rx="15" fill="{fill}" stroke="{stroke}" stroke-width="2"/>
<text x="44" y="28" text-anchor="middle" fill="{stroke}" font-size="10" font-weight="900">{index + 1:02d} / {state}</text>
<text x="44" y="80" text-anchor="middle" fill="#172337" font-size="18" font-weight="900">{html.escape(str(item["value_fixed"]))}</text>
<text x="44" y="104" text-anchor="middle" fill="#64748b" font-size="10">fixed units</text>
<text x="44" y="158" text-anchor="middle" fill="#334155" font-size="9" font-weight="700">{html.escape(client_id)}</text>
<text x="44" y="180" text-anchor="middle" fill="#64748b" font-size="9">rank {index}</text>
</g>"""
        )
    arithmetic = cast(dict[str, object], coordinate["arithmetic"])
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 560">
<rect width="1200" height="560" rx="28" fill="#f7f9fc"/>
<text x="43" y="58" fill="#4f6bed" font-size="14" font-weight="800" letter-spacing="2">REAL COORDINATE WITNESS / {html.escape(str(coordinate["dimension"]))}</text>
<text x="43" y="104" fill="#172337" font-size="31" font-weight="900">Total order fixes exact membership</text>
<text x="43" y="137" fill="#64748b" font-size="14">Sorted by (value_fixed, client_id) · scale {html.escape(str(round_doc["scale"]))} · trim {html.escape(str(round_doc["trim"]))} per side</text>
{"".join(cards)}
<text x="43" y="462" fill="#172337" font-size="16" font-weight="800">trimmed mean {_ratio_text(arithmetic["trimmed_mean"])} · ordinary mean {_ratio_text(arithmetic["mean"])} · median {_ratio_text(arithmetic["median"])}</text>
<text x="43" y="501" fill="#64748b" font-size="13">Client IDs are deterministic tie-breakers only; exclusion membership is not attacker identification.</text>
</svg>
"""


def _shift_comparison_svg(receipt: dict[str, object]) -> str:
    coordinates = cast(list[dict[str, object]], receipt["coordinates"])
    maximum = max(
        1e-12,
        max(
            abs(_ratio_float(cast(dict[str, object], item["arithmetic"])["trimmed_minus_mean"]))
            for item in coordinates
        ),
    )
    rows = []
    for index, coordinate in enumerate(coordinates):
        arithmetic = cast(dict[str, object], coordinate["arithmetic"])
        shift = cast(dict[str, int], arithmetic["trimmed_minus_mean"])
        magnitude = abs(_ratio_float(shift))
        width = max(2, int(430 * magnitude / maximum))
        color = "#4f6bed" if shift["numerator"] < 0 else "#20a58f"
        y = 170 + index * 65
        rows.append(
            f'<text x="48" y="{y + 5}" fill="#26344e" font-size="12" font-weight="700">{html.escape(str(coordinate["dimension"]))}</text>'
            f'<rect x="245" y="{y - 14}" width="430" height="22" rx="11" fill="#e7ebf3"/>'
            f'<rect x="245" y="{y - 14}" width="{width}" height="22" rx="11" fill="{color}"/>'
            f'<text x="695" y="{y + 5}" fill="#172337" font-size="12" font-weight="800">Δ {_ratio_text(shift)}</text>'
            f'<text x="855" y="{y + 5}" fill="#64748b" font-size="11">mean {_ratio_text(arithmetic["mean"])} → trimmed {_ratio_text(arithmetic["trimmed_mean"])}</text>'
        )
    summary = cast(dict[str, object], receipt["summary"])
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 620">
<defs><linearGradient id="shift-bg" x2="1"><stop stop-color="#f8f9fd"/><stop offset="1" stop-color="#eef9f7"/></linearGradient></defs>
<rect width="1200" height="620" rx="28" fill="url(#shift-bg)"/>
<text x="48" y="58" fill="#4f6bed" font-size="14" font-weight="800" letter-spacing="2">SOURCE-DERIVED EXACT ARITHMETIC</text>
<text x="48" y="101" fill="#172337" font-size="30" font-weight="900">Ordinary mean vs declared trimmed mean</text>
<text x="48" y="132" fill="#64748b" font-size="13">Bar length is |trimmed − mean|; printed fractions are authoritative.</text>
{"".join(rows)}
<text x="48" y="579" fill="#64748b" font-size="13">Maximum absolute shift {_ratio_text(summary["maximum_abs_mean_shift"])} at {html.escape(str(summary["maximum_shift_dimension"]))}; one synthetic round, not a convergence claim.</text>
</svg>
"""


def _exclusion_map_svg(receipt: dict[str, object]) -> str:
    round_doc = cast(dict[str, object], receipt["round"])
    clients = cast(list[dict[str, object]], round_doc["clients"])
    coordinates = cast(list[dict[str, object]], receipt["coordinates"])
    summary = cast(dict[str, object], receipt["summary"])
    client_ids = [str(client["client_id"]) for client in clients]
    headers = []
    for index, client_id in enumerate(client_ids):
        x = 260 + index * 80
        headers.append(
            f'<text x="{x}" y="157" transform="rotate(-38 {x} 157)" text-anchor="start" fill="#526176" font-size="9" font-weight="700">{html.escape(client_id)}</text>'
        )
    rows = []
    for row_index, coordinate in enumerate(coordinates):
        y = 195 + row_index * 54
        low_ids = {
            str(item["client_id"])
            for item in cast(list[dict[str, object]], coordinate["low_excluded"])
        }
        high_ids = {
            str(item["client_id"])
            for item in cast(list[dict[str, object]], coordinate["high_excluded"])
        }
        cells = []
        for column, client_id in enumerate(client_ids):
            x = 224 + column * 80
            if client_id in low_ids:
                fill, label = "#ef5f73", "L"
            elif client_id in high_ids:
                fill, label = "#e8a23a", "H"
            else:
                fill, label = "#20a58f", "·"
            cells.append(
                f'<rect x="{x}" y="{y - 18}" width="58" height="34" rx="9" fill="{fill}"/><text x="{x + 29}" y="{y + 4}" text-anchor="middle" fill="#ffffff" font-size="12" font-weight="900">{label}</text>'
            )
        rows.append(
            f'<text x="48" y="{y + 4}" fill="#26344e" font-size="12" font-weight="700">{html.escape(str(coordinate["dimension"]))}</text>{"".join(cells)}'
        )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 590">
<rect width="1200" height="590" rx="28" fill="#ffffff"/>
<text x="48" y="56" fill="#4f6bed" font-size="14" font-weight="800" letter-spacing="2">COORDINATE-BY-CLIENT MEMBERSHIP</text>
<text x="48" y="99" fill="#172337" font-size="30" font-weight="900">{summary["excluded_cells"]} excluded cells are explicit—not inferred</text>
<text x="48" y="128" fill="#64748b" font-size="13">L = low rank · H = high rank · green = included in that coordinate</text>
{"".join(headers)}{"".join(rows)}
<rect x="48" y="544" width="12" height="12" rx="4" fill="#ef5f73"/><text x="68" y="555" fill="#64748b" font-size="11">low</text>
<rect x="117" y="544" width="12" height="12" rx="4" fill="#e8a23a"/><text x="137" y="555" fill="#64748b" font-size="11">high</text>
<rect x="190" y="544" width="12" height="12" rx="4" fill="#20a58f"/><text x="210" y="555" fill="#64748b" font-size="11">included</text>
<text x="330" y="555" fill="#64748b" font-size="11">{summary["distinct_excluded_clients"]} distinct IDs appear in exclusions; membership can vary by coordinate.</text>
</svg>
"""


def _terminal_html(cli: str) -> str:
    escaped = html.escape(cli)
    return f"""<!doctype html><meta charset="utf-8"><style>
html,body{{margin:0;background:#071019;color:#dce8f2}}body{{padding:34px;font:15px/1.48 ui-monospace,SFMono-Regular,Consolas,monospace}}
.window{{border:1px solid #294158;border-radius:18px;overflow:hidden;box-shadow:0 24px 70px #0008}}
.bar{{height:46px;background:#101e2c;border-bottom:1px solid #294158;display:flex;align-items:center;padding:0 18px;gap:9px}}
.dot{{width:12px;height:12px;border-radius:50%}}.r{{background:#ff6b6b}}.y{{background:#f4d35e}}.g{{background:#52d6a6}}
pre{{margin:0;padding:24px 28px;white-space:pre-wrap;overflow-wrap:anywhere}}
</style><div class="window"><div class="bar"><i class="dot r"></i><i class="dot y"></i><i class="dot g"></i></div><pre>{escaped}</pre></div>"""


def _source_paths(root: Path) -> list[Path]:
    paths = [
        root / ".github/workflows/evidence.yml",
        root / "pyproject.toml",
        root / "requirements/evidence-browser-image.lock.json",
        root / "requirements/evidence-browser.txt",
        root / "requirements/quality.in",
        root / "requirements/quality.txt",
        root / "scenarios/sign-flip-round.json",
        root / "tools/capture_evidence.py",
    ]
    paths.extend(sorted((root / "src/quorumgrad").glob("*.py")))
    paths.append(root / "src/quorumgrad/py.typed")
    return paths


def _file_record(path: Path, root: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "path": path.relative_to(root).as_posix(),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _evidence_record(path: Path, root: Path) -> dict[str, Any]:
    record = _file_record(path, root)
    record["media_type"] = MEDIA_TYPES[path.suffix]
    if path.suffix == ".png":
        record["dimensions"] = list(_png_dimensions(path))
    elif path.suffix == ".gif":
        record["dimensions"] = list(_gif_dimensions(path))
        record["frames"] = 3
    return record


def _png_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()[:24]
    if len(data) != 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"invalid PNG: {path}")
    return struct.unpack(">II", data[16:24])


def _gif_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()[:10]
    if len(data) != 10 or data[:6] not in {b"GIF87a", b"GIF89a"}:
        raise ValueError(f"invalid GIF: {path}")
    return struct.unpack("<HH", data[6:10])


def _validate_oid(value: str, label: str) -> None:
    if len(value) != 40 or any(character not in "0123456789abcdef" for character in value):
        raise ValueError(f"invalid {label}")


def _verify_svg(path: Path) -> None:
    root = ET.parse(path).getroot()
    if not root.tag.endswith("svg") or root.get("viewBox") is None:
        raise ValueError(f"invalid SVG structure: {path}")
    if len(list(root.iter())) < 8:
        raise ValueError(f"SVG lacks detail: {path}")


def _reject_sensitive_text(value: str) -> None:
    for marker in FORBIDDEN_TEXT:
        if marker in value:
            raise ValueError(f"evidence contains forbidden marker: {marker}")


def _write_text(path: Path, value: str) -> None:
    path.write_text(value, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    raise SystemExit(main())
