# Changelog

All notable changes to QuorumGrad are documented here. The format follows Keep a Changelog principles and the project uses Semantic Versioning.

## [Unreleased]

## [0.1.0] - 2026-08-10

### Added

- strict bounded fixed-point contract for 3–31 clients and 1–16 coordinates;
- deterministic coordinate-wise trimmed mean and median with exact rank partitions;
- reduced rational arithmetic without floating-point aggregation or verification;
- independent O(n²) pairwise-rank receipt verifier with no shared analyzer, engine, or ledger code;
- canonical SHA-256 round, coordinate, ledger, and complete receipt commitments;
- zero-runtime-dependency CLI for aggregate, verify, inspect, and self-contained HTML report;
- synthetic 66-cell sign-flip round with 42 included and 24 excluded coordinate witnesses;
- 88-test suite with 96.57% line coverage and strict static analysis;
- clean-wheel validation on exact CPython 3.11 through 3.14;
- source-bound real screenshots, four SVG diagrams, GIF demo, CLI transcript, receipt, report, and evidence manifest;
- digest-pinned networkless browser evidence workflow;
- transparent preservation of the repository’s empty 2021 RDP origin.

[Unreleased]: https://github.com/omar07ibrahim/quorumgrad/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/omar07ibrahim/quorumgrad/releases/tag/v0.1.0
