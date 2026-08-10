"""Render a self-contained verified aggregation report."""

from __future__ import annotations

import html
from decimal import Decimal, localcontext
from typing import cast

from quorumgrad.verify import verify_receipt


def _escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def _ratio(value: object) -> str:
    ratio = cast(dict[str, int], value)
    numerator = ratio["numerator"]
    denominator = ratio["denominator"]
    exact = str(numerator) if denominator == 1 else f"{numerator}/{denominator}"
    with localcontext() as context:
        context.prec = 28
        decimal = format(Decimal(numerator) / Decimal(denominator), ".6f")
    decimal = decimal.rstrip("0").rstrip(".")
    return f"{_escape(exact)} <small>approx {_escape(decimal)}</small>"


def render_report(receipt: dict[str, object]) -> str:
    """Verify first, then render only canonical receipt fields."""

    summary = verify_receipt(receipt)
    round_doc = cast(dict[str, object], receipt["round"])
    clients = cast(list[dict[str, object]], round_doc["clients"])
    dimensions = cast(list[str], round_doc["dimensions"])
    coordinates = cast(list[dict[str, object]], receipt["coordinates"])

    metrics = (
        ("Clients", summary["clients"], "submitted updates"),
        ("Dimensions", summary["dimensions"], "fixed-point coordinates"),
        ("Included", summary["included_cells"], "coordinate cells"),
        ("Excluded", summary["excluded_cells"], "rank witnesses"),
    )
    metric_cards = "".join(
        f"""<article class="metric"><span>{_escape(label)}</span>
<strong>{_escape(value)}</strong><small>{_escape(note)}</small></article>"""
        for label, value, note in metrics
    )

    coordinate_rows = []
    witness_cards = []
    for coordinate in coordinates:
        arithmetic = cast(dict[str, object], coordinate["arithmetic"])
        low = cast(list[dict[str, object]], coordinate["low_excluded"])
        included = cast(list[dict[str, object]], coordinate["included"])
        high = cast(list[dict[str, object]], coordinate["high_excluded"])
        coordinate_rows.append(
            f"""<tr><td><code>{_escape(coordinate["dimension"])}</code></td>
<td>{_ratio(arithmetic["mean"])}</td>
<td>{_ratio(arithmetic["trimmed_mean"])}</td>
<td>{_ratio(arithmetic["median"])}</td>
<td>{_ratio(arithmetic["trimmed_minus_mean"])}</td>
<td><code>{_escape(coordinate["coordinate_sha256"])}</code></td></tr>"""
        )
        low_items = "".join(
            f"<li><code>{_escape(item['client_id'])}</code><b>{_escape(item['value_fixed'])}</b></li>"
            for item in low
        )
        high_items = "".join(
            f"<li><code>{_escape(item['client_id'])}</code><b>{_escape(item['value_fixed'])}</b></li>"
            for item in high
        )
        included_ids = " / ".join(_escape(item["client_id"]) for item in included)
        witness_cards.append(
            f"""<article class="witness"><div class="witness-title"><span>{_escape(coordinate["index"])}</span>
<h3>{_escape(coordinate["dimension"])}</h3></div>
<div class="rank-grid"><div><h4>Low excluded</h4><ul>{low_items}</ul></div>
<div class="center"><h4>Included ({len(included)})</h4><p>{included_ids}</p>
<strong>trimmed {_ratio(arithmetic["trimmed_mean"])}</strong></div>
<div><h4>High excluded</h4><ul>{high_items}</ul></div></div></article>"""
        )

    header_cells = "".join(f"<th>{_escape(dimension)}</th>" for dimension in dimensions)
    client_rows = []
    for client in clients:
        update = cast(list[int], client["update"])
        values = "".join(f"<td>{_escape(value)}</td>" for value in update)
        client_rows.append(f"<tr><td><code>{_escape(client['client_id'])}</code></td>{values}</tr>")

    maximum_shift = cast(dict[str, int], summary["maximum_abs_mean_shift"])
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>QuorumGrad · {_escape(round_doc["round_id"])}</title>
<style>
:root{{--ink:#172337;--muted:#64748b;--paper:#f5f7fb;--card:#fff;--night:#111827;
--blue:#4f6bed;--cyan:#20b8b0;--red:#ef5f73;--amber:#e8a23a;--green:#15806b;--line:#dfe5ef}}
*{{box-sizing:border-box}}html{{background:var(--paper);color:var(--ink);font:15px/1.5 Inter,ui-sans-serif,system-ui,-apple-system,sans-serif}}
body{{margin:0}}header{{background:radial-gradient(circle at 84% 0,#244a7e 0,transparent 40%),linear-gradient(145deg,#0b1323,#18213d);color:#fff;padding:54px max(5vw,28px) 54px}}
.eyebrow{{color:#6ee7df;font-size:12px;font-weight:800;letter-spacing:.18em;text-transform:uppercase}}
h1{{font-size:clamp(40px,6vw,74px);line-height:1;margin:14px 0 18px;letter-spacing:-.05em}}
.lead{{max-width:870px;color:#d0d9ea;font-size:18px}}.badges{{display:flex;gap:10px;flex-wrap:wrap;margin-top:26px}}
.badge{{border:1px solid #ffffff30;border-radius:99px;padding:7px 12px;background:#ffffff0d;color:#e5edf9;font-size:12px}}
main{{max-width:1240px;margin:auto;padding:32px 28px 72px}}.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-top:-72px}}
.metric{{background:var(--card);border:1px solid var(--line);box-shadow:0 18px 44px #233d5a12;border-radius:18px;padding:22px}}
.metric span,.metric small{{display:block;color:var(--muted)}}.metric strong{{display:block;font-size:36px;line-height:1.1;margin:8px 0;color:var(--night)}}
section{{background:var(--card);border:1px solid var(--line);border-radius:20px;padding:26px;margin-top:22px;overflow:hidden}}
h2{{font-size:24px;margin:0 0 6px;letter-spacing:-.02em}}.sub{{color:var(--muted);margin:0 0 22px}}
.boundary{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}.boundary section{{margin:0}}.callout{{background:#111a2e;color:#eef4ff}}
.callout .sub{{color:#bdc9dc}}.callout strong{{font-size:32px}}.callout code{{color:#75e5dd}}
.table-wrap{{overflow:auto;border:1px solid var(--line);border-radius:14px}}table{{width:100%;border-collapse:collapse;min-width:1050px}}
th,td{{padding:11px 12px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}}th{{font-size:11px;letter-spacing:.07em;text-transform:uppercase;color:var(--muted);background:#f8f9fc}}
tr:last-child td{{border-bottom:0}}code{{font:12px ui-monospace,SFMono-Regular,Consolas,monospace}}td code{{overflow-wrap:anywhere}}td small{{display:block;color:var(--muted)}}
.witnesses{{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}}.witness{{border:1px solid var(--line);border-radius:17px;padding:18px;background:#fbfcff}}
.witness-title{{display:flex;align-items:center;gap:11px}}.witness-title span{{display:grid;place-items:center;width:27px;height:27px;border-radius:8px;background:#e8ecff;color:#4058ce;font-weight:800}}
.witness h3{{margin:0;font-size:17px}}.rank-grid{{display:grid;grid-template-columns:1fr 1.4fr 1fr;gap:10px;margin-top:14px}}
.rank-grid>div{{border-radius:12px;padding:12px;background:#fff3f5}}.rank-grid>div:last-child{{background:#fff8eb}}.rank-grid .center{{background:#ebf8f5}}
.rank-grid h4{{margin:0 0 8px;font-size:11px;text-transform:uppercase;color:var(--muted)}}ul{{list-style:none;padding:0;margin:0}}li{{display:flex;justify-content:space-between;gap:8px;margin:5px 0}}
.rank-grid p{{font-size:11px;color:#526176;overflow-wrap:anywhere}}.rank-grid strong{{font-size:12px}}.rank-grid strong small{{display:block;color:var(--muted)}}
.digest{{display:grid;grid-template-columns:205px 1fr;gap:10px 18px}}.digest code{{overflow-wrap:anywhere;color:#354b69}}
footer{{color:var(--muted);font-size:12px;margin-top:24px;padding:0 6px}}
@media(max-width:900px){{header{{padding-bottom:90px}}.metrics{{grid-template-columns:repeat(2,1fr)}}.boundary,.witnesses{{grid-template-columns:1fr}}}}
@media(max-width:520px){{main{{padding:20px 14px 50px}}header{{padding:38px 18px 84px}}.metrics{{gap:9px}}.metric{{padding:15px}}.metric strong{{font-size:28px}}section{{padding:18px}}.rank-grid{{grid-template-columns:1fr}}.digest{{grid-template-columns:1fr;gap:3px}}}}
</style></head><body>
<header><div class="eyebrow">QuorumGrad / independently replayed aggregation receipt</div>
<h1>Robust aggregation,<br>with receipts.</h1>
<p class="lead">Every fixed-point coordinate exposes its total order, low and high exclusions,
included cohort, exact rational arithmetic, and content digest. A separate pairwise-rank verifier
rebuilds the result without importing the sorting analyzer.</p>
<div class="badges"><span class="badge">synthetic fixture</span>
<span class="badge">integer-only input</span><span class="badge">exact rational output</span>
<span class="badge">pairwise replay passed</span></div></header>
<main><div class="metrics">{metric_cards}</div>
<div class="boundary"><section><h2>Reference-round result</h2>
<p class="sub">The largest absolute mean-to-trimmed shift occurs at
<code>{_escape(summary["maximum_shift_dimension"])}</code>.</p>
<p><strong>{_ratio(maximum_shift)}</strong></p>
<p>{_escape(summary["distinct_excluded_clients"])} distinct client IDs appear in at least one exclusion witness.</p></section>
<section class="callout"><h2>Evidence boundary</h2><p class="sub">This report proves deterministic aggregation and replay for one declared round.
It does not identify attackers, guarantee convergence, preserve privacy, certify a federated system,
or establish universal poisoning resistance.</p><strong>{_escape(round_doc["trim"])}</strong>
<p>declared exclusions per side and coordinate</p></section></div>
<section><h2>Exact aggregation comparison</h2><p class="sub">Fractions are authoritative; decimals are display-only approximations.</p>
<div class="table-wrap"><table><thead><tr><th>Dimension</th><th>Mean</th><th>Trimmed mean</th><th>Median</th><th>Trim - mean</th><th>Coordinate digest</th></tr></thead>
<tbody>{"".join(coordinate_rows)}</tbody></table></div></section>
<section id="witnesses"><h2>Coordinate rank witnesses</h2><p class="sub">Ties are ordered by client ID for reproducible membership; equal values do not change the aggregate.</p>
<div class="witnesses">{"".join(witness_cards)}</div></section>
<section id="updates"><h2>Declared fixed-point updates</h2><p class="sub">Values are integers divided by scale {_escape(round_doc["scale"])}. Client IDs carry no trust semantics.</p>
<div class="table-wrap"><table><thead><tr><th>Client</th>{header_cells}</tr></thead>
<tbody>{"".join(client_rows)}</tbody></table></div></section>
<section id="receipt"><h2>Receipt integrity</h2><p class="sub">Canonical SHA-256 binds the normalized round, every coordinate witness, summary, and append-only ledger.</p>
<div class="digest"><strong>Round SHA-256</strong><code>{_escape(receipt["round_sha256"])}</code>
<strong>Coordinates SHA-256</strong><code>{_escape(summary["coordinate_commitment_sha256"])}</code>
<strong>Ledger root</strong><code>{_escape(receipt["ledger_root_sha256"])}</code>
<strong>Receipt SHA-256</strong><code>{_escape(receipt["receipt_sha256"])}</code></div></section>
<footer>Generated deterministically by QuorumGrad v0.1.0 · no network, model weights, dataset, or external database required.</footer>
</main></body></html>
"""
