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
