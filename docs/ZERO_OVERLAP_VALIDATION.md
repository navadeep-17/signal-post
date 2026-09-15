# Zero-overlap external precision validation

## Purpose

Measure wrong-company publication risk on companies that were not present anywhere in the 1,000-company development/release manifest selected with seed `20260823`.

This validation is intentionally separate from:

- frozen development 100 (rows 1-100 of the entry manifest),
- earlier H1 validation/qualification slices inside that manifest,
- the reserved final 200-company holdout inside that manifest.

The validation corpus is sampled from the same frozen Builderr universe only after excluding all 1,000 entry-manifest organisation numbers.

## Frozen selection protocol

1. Recreate the 1,000-company entry manifest with `select_entry_batch.py`, seed `20260823`.
2. Exclude every organisation number in that manifest.
3. Deterministically sample 300 companies from the remainder with seed `20260915` using `scripts/select_disjoint_validation_batch.py`.
4. Record universe, excluded-manifest and selected-corpus SHA-256 values.
5. Require `overlap_count == 0` before any live enrichment runs.

The reserved final 200-company holdout is therefore not consumed by this validation.

## Evaluator protocol

Run the merged one-command evaluator unchanged except for validation-scale count/budget values:

- expected companies: 300,
- workers: 8,
- site timeout: 6 seconds,
- theoretical conservative request ceiling: 5,400 (= 1,800 per 100 companies),
- third-party API cost ceiling: $0,
- search APIs: disabled,
- experimental connectors: disabled.

The workflow must produce exactly 300 unique completed final contract objects with zero contract/change/budget errors.

## Precision audit protocol

The workflow emits `verified-sites.jsonl` containing every company whose final canonical website evidence is `available` and `identity_assessment.publishable == true`.

Every row in that list must be manually audited before a precision result is recorded. For each promoted site verify, preferably with independent public evidence:

- organisation number when publicly visible,
- exact legal name,
- municipality/address where available,
- whether redirects/rebrands still resolve to the same legal entity,
- whether the site is instead a parent, franchise, directory, service provider, namesake or parked domain.

A promotion is a false positive if the published canonical website belongs to a different legal entity, even if the name is similar.

Observed precision is `correct promotions / audited promotions`. Do not claim that a small zero-error sample statistically proves the competition's >=95% hidden precision threshold; record sample size and uncertainty explicitly.

## Current status

Live 300-company run is in progress. Results, frozen hashes, manual audit outcomes and merge/hold decision will be appended only after the artifact is inspected.
