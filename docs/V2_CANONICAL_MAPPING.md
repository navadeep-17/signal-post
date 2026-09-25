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

## Canonical families

| Existing claim | Canonical field/family |
|---|---|
| `legal_name` | `company.legal_name` |
| `legal_form` | `company.legal_form` |
| `municipality` | `company.municipality` |
| `industry` | `company.industry` |
| `employee_count` | `company.employee_count` |
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

## What V2 does not change

- existing BRREG/accounting collection behavior;
- website identity thresholds;
- request/cost budgets;
- Wikidata's candidate-only role;
- H2 social/contact interpretation boundaries;
- annual-report workforce semantics;
- refresh/change semantics.

This iteration is intended to recover evaluator-visible value from already-supported facts before adding broader source families.
