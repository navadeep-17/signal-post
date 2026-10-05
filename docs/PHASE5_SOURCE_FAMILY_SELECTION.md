# Phase 5 — Deterministic source/family selection

> **Superseding production note — 2026-10-05:** the early reach screen in this document was intentionally broad and included recipient-like columns that later proved semantically distinct. Production Støtteregisteret identity is stricter: only the **primary recipient organisation number** may authorize the target company. `Spesifisert mottaker` and granting-authority organisation numbers are context only. Historical 106/1000 and 88/1000 figures are therefore research-screen numbers, not production-equivalent reach. The definitive hardened actual-V8 consumed qualification is run `37254237936`: 11/100 companies, 46 typed support claims/facts, zero validation/integrity failures, artifact `11321344340`.


Date: 2026-10-04

Status: **SOURCE SELECTION COMPLETE / STØTTEREGISTERET PROMOTED TO CONSUMED-ONLY IMPLEMENTATION EXPERIMENT**

This is a source-selection result, not a production connector qualification. Candidate discovery and source overlap do not authorize publication.

## Cohort and invariants

The screen used the already-consumed certified release population only:

- companies: 1,000
- cohort: `submission/final-release-1000.jsonl`
- cohort SHA-256: `80e8f5c88b2d2facc1a00c20677a0930240f40fc75a36a27bee16c54efa2de26`
- fresh cohort consumed: **no**
- production publication enabled: **no**
- third-party API spend: **$0**

Final exact-recipient audit:

- branch: `audit/phase5-source-family-selection`
- exact head: `01efa81293af2d4363cebf23f3810d13456c4a20`
- GitHub Actions run: `37222478510` — **PASS**
- artifact: `phase5-source-family-selection`, ID `11310717600`
- artifact digest: `sha256:234dadd1134338f247f6ffaa4fa6971642dc91dd5affac608f48d1447f694906`

The harness explicitly distinguishes Støtteregisteret recipients from granting authorities, validates Norwegian organisation-number MOD-11 checksums, preserves source-file hashes, and keeps all outputs candidate-only.

## Selection matrix

| Source | Rights | Exact organisation join | Consumed reach | Family value | Freshness/access | Decision |
|---|---|---|---:|---|---|---|
| **Støtteregisteret** | Search/download distribution is open under NLOD | Exact recipient and specified-recipient organisation-number fields | **106/1,000 = 10.6%** | Dated official public-funding/activity events; amount/currency/instrument and recipient context are potentially useful | Continuously updated; public CSV/JSON search/download; full current CSV is large | **PROMOTE to consumed-only implementation experiment** |
| Doffin | Public procurement CSV is open under CC BY 4.0 | Deterministic org fields exist in exports, but the reproducible 2023 distribution exposed only `eier_orgnr` in this screen | **0/1,000** on the one reproducible annual distribution | Procurement/public activity can be useful if supplier/winner identity is available | Dataset is nominally monthly; annual download layout was not reproducible for current years in this audit | **SHELVE / RETUNE**; do not implement from the current export path |
| Patentstyret | Open Data under NLOD 2.0; source citation expected | Official `/register/v1/IprCasesByCompany` is designed for company portfolios and Norwegian companies can be keyed by organisation number | Not measured | IP applications/rights/events are dated official public activity | API requires account + subscription key/token | **SHELVE / RETUNE** until access/reproducibility is acceptable and reach is measured |

## Støtteregisteret measured result

The current full allocation CSV was downloaded from the official Støtteregisteret search/download surface and normalized from its observed UTF-16 representation before screening.

Raw source:

- raw source SHA-256: `5a10664dfc093a2914713309179349942f365fd97879bcb4cf570771ee3d1f1d`
- normalized source SHA-256: `bdf4a81425311b53c233fc08e07e8c23e7c2db441dc13a56c2aea93857a97f9d`
- rows scanned: **335,617**
- recipient-matched award rows: **661**
- unique target recipient companies: **106/1,000 = 10.6%**
- selected identity columns:
  - `Organisasjonsnummer støttemottaker`
  - `Organisasjonsnummer spesifisert støttemottaker`
- granting-authority organisation numbers: **excluded from reach**

This is meaningful company-level reach on a consumed evaluator-shaped population. The source is therefore worth one bounded implementation experiment.

### Why this is not yet a production promotion

1. The selection run proves source overlap, not final claim semantics.
2. The full CSV is roughly 291 MiB and the complete audit workflow took about six minutes. A production implementation should first determine whether exact-recipient retrieval can use a smaller deterministic search/API path or whether one shared bulk snapshot remains operationally acceptable.
3. Builderr scoring acceptance of a public-aid record must be expressed through an existing/new canonical information family without inflating generic claim count.
4. Evidence must retain the exact official source, recipient org number, award date, amount/currency and stable record identifier/URL where available.
5. Refresh semantics must distinguish a genuinely new award from source failure or snapshot drift.

## Doffin result — narrow interpretation only

The audit could reproduce only `Kunngjoringer_2023.csv` from the attempted annual download pattern:

- source SHA-256: `ec575b40fe34074d9a5e5fc49d4a53558369607a5e7486a90bc0a1930f7f1167`
- rows scanned: 5,411
- detected org field: `eier_orgnr`
- exact target companies: **0/1,000**

This is **not** evidence that Doffin has zero useful historical/current company overlap. It means the currently reproduced annual export path did not expose a useful exact target-company join for this cohort. Do not implement a connector from this narrow path without a new deterministic participant/supplier dataset or API route.

## Patentstyret result

Patentstyret remains attractive in principle:

- NLOD 2.0 open-data rights;
- company-oriented portfolio endpoint;
- organisation-number identity for many Norwegian businesses;
- dated patent/trademark/design status/event data.

However, the official developer portal requires account creation and an API subscription key. No key was configured for this audit, so company-level reach was not measured. Do not spend a fresh cohort or add production complexity until access is explicitly available and a consumed reach screen is possible.

## Decision

**PROMOTE Støtteregisteret to one consumed-only implementation experiment.**

This means:

```text
exact target organisation number
        ↓
Støtteregisteret exact recipient award
        ↓
source observation only
        ↓
canonical public-funding / dated-activity mapping
        ↓
evidence + refresh semantics
        ↓
consumed cohort comparison
        ↓
PROMOTE / RETUNE / SHELVE / DROP
```

It does **not** mean Støtteregisteret is production-qualified.

Doffin: **SHELVE / RETUNE**.

Patentstyret: **SHELVE / RETUNE pending access + reach measurement**.

## NEXT

Implement a **research-only Støtteregisteret award connector on a consumed cohort**. Preserve exact-recipient identity, publication-disabled experiment semantics, and current production output. Measure unique companies with valid dated awards, canonical-family mapping, evidence completeness, source/runtime/request cost and net-new company-family coverage. Do not consume a fresh cohort until that implementation demonstrates meaningful clean transfer on consumed data.
