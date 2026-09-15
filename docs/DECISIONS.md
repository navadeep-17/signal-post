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

This decision is subordinate to D018: paid APIs are not part of the final strategy unless the user explicitly changes the zero-cost requirement.

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

## D018 — Final production strategy must remain zero-cost

**Decision:** Target **$0 third-party API spend per 100-company run** and do not require paid APIs, paid search, paid places, paid news, or other metered commercial services in the final competition strategy.

Free/public official sources and ordinary permitted public-page fetches remain allowed. A connector with a free introductory quota but a paid continuation path is not a production dependency.

Existing paid-provider experiments may remain in the repository as dormant research code, but they must not be enabled by the final runner unless the user explicitly reverses this decision.

## D019 — Wikidata may nominate exact-ID website candidates, never prove identity

**Decision:** The final runner may use the public Wikidata Query Service as a zero-cost, bounded **candidate-discovery** source using only exact Norwegian organisation number (`P2333`) to official website (`P856`) mappings. Wikidata is not accepted as entity-proof evidence.

Publication still requires an independently fetched company page to contain either the exact target organisation number or the full legal name plus BRREG location corroboration, followed by the existing registry-risk guard. Ambiguous Wikidata mappings abstain, H1d runs first, and a Wikidata outage/throttle must degrade to H1d rather than fail the company batch.

**Rights/access basis:** Wikidata structured data is published under CC0. Programmatic access must follow Wikidata access best practices: identify the client with a proper User-Agent, request compressed responses, keep queries bounded, avoid fuzzy/text search through WDQS, and stop/abstain on service errors or throttling. Signalpost batches at most 100 exact IDs per query, performs no retries inside the connector, and keeps third-party API spend at $0.

**Qualified evidence:** H1e fresh zero-overlap validation (seed `20260921`, excluding 2,800 prior/touched companies) improved verified websites from 16 to 17 on 300 companies with zero lost sites. The sole promotion, NORSKE SELSKAB (`971424079`) → `norskeselskab.no`, was manually verified against the current BRREG legal name/location and the independently fetched site. The structural conservative ceiling is 1,802 requests per 100 companies, below the official 2,000-request cap.

## D020 — Do not promote low-yield company-site deep crawls without material recall gain

**Decision:** Do not promote H2b company-owned dated activity or revive the existing company-careers experiment in their measured forms.

**Why:** The H2b fresh zero-overlap run `34966322464` excluded 3,400 previously touched companies and evaluated a new 300-company cohort. Thirty-one companies had verified websites and all 31 had enough remaining site-request headroom for a production-compatible activity-page fetch, but only one company produced qualifying dated activity: 5 observations on CHIIJE AS. That is 1/300 = 0.33% company-level gain. The observations validated cleanly and the entity was manually corroborated, so precision was not the limiting factor; reach was.

The older company-careers frozen-100 audit `34857612452` was weaker: 6 verified sites, 11 extra careers requests and 0 publishable observations.

H2b could theoretically fit under the existing 1,802 conservative requests/100 ceiling by capturing activity links during the already-paid homepage fetch and using only remaining site-request headroom. We still decline production integration because the measured recall improvement is too small relative to the challenge's mandatory weighted external-company-recall gate.

**Follow-up rule:** Future external-signal experiments must target sources with substantially broader company coverage than the current verified-site subset. Keep H2b/careers code experimental unless new evidence materially changes expected population reach.