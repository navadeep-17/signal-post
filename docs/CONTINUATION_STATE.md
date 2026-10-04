# Signalpost — Current Continuation State

Last updated: 2026-10-04 (Asia/Kolkata)

Repository state and live GitHub metadata are authoritative over chat history. Historical detail belongs in `docs/IMPLEMENTATION_LOG.md`; architecture and phase order belong in `docs/70_PLUS_IMPLEMENTATION_PLAN.md`.

## 1. Current source of truth

Repository: `navadeep-17/signal-post`

Production branch: `main`

Current production `main` SHA before this documentation reconciliation:

`7e299246c620860a13c82b20a2f24564a240e951`

That commit is documentation-only on top of Phase-A production merge `8a729036350c019e107cd68a08641f1fff6796f6`.

PR #94 `Phase A: exact-live BRREG zero-request breadth recovery` is **MERGED**.

- qualified measurement head: `a7192c4fe9f47e26fcc2a0d3b632e86a1586cfe0`
- cleaned/reconciled PR head: `d36ea6edefc58e38ad656042d93c6a409c4f02e7`
- exact-head Baseline CI: `37205694426` PASS
- merge commit: `8a729036350c019e107cd68a08641f1fff6796f6`
- post-merge Baseline CI: `37205739214` PASS
- final handoff Baseline CI on `7e299246...`: `37205977491` PASS

Open PRs #76, #78 and #84 are historical/experimental and are not the active production path.

Active implementation branch / PR: **none yet**. Phase 2 should start from current `main` after this state reconciliation.

## 2. Lifecycle state

### Phase 1 / collected-vs-emitted exact BRREG recovery

- **IMPLEMENTED:** yes
- **TESTED:** yes
- **QUALIFIED:** yes
- **MERGED:** yes
- **POST-MERGE GREEN:** yes

Phase 1 is closed.

Retained production behavior includes exact-live BRREG postal address, foundation/articles dates, Foretaksregisteret state/date, institutional sector, registered capital, VAT state/date and forced-dissolution state with exact source-path/source-row/URL/hash/canonical lineage and zero added source requests.

### Phase 2 / exact website-discovery improvement

- **IMPLEMENTED:** no new Phase-2 production strategy yet
- **TESTED:** current-main consumed baseline measured
- **QUALIFIED:** no
- **MERGED:** no
- **POST-MERGE GREEN:** not applicable

Phase 2 is the active architecture stage.

## 3. Phase-A qualification evidence retained as baseline

Second untouched qualification run `37203580574` on head `a7192c4fe9f47e26fcc2a0d3b632e86a1586cfe0`:

- exclusion union: 8,323 unique companies
- exclusion SHA: `ae5a1e78a883d75332d93bd0cd88f123e7f1a88300ee3d795067fc73c4cb2f85`
- seed: `20261103`
- fresh cohort: 100 unique, overlap 0
- cohort SHA: `4078579d4a581da0b8d56e4d03d567c4032d43e93c8bb94ee3c02b140b651e40`
- 100/100 terminal
- V8 `passed=true`
- evidence/contract/canonical/synthesis errors: 0
- logical requests: 666
- conservative charge: 1,332/2,000
- runtime: 460.916 s
- third-party cost: $0
- search API requests: 0
- artifact: `phasea-final-fresh-disjoint-100-v2`, ID `11304401011`, digest `sha256:31e12e11f2746dcf8c0b6454ab6052ab44281176363b6934889d22d57a08800b`

The earlier seed-`20261102` 100-company attempt remains a correctly failed, consumed cohort and must never be reused as fresh validation data.

## 4. Current-main Phase-2 baseline on the consumed qualification cohort

Artifact `11304401011` was re-read after Phase A closed.

Website claim status / 100:

- exact verified website: **7**
- not available: **87**
- ambiguous: **4**
- failed: **2**

Verified website sources:

- company-owned / registry-linked exact sites: 4
- deterministic legal-name `.no` exact sites: 3

External families on the same cohort:

- `external.profile_handle`: 10 claims
- `external.contact_email`: 6 claims
- `external.workforce_snapshot`: 100 claims

Interpretation: exact website reach is the dominant unlock for later contact/social/jobs/activity phases.

## 5. Phase-2 source audit decisions

### Norid organization-number domain lookup

Decision: **DROP / DO NOT IMPLEMENT**.

Reason:

- Norid's public directory does support organisation-number -> domain registrations, but the published terms prohibit commercial use and restrict use to specified contact/security/legal purposes;
- repeated lookups are rate-limited and the public page requires anti-bot confirmation;
- anonymous RDAP does not provide a replacement organisation-number domain-search path; relevant subscriber-identity search/count functions are authenticated-registrar capabilities.

This source is therefore not acceptable for Signalpost discovery under the repository's rights-safe promotion criteria.

### BRREG subunit homepage hints

Selected next screen: **exact parent-linked subunit `hjemmeside` candidates**.

Why this is materially different from prior failed domain guessing:

- production already spends the official `locations` request against `underenheter?overordnetEnhet=<org>`;
- BRREG's underunit schema includes `hjemmeside` and exact `overordnetEnhet` linkage;
- current `normalize_locations()` discards `hjemmeside`, so candidate information is already fetched but lost;
- retaining the field adds zero official-source requests;
- a subunit homepage is only a candidate, never proof;
- publication must still pass the existing exact target-company website identity gate;
- parent/subunit inheritance is not allowed merely because the relationship exists.

## 6. Precision and budget invariants

- exact organisation number remains the legal-entity anchor;
- candidate generation is never publication proof;
- parent/subsidiary/subunit relationship alone cannot authorize a website claim;
- exact-page external provenance remains mandatory;
- wrong-company publication is a hard failure;
- missing/blocked/ambiguous stays explicit;
- third-party API spend remains $0;
- no paid/search API path is active;
- at most four logical site requests/profile remains the Phase-2 production ceiling;
- any new candidate strategy must fit that ceiling by ordering/substitution, not by silently adding a fifth site request;
- fresh cohorts are reserved for promotion only after consumed-cohort transfer is meaningful.

## 7. Known rejected / do-not-repeat website-discovery paths

Do not revive without genuinely new evidence:

- guessed `.com` expansion;
- broad rule/ML legal-name candidate ranking that previously produced no net-new exact sites;
- annual-report domain hints after the prior zero-yield screen;
- Norid public lookup because rights/purpose terms are incompatible;
- provider-dependent model/search PRs #78/#84 unless Builderr explicitly resolves provider/key/budget and the $0 project constraint changes.

## 8. Exact next 1–3 actions

1. Create a Phase-2 experiment branch from the reconciled current `main` and retain `hjemmeside` in normalized exact-parent BRREG subunit/location records without publishing anything.
2. On the already-consumed seed-`20261103` 100-company cohort, measure how many currently unresolved companies expose one or more subunit homepage hints; independently fetch only a tightly bounded candidate set and apply the existing exact target-company website identity gate. Report attempted candidates, exact verified sites, ambiguous/wrong-company rejects, added site requests, runtime and cost.
3. Decision gate: PROMOTE only if the strategy adds meaningful net-new exact verified websites with zero wrong-company publications and can be integrated without exceeding four logical site requests/profile. Otherwise RETUNE/SHELVE/DROP and record the result.

## 9. NEXT

**NEXT: Phase 2 consumed-cohort screen of exact-parent BRREG subunit `hjemmeside` candidates. Retain the already-fetched field first, keep publication disabled, independently verify candidate pages against the target main entity, and do not spend a fresh cohort yet.**
