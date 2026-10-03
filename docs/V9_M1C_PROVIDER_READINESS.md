# V9 M1c — provider-gated model-search qualification readiness

Status: **READY / DO NOT RUN UNTIL BUILDRR CONFIRMS PROVIDER + BUDGET**

This branch is stacked directly on the V9 M1 website-discovery experiment head. It does not modify production V8 and it does not move the M1 branch used as the base of the M2-M5 experiment stack.

## Purpose

M1c is the first live transfer gate for Website Discovery 2.0. The objective is to test model-assisted web search only as **URL nomination**, followed by the existing independent exact-company page verification.

The provider/model/search output never proves identity and is never company evidence.

## Guarded workflow

`.github/workflows/v9-m1c-model-search-qualification.yml` is intentionally **manual-only** (`workflow_dispatch`). It has no push or pull-request trigger.

The job exits before downloading or selecting a new qualification cohort unless all of the following are explicitly supplied:

1. confirmation string exactly `BUILDR_PROVIDER_AND_BUDGET_CONFIRMED`;
2. a non-placeholder model name;
3. a repository secret containing a temporary qualification API key;
4. a positive Builderr-confirmed external API cost ceiling;
5. declared web-search and token pricing used for cost accounting.

The workflow currently targets the OpenAI Responses API web-search adapter already implemented in M1. If Builderr confirms another provider/API, this workflow must be patched and re-qualified before any live run.

## Freshness boundary

The workflow deterministically reconstructs the exact historical 7,920-company exclusion chain used before the V7 careers transfer:

- expected exclusion SHA-256: `5f5560498fa22a15a24a74ab05ebbba820cc20cf9a164cd5fa007ee898deb17c`.

It then restores and verifies the frozen V7 M2C careers transfer 100:

- cohort SHA-256: `1d50c3eddb91004c6413ffd263e25b166b9ec822cceae9c9bb8c0908edd997b3`.

The two are combined into an 8,020-company exclusion manifest with unique organisation numbers.

Only then does the workflow deterministically select a new disjoint 40-company pool with seed `20261016`.

The pool is not committed to the repository. It is created only when the manually-confirmed qualification workflow runs. At that point all 40 companies are considered touched and must be added to future exclusion chains.

## Incumbent baseline before model search

`scripts/prepare_v9_m1c_unresolved_cohort.py` runs only the current website-discovery stack over the fresh 40:

1. current BRREG bulk profile;
2. existing registry/deterministic website discovery;
3. exact-org Wikidata P2333 -> P856 candidate fallback with independent page verification;
4. H1g hyphenated `.no` fallback;
5. existing four logical site-request ceiling per company.

No model/search provider is called during cohort preparation.

The first 20 companies that remain without a publishable incumbent website become the immutable M1c query cohort. If fewer than 20 remain unresolved, the workflow fails **before** model search rather than silently shrinking the qualification sample.

## Search / identity boundary

For exactly 20 incumbent-unresolved companies:

- one provider response may nominate URLs;
- at most two distinct candidate domains are independently crawled per company;
- model text, titles, ranking and raw response are transient;
- every candidate must pass the existing exact-company destination-page gate;
- conflicting explicit organisation numbers quarantine the candidate;
- rejected/ambiguous candidate pages are not persisted under the target company;
- only an independently verified page may be retained as `website_model_search_candidate`.

## Automated decision gate

`scripts/summarize_v9_m1c_qualification.py` emits one of:

- `PROVISIONAL_GO_PENDING_MANUAL_WRONG_COMPANY_AUDIT`: at least 5 verified sites / 20 and all hard machine gates pass;
- `HOLD_PENDING_MANUAL_AUDIT`: 3-4 verified sites / 20;
- `NO_GO_LOW_YIELD`: fewer than 3 verified sites / 20;
- `HARD_FAIL`: cohort size, provider errors, cost ceiling, persistence boundary, report/output integrity or accepted evidence fails.

A provisional GO is **not** sufficient for production promotion. Every accepted website must be manually reviewed against the legal entity. Any material wrong-company publication is an automatic NO-GO.

## Qualification artifact

The workflow will retain:

- fresh pool 40 + hash + selection report;
- incumbent baseline profiles;
- immutable unresolved 20 + hash;
- cohort report;
- model-search output and aggregate report;
- machine decision summary;
- compact manual accepted-site review JSONL containing legal identity, URL, identity method/reasons and destination hash.

It deliberately does **not** retain raw provider responses, response text, or rejected candidate page content.

## Current action

Do not dispatch the workflow yet.

Wait for Builderr's reply confirming:

- provider/API;
- model/key format;
- web-search/tool availability;
- exact external API budget and what it includes.

After that reply:

1. patch provider-specific details if necessary;
2. run full exact-head CI again;
3. configure the temporary repository secret if required;
4. manually dispatch M1c once;
5. audit every accepted company/domain;
6. promote to fresh-100 M1d only on zero wrong-company publications and the documented yield gate.
