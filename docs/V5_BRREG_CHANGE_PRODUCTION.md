# Signalpost V5 — Official BRREG Registry Changes

Updated: 2026-10-01

## Status

**Fresh production qualification: PASS.**

This milestone promotes the previously screened Brønnøysundregistrene Enhetsregister update feed into a bounded production source for dated **official registry changes**. It does not reinterpret registry events as company-authored news, social activity, hiring activity, or press releases.

## Why this source was promoted

The screen in `docs/V5_BRREG_CHANGE_SCREEN.md` showed broad exact-entity reach on the fixed 20-company comparison cohort:

- 20 / 20 companies had update history;
- 20 / 20 had an update in the previous 365 days;
- one exact-org batched request covered all 20 companies;
- unexpected organisation numbers: 0.

That justified a separate production implementation with stricter semantic and budget guards.

## Production contract

Source endpoint:

`https://data.brreg.no/enhetsregisteret/api/oppdateringer/enheter`

The production connector in `src/norway_company_agent/brreg_changes.py`:

- anchors every query and every emitted claim to the exact 9-digit organisation number;
- batches up to 100 organisations per request;
- requests `includeChanges=true`;
- uses a 365-day lookback;
- retains at most the three newest qualified events per company;
- rejects events for organisations outside the requested batch;
- preserves BRREG event id, event date, exact change paths, source URL, retrieval URL and SHA-256 evidence;
- treats transport failure as supplementary/fail-soft but treats source-attribution/schema integrity errors as hard validation failures;
- adds no paid/search/social-platform API dependency.

Only paths with a stable, source-specific interpretation are promoted. The current allowlist includes:

- latest submitted annual accounts;
- registered employee count;
- registered industry;
- business/postal address changes;
- VAT registration status/date;
- articles date;
- selected registered-capital fields.

Unknown paths remain in the source response but are not converted into evaluator-facing facts.

## Claim and canonical boundary

The evaluator-facing claim is:

- field: `official_registry_change`
- signal type: `official_registry_change`
- confidence: `1.0`
- source class: `official`

The canonical fact is:

- type: `registry_change`
- canonical field: `company.registry_change`
- category: `canonical_profile.company_record`

Registry changes are deliberately excluded from `canonical_profile.public_activity`.

The synthesis layer may use up to three dated registry changes in `what_changed` when no stronger explicit refresh diff is present. The generated text explicitly says `official BRREG registry change` and retains evidence ids. It never calls the event company-authored news.

## Request-budget design

The challenge budget remains capped at 2,000 conservative requests per 100 companies.

For a 100-company run:

- BRREG change-feed theoretical logical requests: **1**;
- conservative charge multiplier: **2**;
- reserved conservative charge: **2**;
- base runner therefore receives a maximum challenge-request budget of **1,998**;
- the combined structural ceiling remains exactly **2,000**.

The reservation is made before the base runner starts, so the new source cannot silently push a valid base run over the challenge cap.

## Fresh zero-overlap 100-company qualification

Workflow run: `36890996638`

Artifact: `v5-brreg-change-production-qualification` (`11177222419`)

Selection:

- deterministic seed: `20261008`;
- universe rows: **411,160**;
- previously touched/excluded organisations: **7,320**;
- eligible rows: **403,840**;
- selected companies: **100**;
- overlap with exclusions: **0**;
- cohort SHA-256: `a7a18aab77f9c7192ba5e55b31e5dd225718a20b6b0f6d036fb78a2a524d412d`.

End-to-end result:

- terminal companies: **100 / 100**;
- companies with a published registry-change claim: **100 / 100**;
- published registry-change claims: **156**;
- BRREG change-feed requests: **1**;
- BRREG response bytes: **463,888**;
- BRREG events received before recency/path qualification: **1,957**;
- source-integrity errors: **0**;
- evidence errors: **0**;
- output-contract errors: **0**;
- canonical validation errors: **0**;
- synthesis validation errors: **0**;
- observed conservative challenge-request charge: **1,382 / 2,000**;
- theoretical conservative challenge-request ceiling: **2,000 / 2,000**;
- wall runtime: **449.224 seconds** (~7.49 minutes);
- third-party API cost: **$0.00**;
- search API requests: **0**;
- final report `passed`: **true**.

The live response SHA-256 recorded by the runner was:

`d2e2311882ee2057d03856b671468133c6317cb96a19b6e4caf951d420c3eb59`

The qualification output SHA-256 was:

`196d22c0d27852392725c4d7c3b7a60c329aa5ae0276d014ebd5411d8cc594a4`

## Observed qualified path families

Across the 156 published events, the fresh run contained the following qualified paths:

| BRREG path | Qualified occurrences |
|---|---:|
| `/sisteInnsendteAarsregnskap` | 101 |
| `/antallAnsatte` | 28 |
| `/forretningsadresse/postnummer` | 10 |
| `/vedtektsdato` | 10 |
| `/forretningsadresse/adresse/0` | 9 |
| `/registreringsdatoMerverdiavgiftsregisteret` | 7 |
| `/registrertIMvaregisteret` | 7 |
| `/forretningsadresse/kommune` | 4 |
| `/forretningsadresse/kommunenummer` | 4 |
| `/forretningsadresse/poststed` | 4 |
| `/kapital/innfortDato` | 2 |
| `/forretningsadresse/adresse/1` | 2 |
| `/naeringskode1` | 2 |
| `/forretningsadresse/adresse/-` | 1 |
| `/kapital/belop` | 1 |
| `/postadresse/postnummer` | 1 |
| `/postadresse/adresse/1` | 1 |

A retained 50-event manual audit showed source-faithful summaries such as:

- `latest submitted annual accounts updated: 2025`;
- `registered employee count updated: 44`;
- `VAT registration date added: 2026-04-01; VAT registration status updated: True`;
- `registered industry added: Aktiviteter i borettslag og boligsameier (97.001)`;
- business-address and registered-capital updates explicitly labelled as registry changes.

No manually audited item was reclassified as company-authored public activity.

## Canonical breadth on the fresh qualification

The final fresh output contained **3,795 canonical facts**, including:

- registry changes: **156**;
- company descriptions: **100**;
- financial revenue facts: **226**;
- person-role facts: **368**;
- registered locations: **88**;
- workforce snapshots: **98**;
- social-profile facts: **3**;
- contact-email facts: **5**.

The registry-change facts increased dated currentness/change context without changing the strict first-party public-activity boundary.

## Validation and compatibility

The connector has regressions for:

- exact-org batching and request ceilings;
- unsupported-path abstention;
- lookback filtering;
- per-company event caps;
- wrong-organisation rejection;
- evidence completeness;
- idempotent projection;
- canonical category separation;
- synthesis provenance;
- legacy synthesis-shape compatibility when no V5 registry-change facts exist.

The last compatibility guard is important because the repository retains a certified V2 HTML artifact. Contracts without registry-change facts keep the pre-V5 `what_changed` object shape byte-for-byte; V5 provenance keys are added only when registry-change facts actually exist.

## What this establishes

This qualification establishes that exact-org BRREG registry changes are a high-reach, low-request, zero-paid-cost source that can improve currentness and change explanation while preserving Signalpost's precision and evidence boundaries.

It does **not** establish that Builderr will award public-activity points for these events. Builderr remains authoritative about its private matching taxonomy and total score. The correct claim is narrower: Signalpost now exposes dated, evidence-backed official registry changes for a broad fresh cohort, under the challenge's request/runtime/cost limits.
