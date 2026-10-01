# Signalpost V5 — BRREG exact-org change-feed screen

Date: 2026-10-01

Branch: `feature/v5-brreg-change-screen`

## Why this source was screened

Builderr explicitly rewards current profiles and useful synthesis of what changed. The official Brønnøysundregistrene Enhetsregister API exposes an entity-update feed at:

`GET https://data.brreg.no/enhetsregisteret/api/oppdateringer/enheter`

The official API supports:

- filtering by one or more exact `organisasjonsnummer` values;
- `includeChanges=true` to return the field changes that caused an update to be published;
- deterministic pagination/sorting;
- no personal account/API key for this open-data endpoint.

This makes the source materially different from generic web/news discovery: entity attribution is exact by organisation number and a 20-company screen can be done in one batched request.

## Comparison cohort

The screen deliberately reuses the fixed V4 source-triage cohort rather than consuming another untouched qualification cohort.

- companies: **20**
- unique organisations: **20**
- seed used when originally frozen: `20261006`
- prior exclusions at freeze time: **7,200**
- overlap at freeze time: **0**
- cohort SHA-256: `fdf402093fa87e65103c9e5b9e8d26db15b0027da4a4504deb7f575117afa5bb`

This is a source-reach comparison cohort, not a future qualification holdout.

## Screen implementation

`scripts/screen_brreg_change_feed_reach.py` batches all 20 organisation numbers into one official request:

- `organisasjonsnummer=<comma-separated exact orgs>`
- `includeChanges=true`
- `size=10000`
- `sort=id,DESC`

The screen:

1. rejects malformed organisation numbers;
2. never attributes an event whose organisation number is outside the requested set;
3. preserves official event timestamps and change paths;
4. measures both historical and recent company reach;
5. does not emit production claims;
6. explicitly labels registry events as registry changes, not company-authored news.

As-of date for the reproducible recency measurement: `2026-10-01T00:00:00Z`.

## Measured result

GitHub Actions run: `36885512441`

Artifact: `v5-brreg-change-feed-screen`

- outbound requests: **1**
- response size: **74,532 bytes**
- response SHA-256: `0ec3619769ff15c8499bdb2d981c59a21c9ed1351c98ba258f5228198a650e92`
- update events returned: **329**
- companies with any update history: **20/20 = 100%**
- companies with an update in the last 365 days: **20/20 = 100%**
- companies with an update in the last 730 days: **20/20 = 100%**
- unexpected organisation numbers in response: **0**

All 20 companies had recent official update activity. The most common explicit change path was `/sisteInnsendteAarsregnskap` (20/20), meaning the feed directly captures publication of a newer submitted-accounts state. The sample also contained explicit changes to employee counts/registration dates, addresses, industry code, VAT registration, articles date, and share-capital metadata.

Event-type counts in the screen response:

- `Endring`: 267
- `Ukjent`: 55
- `Ny`: 7

## Decision

**PROMOTE to a production experiment, with a strict source-specific fact boundary.**

The source has unusually strong properties for Signalpost:

- 100% company reach on the fixed comparison cohort;
- exact legal-entity attribution;
- official timestamps;
- structured changed-field evidence;
- one request can cover a whole 20-company screen;
- no third-party account cost;
- no website identity risk.

However, a registry update is **not** the same thing as a LinkedIn post, press release, news article, or hiring event. Production facts must be named and synthesized as **official registry changes**. They must never be presented as company-authored news.

## Production experiment boundary

The first production version should publish only structured updates whose `endringer[]` list is non-empty and whose organisation number exactly matches the target.

Recommended event representation:

- event date from BRREG `dato`;
- event ID from `oppdateringsid`;
- change type from `endringstype`;
- exact changed paths and operations from `endringer[]`;
- source URL containing the exact target organisation-number query;
- retrieval time and source-response hash;
- a conservative human-readable summary generated deterministically from known paths.

Initially prioritize interpretable paths such as:

- `/sisteInnsendteAarsregnskap`
- `/antallAnsatte`
- address paths
- `/naeringskode1`
- VAT-registration fields
- `/vedtektsdato`
- capital/share fields

Unknown paths should remain structured evidence and should not be converted to a natural-language claim until a safe label exists.

## Next gate

Do not merge registry changes into the main evaluator path from this source-screen branch. Create a separate production branch after the current V4 registry-description change is qualified/merged, then:

1. implement deterministic BRREG change-event observations/claims;
2. preserve exact source timestamp/hash/path evidence;
3. add refresh/idempotence tests using `oppdateringsid` as event identity;
4. qualify on a fresh zero-overlap 100-company cohort;
5. manually audit every published path family;
6. measure added requests and wall time;
7. only promote if no evidence/identity regressions occur.
