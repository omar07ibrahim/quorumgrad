# Contributing to QuorumGrad

Thank you for helping make robust aggregation easier to inspect and replay.

## Development setup

Use a supported CPython version (3.11 through 3.14):

    python -m venv .venv
    . .venv/bin/activate
    python -m pip install --no-deps --require-hashes -r requirements/quality.txt
    python -m pip install --no-build-isolation --no-deps -e .

Run the complete quality gate:

    python -m ruff check .
    python -m ruff format --check .
    python -m mypy
    python -m pytest -q --cov=quorumgrad --cov-report=term-missing --cov-fail-under=92
    git diff --check

## Change expectations

- Add or update deterministic tests for behavior changes.
- Preserve strict bounds, fixed-point inputs, reduced rational outputs, and exclusive output creation.
- Keep analyzer sorting and pairwise-rank verifier implementations structurally independent.
- Do not introduce `sorted()` or analyzer, engine, or ledger imports into the verifier.
- Do not weaken canonicalization, exact-field replay, ledger integrity, or mutation rejection.
- Use synthetic fixtures only; never commit private client updates, model data, credentials, or personal data.
- State any change to the threat model or claim boundary explicitly.
- Explain user-visible changes in the changelog.
- Keep commits focused, linear, and reviewable.

## Visual evidence

Files under `docs/evidence/` are generated. Do not edit them by hand.

When a source, scenario, report, or evidence tool changes, open the pull request and let the evidence workflow regenerate the bundle. Review real screenshots, the GIF, SVG diagrams, transcript, receipt, and manifest together. A valid update must remain source-bound and independently replayable.

## Pull requests

A pull request should state:

- the problem and intended behavior;
- design or trust-boundary changes;
- tests and exact commands run;
- visual/evidence impact;
- compatibility or migration considerations.

By contributing, you agree that your contribution is licensed under Apache-2.0.
