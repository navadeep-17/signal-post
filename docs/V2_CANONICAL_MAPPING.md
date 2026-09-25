# Signalpost V2 canonical mapping

This document describes the evaluator-facing projection added after Builderr's 700-company private diagnostic. The diagnostic indicated that the previous submission returned complete company outputs but that the evaluator's canonical mapping recovered relatively little official/external information and detected no submitted data-linked product surface.

## Design rule

`claims[]` remains the source of truth. `canonical` is a deterministic projection over those already-published claims.

The projection must never:

- invent a value that is not already present in `claims[]`;
- convert `not_available`, `blocked`, `ambiguous`, `failed`, or missing into zero/false;
- create evidence independent of the original claim;
- weaken company identity checks;
- treat a generic careers page as a hiring fact.

Every canonical fact reuses the original `evidence_ids` and is hard-gated before output.

## Recovered official data that V1 was already fetching

The V2 audit found a concrete mapping loss in the Version 1 adapter. The runner already fetched the exact BRREG entity endpoint (`registry_live`) for every company, but the final output adapter did not project the normalized values from that module. This meant official facts could be fetched, charged and retained internally yet remain invisible to Builderr's canonical scorer.

V2 now projects these already-fetched live BRREG values when the same field is not already available from the frozen bulk row:

- legal name;
- legal form;
- employee count;
- municipality from the business address;
- primary industry code and label;
- business address;
- postal address;
- bankruptcy flag;
- liquidation flag;
- latest submitted accounts year.

This adds **zero network requests**. It also preserves the existing exact-company bulk value whenever that value is already published, so the live projection acts as a recovery/fallback layer rather than silently replacing certified facts.

The audit also found a separate bulk-normalization mismatch: `sampling.normalize_row()` preserved `industry_code` and `industry_label`, while the output adapter expected `profile["industry"]`. V2 retains the existing scalar keys used by sampling strata and additionally carries an output-ready structured `industry` value. That gives the bulk registry path a zero-network industry fallback if the live endpoint is unavailable.

Importantly, the `website` field present in the live BRREG entity record is **not** promoted directly to `official_website`. Website publication still goes through the existing independent identity-verification gate.

## Canonical families

| Existing claim | Canonical field/family |
|---|---|
| `legal_name` | `company.legal_name` |
| `legal_form` | `company.legal_form` |
| `municipality` | `company.municipality` |
| `industry` | `company.industry` |
| `employee_count` | `company.employee_count` |
| `business_address` | `company.business_address` |
| `postal_address` | `company.postal_address` |
| `bankrupt` | `company.bankrupt` |
| `liquidating` | `company.liquidating` |
| `group_structure` | `company.group_structure` |
| `latest_submitted_accounts` | `accounts.latest_submitted` |
| `accounting_obligation` | `accounts.accounting_obligation` |
| `financial.revenue` | `accounts.revenue` |
| `financial.operating_result` | `accounts.operating_result` |
| `financial.profit_before_tax` | `accounts.profit_before_tax` |
| `financial.annual_result` | `accounts.annual_result` |
| `financial.assets` | `accounts.assets` |
| `financial.equity` | `accounts.equity` |
| `financial.debt` | `accounts.debt` |
| `roles` | individual `people.role` facts when the value contains a list |
| `locations` | individual `locations.location` facts when the value contains a list |
| `external.workforce_snapshot` | `workforce.snapshot` |
| `official_website` | `web.official_website` |
| `company_description` | `web.company_description` |
| `external.contact_email` | `web.contact_email` |
| `external.profile_handle` | `web.social_profile` |

The canonical object also contains explicit `hiring: []` and `public_activity: []` arrays. Those remain empty until a concrete, evidence-backed fact is available. In particular, a generic careers page is not enough to populate `hiring`.

## Product surface

`scripts/run_signalpost_v2.py` is the V2 one-command wrapper. It:

1. runs the existing bounded production collector;
2. requires every output row to contain the canonical projection;
3. builds a static evidence workspace directly from that same JSONL.

Example:

```bash
uv run python scripts/run_signalpost_v2.py \
  --organisations evaluator-100.jsonl \
  --bulk brreg-enheter.csv \
  --output out/final-output.jsonl \
  --product-output out/signalpost.html \
  --report out/final-report.json \
  --work-dir out/final-work \
  --run-id builderr-v2-001 \
  --expected-count 100 \
  --workers 8 \
  --site-timeout 6 \
  --wikidata-timeout 8 \
  --max-challenge-requests 2000 \
  --max-third-party-cost-usd 0 \
  --max-wall-runtime-seconds 2400 \
  --annual-workforce-workers 4 \
  --annual-workforce-timeout 60 \
  --annual-workforce-min-start-interval 2.1 \
  --annual-workforce-ocr-pages 8 \
  --annual-workforce-ocr-dpi 110
```

The HTML is self-contained and can be opened directly or served as a static file. It is generated from the exact evaluator output, not from a separate demo dataset.

For reviewer visibility, the V2 branch also commits `submission/v2-product-preview.html`. That preview is deterministically rebuilt from the certified V1 1,000-company output after zero-network canonical projection; its metadata is recorded in `submission/v2-product-preview.json`. The preview proves the data-linked product path but does not claim to contain the later live-registry recovery values, because those internal `registry_live` records were not present in the frozen V1 public JSONL.

## What V2 does not change

- website identity thresholds;
- request/cost budgets;
- Wikidata's candidate-only role;
- H2 social/contact interpretation boundaries;
- annual-report workforce semantics;
- refresh/change semantics.

The only official-data behavior change is publication of BRREG values that the existing runner already fetched, plus preservation of the bulk industry value that was previously normalized under mismatched keys.

This iteration is intended to recover evaluator-visible value from already-supported facts before adding broader source families.
