# Reference scenarios

<code>sign-flip-round.json</code> is a deterministic synthetic aggregation round. It contains 11 six-coordinate fixed-point updates and requests two exclusions from each side of every coordinate.

The <code>attack-positive</code> and <code>attack-negative</code> identifiers are fixture narration only. QuorumGrad does not inspect client names, infer intent, identify Byzantine clients, or establish that every excluded update is malicious. Coordinate-wise trimming also excludes one non-attack boundary value on each side in this scenario.

The fixture demonstrates exact witness construction, rational arithmetic, analyzer/verifier agreement, and mean-versus-trimmed-mean divergence. It is not a convergence experiment, privacy result, model-quality benchmark, production attack defense, or proof that trimmed mean is universally robust.
