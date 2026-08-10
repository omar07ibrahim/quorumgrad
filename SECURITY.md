# Security policy

## Supported versions

| Version | Security fixes |
|---|---|
| 0.1.x | Yes |
| Earlier or untagged snapshots | No |

The latest release and the default branch receive security fixes.

## Report a vulnerability

Please use [GitHub private vulnerability reporting](https://github.com/omar07ibrahim/quorumgrad/security/advisories/new). Do not open a public issue for a suspected vulnerability and do not include credentials, private updates, model data, or personal data in a report.

Include:

- affected version or commit;
- minimal reproduction using synthetic data;
- impact and attacker prerequisites;
- suggested remediation, if known.

You should receive an acknowledgement within 72 hours. Triage and remediation timing depend on severity and reproducibility. Coordinated disclosure is preferred; please allow a fix to be prepared before publishing details.

## Security boundaries

QuorumGrad processes bounded local JSON and creates new receipt/report outputs exclusively with owner-only `0600` permissions. It performs no application-runtime network requests and has no third-party runtime dependencies. This reduces attack surface but does not authenticate clients, validate upstream updates, protect the host Python environment, provide secure aggregation, or preserve privacy.

The independent verifier establishes receipt integrity for the declared round. It does not prove that updates are truthful or that an aggregate is safe to deploy.

The evidence workflow downloads pinned inputs before browser capture; capture itself runs without networking, with a read-only source mount, dropped Linux capabilities, no privilege escalation, and resource limits.

Please rotate or revoke any credential accidentally committed to Git history even after the current tree is cleaned.
