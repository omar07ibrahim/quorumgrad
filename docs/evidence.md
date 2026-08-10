# Evidence lifecycle and reproduction

The files in this directory are generated from the real QuorumGrad CLI and the checked-in synthetic round. They are portfolio evidence, regression artifacts, and an auditable rendering contract—not hand-edited mockups.

## What is tracked

| Artifact | Source |
|---|---|
| `quorumgrad-receipt.json` | Installed CLI aggregation of the reference round |
| `quorumgrad-report.html` | Verified self-contained report renderer |
| `quorumgrad-cli.txt` | Exact aggregate, verify, inspect, and report transcript |
| Desktop, full-page, and mobile PNGs | Chromium capture of that HTML |
| CLI PNG | Chromium capture of the exact transcript |
| Three-frame GIF | Real report header, rank witnesses, and receipt sections |
| Four SVG diagrams | Derived from the receipt contract, ranks, arithmetic, and membership |
| `quorumgrad-evidence.json` | Source, toolchain, dimensions, bytes, and SHA-256 manifest |

The manifest intentionally does not hash itself. It hashes every other evidence artifact plus every declared source input.

## Reproduce through the workflow

Open a pull request that changes any evidence input. The [QuorumGrad evidence workflow](../.github/workflows/evidence.yml) will:

1. derive the exact source revision and tree;
2. execute the installed application against `scenarios/sign-flip-round.json`;
3. capture browser artifacts without network access;
4. validate image dimensions, GIF frames, SVG structure, sensitive markers, source hashes, and receipt replay;
5. commit drift back to the same repository branch as Omar Ibrahim.

A forked pull request can run read-only validation but cannot receive an evidence write. On `main`, drift fails rather than mutating the protected branch.

## Local semantic reproduction

Browser output is intentionally produced in CI because its image, architecture, browser, Python, Playwright, and Pillow versions are pinned. The semantic artifacts can be reproduced locally:

    python -m pip install .
    quorumgrad aggregate scenarios/sign-flip-round.json --output receipt.json
    quorumgrad verify receipt.json
    quorumgrad inspect receipt.json
    quorumgrad report receipt.json --output report.html

Compare the reported digests with the tracked transcript after the workflow generates the bundle.

## Pinned rendering contract

- container: `mcr.microsoft.com/playwright/python@sha256:51d31fdfacb0cff99a1a724152e34ae408d2bd4e7da310ff157450f49261cc59`
- platform: `linux/amd64`
- browser: Chromium 151.0.7922.34
- Playwright: 1.62.0
- Pillow: 12.3.0
- application Python: 3.14.6
- wheel downloader Python: 3.12.3
- browser network: disabled
- source mount: read-only

The image metadata is recorded in `requirements/evidence-browser-image.lock.json`. Python browser wheels and hashes are recorded in `requirements/evidence-browser.txt`.

## Updating evidence safely

Do not edit generated evidence by hand. Change the source, fixture, report, or generator in a focused commit and let the workflow regenerate the bundle. Review both the visual diff and manifest diff before merge.

When a visual legitimately changes, verify:

- the source revision reflects the intended source commit;
- summary counts and receipt digests changed only when semantic inputs changed;
- screenshots contain no secrets, local paths, usernames, or personal data;
- mobile and desktop text remains readable;
- diagrams still represent data present in the receipt;
- the full-page image captures every report section;
- all workflow checks pass on the post-generation branch head.

## Current reference contract

The checked-in synthetic round declares 11 clients, 6 coordinates, scale 1000, and trim 2 per side. The generated evidence must show 42 included cells, 24 explicit exclusion witnesses, an 18-entry ledger, and independent pairwise-rank replay. These values describe one synthetic fixture; they do not identify attackers, guarantee convergence, preserve privacy, or certify universal poisoning resistance.
