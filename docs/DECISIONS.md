# Signalpost engineering decisions

These are deliberate project decisions, not immutable competition rules. Change one only with new evidence and record the replacement decision.

## D001 — Preserve the Builderr starter

**Decision:** Improve the reference agent rather than rewriting it.

**Why:** The starter already provides official identity/financial/role/location data, website safety/extraction, batch execution, refresh, provenance, tests, external observation models and a prototype. Rewriting creates risk without scoring value.

## D002 — Protect a reproducible baseline

**Decision:** Keep the untouched starter at `d0d4599cbb9a1ed00303976c9984630a004ed37a` and branch `baseline/builderr-starter-2026-08-24`.

All development goes through bounded branches/PRs with CI.

## D003 — Current official page outranks stale indexed pages

**Decision:** The current live challenge page is the scoring/rules authority. The older indexed listed-equities/investment-research Signalpost page is stale for this repository.

## D004 — Official scoring outranks starter proxy scoring

**Decision:** Optimize against the current official 35/30/20/10/5 rubric and hard gates. Use `score_competition_v3.py` and development scores only as diagnostics.

Never change a local scorer merely to report a higher result.

## D005 — Exact entity precision is a safety constraint

**Decision:** Candidate discovery and publication identity are separate stages. Search/fuzzy matching may nominate candidates; publication requires exact-entity evidence.

We may add corroborating signals (org number, address, phone, municipality, domain/cross-links, etc.) but do not weaken the publication threshold simply for recall.

## D006 — Deterministic pipeline first

**Decision:** Retain Scrapy + extruct + Trafilatura as the primary crawl/extraction path and Playwright only as a measured fallback.

LLM/browser-agent crawling is not the foundation because of cost, determinism, evidence and batch-budget requirements.

## D007 — LLM use is downstream and evidence-bounded

**Decision:** LLMs may later help constrained extraction/synthesis/explanation where measured useful. They do not author authoritative financial values, decide exact company identity by themselves, or convert unsupported fields into facts.

## D008 — Company-owned sources before harder external sources

**Decision:** First increase value from verified company websites because they are cheap, auditable and useful for identity, social cross-links, jobs and activity.

The precise first feature after Phase 1 will still be chosen from the 100-company failure map.

## D009 — Experimental connector code is not publishable evidence

**Decision:** Existing LinkedIn guest/jobs, Google News RSS, Fagfolkguiden and other rights-review/unofficial experiments remain experimental unless the acquisition path, rights, identity precision and evidence requirements are independently qualified.

Do not make evidence publishable by simply changing `rights_status` or `acquisition_mode` strings.

## D010 — Prefer official/licensed API paths for promoted connectors

**Decision:** Where external evidence is worth pursuing, prefer an official API, licensed API/provider, company-authorized export, or permitted public page. Examples to evaluate include official Google Places and YouTube Data API paths.

## D011 — Do not build a new frontend early

**Decision:** Use and, later, improve `scripts/build_prototype.py` unless a measured UX limitation justifies replacement. UX is 5 official points; engine coverage/correctness/refresh dominate scoring.

## D012 — Use frozen corpora and zero-overlap promotion checks

**Decision:** Iterate on a fixed development set; validate promoted changes on a separate zero-overlap set; preserve a held-out set for release audit. Do not tune on held-out failures.

## D013 — One bounded hypothesis per substantive PR

Each feature PR states:

- hypothesis/gap;
- dangerous failure and regression;
- before/after coverage and correctness;
- request/runtime/cost effect;
- validation-set result;
- source-rights status;
- merge/hold/drop decision.

## D014 — Treat final-output contract adaptation as a real task

**Decision:** Keep the starter's internal envelope for diagnostics, but add a separate, tested projection into the documented `OUTPUT_CONTRACT.md` shape before release.

**Evidence:** repository search found no implementation of `evidence_ids`, `third_party_cost_usd`, or `terminal_status`; the current runner emits top-level `state`, `modules`, and `profile`.

Do not destroy useful internal state just to make the external schema look correct.

## D015 — Global resource budgeting is required before release

**Decision:** Every promoted connector must expose request/cost metrics, and the final orchestrator must enforce batch-level budgets with headroom below the official 2,000 requests / $10 / 45-minute caps.

## D016 — Missing data is a result

**Decision:** Preserve explicit unavailable/blocked/not-applicable/ambiguous/failure semantics. Never replace a missing value with numeric zero or generated prose.

## D017 — CI distinguishes offline and live checks

**Decision:** Fast offline CI runs on every PR. Live network benchmarks are separate/manual or targeted because they download large snapshots and consume public/API requests.

This prevents slow/flaky external access from weakening the core regression gate.
