# V7 exact-org BRREG registered contact fallback

## Decision

**KEEP / productionize.**

This milestone ports the already-qualified V6i registered-contact experiment onto the current V7 production line without changing website identity, request behavior, or the certified V1 output adapter.

## Publication semantics

The fallback publishes BRREG's literal public `epostadresse` only when all of the following hold:

- the retained registry evidence is `available`;
- `source_row_key` exactly equals the target organisation number;
- provenance is an official `https://data.brreg.no/` source;
- the registry evidence has a content hash;
- the value passes conservative email syntax validation;
- no stronger first-party/company-site contact email is already published.

The claim is labelled `official_registry_contact` on platform `brreg_registry`.

It means **public contact email registered for the exact legal entity in Brønnøysundregistrene**. It does **not** establish website ownership, email-domain ownership, mailbox control, or deliverability. It is never used as website-identity evidence.

## Immutable transfer qualification

Historical experimental head:

`f406867d9aefb43a66489f00fb7bcb4228021303`

Workflow:

`37050077407` — V6i Registry Contact Transfer Qualification

Artifact:

- name: `v6i-registry-contact-transfer`
- artifact ID: `11247086581`
- digest: `sha256:4cc753ee22ea1d0659cae988180f172593b42c82732795eb3f1e45975638370e`

Cohort:

- companies: 100
- previous organisations excluded: 7,820
- overlap: 0
- cohort SHA-256: `0e9bdfd429e2d5890bac3b23bb99da5e9951959ac9940a48a7dcf4a3979cf19b`

Observed transfer result:

| Gate | Incumbent | Registry-contact challenger |
|---|---:|---:|
| Companies with contact email | 5 | 31 |
| Net-new contact companies | — | **26** |
| Added logical requests | — | **0** |
| Added conservative request charge | — | **0** |
| Third-party API cost | — | **$0.00** |
| Wrong-company publications | — | **0** |
| Contract errors | — | **0** |
| Canonical errors | — | **0** |
| Synthesis errors | — | **0** |

All 26 V6i-owned positive claims were checked by the qualification workflow for exact-org source-row identity, official BRREG provenance, content hash, and `epostadresse=` claim span. Existing stronger contact-email coverage had zero losses.

## Current V7 integration boundary

The current production port contains only:

1. `registry_contact.py` — deterministic zero-network fallback projector;
2. one call from the existing exact-org registry projection stage after registered narrative projection;
3. permanent regressions for exact identity, source provenance, malformed values, first-party precedence, idempotence, canonical mapping, and integration.

The final V7 release qualification must remain green after this port before the submission SHA is frozen.
