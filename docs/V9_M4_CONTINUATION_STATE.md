# Signalpost V9 M4 Continuation State

Last updated: 2026-10-06

## Boundary

- base `main`: `72f1bf2892ec1c1e35674aa383433c9a37afdaca`
- branch: `experiment/v9-structured-contact-recovery`
- V8 qualified/submission refs are untouched
- research branch is used as evidence only; no wholesale merge
- milestone: **M4 — zero-request structured contact recovery**

## Replayed behavior

This isolated branch reimplements the measured research behavior on current production main:

- schema.org `Organization.email` / nested `ContactPoint.email`;
- schema.org `Organization.telephone`;
- each structured node must independently identify the exact target by:
  - exact target organisation number in structured identity fields; or
  - full normalized legal-name token coverage with no conflicting structured organisation number;
- email must match the already verified company website registered domain;
- telephone is accepted only after conservative Norwegian normalization to `+47XXXXXXXX`;
- arbitrary free-text JSON-LD values are not scanned;
- phone/email values never serve as legal-entity identity proof.

## Request/evidence boundary

M4 performs **zero network requests**. It operates only on the already retained exact-site snapshot and its retained schema.org nodes.

The original footer/contact email path remains unchanged and takes precedence when the same email is also present in JSON-LD.

New phone claims are projected as:

- contract field: `external.contact_phone`
- canonical field: `website.contact_phone`

All new claims retain the exact company-page source URL, retrieval time, content hash, evidence span and structured-node identity proof.

## Gate

Before any integration decision:

1. Baseline CI must pass.
2. Replay on the already-consumed frozen 1,000 retained profiles.
3. Existing email publications lost = 0.
4. Non-contact claims changed = 0.
5. Contract/canonical/synthesis errors = 0.
6. Network requests added = 0.
7. Manually audit every net-new email/phone publication.
8. Record PROMOTE / RETUNE / SHELVE / DROP.

No fresh cohort is authorized from this branch.


## Completed consumed gate

Exact tested code head before documentation-only audit commit:
`64eb9b66046f36a1c089b96e865f9bfdb3d9d425`

- Baseline CI: `37463696609` — **PASS**
- M4 frozen-1000 replay: `37463696625` — **PASS**
- artifact: `11413326913`
- artifact digest: `sha256:c6b240439a0144b0860c251da13a721e0c8fd658077782e0bddafd6c6a40ad6c`
- companies: **1000**
- contact-email companies: **53 -> 58**
- contact-phone companies: **0 -> 19**
- any-external-contact companies: **53 -> 60**
- net-new contact claims: **26**
- existing contact publications lost: **0**
- non-contact claims changed: **0**
- network requests added: **0**
- third-party cost: **$0**
- contract/canonical/synthesis errors: **0**

Manual precision audit: **26/26 reviewed, 0 wrong-company, 0 ambiguous structured-node publications**. See `docs/V9_M4_MANUAL_PRECISION_AUDIT.md`.

Decision: **PROMOTE** the narrow M4 behavior into the later integrated V9 candidate. Do not merge this standalone branch into V8/main.
