# QuorumGrad

QuorumGrad is a dependency-free Python laboratory for deterministic coordinate-wise trimmed-mean and median aggregation. It turns one bounded fixed-point client round into explicit rank witnesses, exact rational outputs, a hash-chain ledger, and a receipt that a structurally independent pairwise-rank implementation can replay.

## Current reference contract

- 3 to 31 client updates;
- 1 to 16 named coordinates;
- bounded integer values and an explicit fixed-point scale;
- a declared trim satisfying <code>2 * trim < clients</code>;
- total ordering by <code>(value, client_id)</code>;
- exact low, included, and high witness sets;
- canonical SHA-256 round, coordinate, ledger, and receipt commitments.

## Quick start

    python -m pip install .
    quorumgrad aggregate scenarios/sign-flip-round.json --output receipt.json
    quorumgrad verify receipt.json
    quorumgrad inspect receipt.json
    quorumgrad report receipt.json --output report.html

## Research and claim boundary

Coordinate-wise median and trimmed mean are established robust distributed-learning techniques; see [Yin et al., ICML 2018](https://proceedings.mlr.press/v80/yin18a.html). They are not universal defenses: [Xie et al., UAI 2020](https://proceedings.mlr.press/v115/xie20a.html) demonstrate attacks against Byzantine-tolerant SGD methods, and [NIST AI 100-2e2025](https://doi.org/10.6028/NIST.AI.100-2e2025) frames poisoning as one part of a broader adversarial-ML risk taxonomy.

QuorumGrad proves deterministic aggregation and replay for the declared input. It does not identify malicious clients, guarantee optimization convergence, provide secure aggregation or privacy, certify a federated-learning deployment, or defeat every poisoning strategy.

The fixture is synthetic. Client names beginning with <code>attack-</code> are narrative labels that the algorithm never interprets.

## Repository origin

The same GitHub repository was an empty repo named RDP from 2021 until its 2026 repurpose. See [PROVENANCE.md](PROVENANCE.md).
