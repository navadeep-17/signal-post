# Signalpost V9 M11 — request theorem preflight (consumed, no release decision)

**Status:** source-level **preflight only**. The 20-company M10 Gate A is assistant-reviewed, but the 100-company M10 Gate B publication review is **not yet complete**. This document does not authorize a fresh test, merge, production promotion, source-policy override, or a claim about Builderr's private scoring.

## Evaluator identity and scope

- Qualified V8 baseline commit: `72f1bf2892ec1c1e35674aa383433c9a37afdaca`.
- Integrated V9 M2+M4+M5 evaluator commit: `2848ed505103b3cbb0a3bf8d6313ee1ba7a25ecf`.
- Gate A: `37565180008`, 20 consumed entities, reported theorem **406**.
- Gate B: prefer PR #156, workflow `37567829642` on **the same frozen evaluator SHAs and one shared BRREG input**, 100 consumed entities. Gate B results and manual evidence audit remain separately binding.

## Structural accounting for 1–100 companies

This proof models only the evaluator source graph at these commits. For a shard of `n` companies (`1 ≤ n ≤ 100`):

| Component | Maximum logical attempts | Code source |
|---|---:|---|
| Official modules | `5n` | `scripts/run_signalpost_final.py`: `OFFICIAL_FETCH_MODULES` |
| Bounded identity/site candidate fetches | `4n` | `final_site_discovery.py`: `MAX_LOGICAL_SITE_REQUESTS_PER_PROFILE` |
| Shared Wikidata discovery | `ceil(n/100)` | `wikidata_discovery.py`: `WIKIDATA_BATCH_SIZE` |
| BRREG changes feed | `ceil(n/100)` | `brreg_changes.py`: `BATCH_SIZE` |
| Shared support registry | `1` | `scripts/run_signalpost_v7.py`: `SUPPORT_REGISTRY_SHARED_REQUEST_CEILING` |
| Annual workforce attempts | `min(n, floor((2000 - 2*(5n + 4n + ceil(n/100) + ceil(n/100) + 1))/2))`, clamped ≥0 | `scripts/run_signalpost_final.py`: residual charge allocation |

`http.py` allows **at most one redirect per logical attempt**. The source `RunBudget` charges `2 × logical requests` conservatively. V7 reserves support first, then V2 reserves change feed, then the final runner constrains annual workforce by the remaining structural charge; the allowances must compose **inside** the single 2,000 charged-request cap, not independently.

For the frozen Gate A `n=20`: `2*(5*20 + 4*20 + 1 Wikidata + 1 BRREG change + 1 support + 20 workforce) = 406`; this reproduces the live Gate A report.

For the frozen Gate B `n=100`: official/site `900` logical + `1` Wikidata = 901; reserve one change and one support request, leaving `(2000-2*(901+1+1))/2 = 97` workforce attempts. Therefore `2*(900+1+1+1+97) = **2,000**`. This is compliant but **has no theoretical outbound-request headroom** under worst-case source behavior. Any extra unconditional source calls invalidate the proof unless an existing bounded slot is explicitly substituted.

The script `scripts/prove_v9_m11_budget.py` imports source constants and the HTTP redirect cap rather than trusting documentation numbers; `tests/test_v9_m11_request_theorem.py` checks Gate A 406, Gate B 2,000, and all integer shard sizes 1..100. Code on this branch must **not** change the frozen evaluator.

## Obligations NOT discharged by this static proof

1. Check actual Gate B runtime reports: exactly 100/100 terminal company envelopes on each side, 0 contract/canonical/synthesis/evidence errors, observed charge ≤ 2,000 **and** reported theoretical charge ≤ 2,000; baseline vs challenger request neutrality; each side ≤45 minutes.
2. Manually review 100% of *new* Gate B external publications for precise legal-entity identity, accessible hashed source evidence, source rights, and claim semantics; fail closed for any wrong-company or unscoped vacancy/social/phone/email claim.
3. Require zero lost family-company edges and zero lost external publications, a positive net-new company-family transfer, $0 third-party API spend, no search/model calls, no fresh companies.
4. Validate runtime source paths not modeled here: retries must increment logical attempt accounting; redirect count must remain ≤1; the external annual workforce and support connectors must respect their bounded per-run caps. The official BRREG CSV cohort preparation and package installation are workflow setup inputs, not per-entity evaluator outbound source requests; if the challenge interprets *all* workflow setup network as competing against the evaluator's 2,000-request budget, revisit the accounting explicitly.
5. Await official Builderr evaluation; do not substitute our cohort-relative seven-family screen for hidden contest scoring or report unpublished precision/recall metrics as official.

**Decision:** M11 static theorem is preparatory evidence, *not* the M10 Gate B outcome, *not* M11 runtime/scope certification, and not release authority.
