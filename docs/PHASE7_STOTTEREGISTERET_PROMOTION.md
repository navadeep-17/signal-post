# Phase 7 — Støtteregisteret Support-Award Promotion

Decision: **PROMOTE source semantics / final wrapper requalification still pending before merge**.

## Identity and evidence contract

- Official Brønnøysundregistrene Støtteregisteret complete CSV; NLOD.
- One shared dataset request per evaluator batch.
- Target identity is authorized only when the row's **primary recipient organisation number** exactly equals the target org number.
- `Spesifisert mottaker` and granting authority are context only.
- <=365-day awards; max 5 most-recent events/company.
- Evaluator-facing evidence retains row SHA-256, snapshot SHA-256, source row number/key, retrieval timestamp and exact evidence span.
- Amounts are emitted only with explicit source currency; interval values retain explicit interval currency.
- Claim: `official.support_award`; canonical fact: `support_award` / `public.official_support_award`.
- The fact is official support activity, never company-authored news/social/hiring activity.
- Expected source failure is nonfatal and cannot remove a terminal company envelope.

## Consumed semantic qualification

Run `37254237936`, job `111587836938`: **PASS**.

- Artifact `11321344340`; ZIP SHA-256 `ba2fcdcf22473cc5e6159086516e7eb32da14b43ff11c4717f889910a383e357`.
- Cohort: certified final-release-1000 chunk 0, already consumed; 100 companies; no fresh cohort.
- 100/100 terminal; 11 support companies; 46 support observations/claims/canonical facts.
- 0 contract, canonical, synthesis, external-observation, registry-change-integrity or budget failures.
- 1 shared support request; 305,978,976 bytes.
- Support snapshot SHA-256 `8889b22ee01c7aaae1dd6a0c079977e00f4d390440ec0779f17d999dfbd951d1`.
- H2g ceiling 97; observed conservative charge 1,366/2,000; theoretical charge 2,000/2,000.
- External wall time 784 s; third-party cost $0; search API requests 0.
- Product HTML contained the canonical support facts/evidence.

This run remains definitive evidence for the source's identity/evidence/amount/currency semantics, but it predates the final V7 integration boundary and cannot replace the exact-wrapper gate.

## Immutable-layer correction

PR #97 initially placed support integration inside immutable certified V1. Baseline CI run `37255960174`, job `111592968992`, correctly blocked that shape after 459 tests passed and the repository-only submission verifier alone failed.

The verifier/pin was not weakened. Instead:

- V1 was restored byte-for-byte to blob `9be89b9827135b1ed703318e1d189d5d3b8ca604`;
- V2 remains unchanged at blob `5b69cc320c38e3aab13cf09fe2e2a09e62751433`;
- V7 owns Støtteregisteret reservation/fetch/projection/report accounting;
- V7 rebuilds canonical projection + synthesis before the V6 evaluator UI;
- support-specific flags terminate at V7.

The provenance-hardened head `7d3c9672dbb592851d705ebe38a1674752fa4c48` subsequently passed full Baseline CI run `37257806967`, including immutable submission-bundle verification.

## First exact-wrapper consumed requalification

Run `37257936472`, job `111598892070`, qualification SHA `05cb7ff9e3defbaea8c5264ceca51467e2be1173` used production parent `7d3c9672dbb592851d705ebe38a1674752fa4c48` plus only a temporary workflow.

Result: **runtime PASS / verifier FAIL because of a report-only canonical-counting bug**.

Production/runtime output from the run:

- 100/100 terminal;
- support status available;
- 11 support companies;
- 46 support observations/claims;
- actual output contains 46 root canonical support facts and 46 `canonical_profile.public_activity` support facts;
- support source request: 1;
- support bytes: 305,978,976;
- support snapshot SHA-256 `8889b22ee01c7aaae1dd6a0c079977e00f4d390440ec0779f17d999dfbd951d1`;
- observed conservative charge 1,366/2,000;
- theoretical ceiling exactly 2,000/2,000;
- wrapper runtime 872.984 s/2,400;
- third-party cost $0;
- search API requests 0;
- contract/canonical/synthesis/support-projection errors 0;
- product HTML 4,839,164 bytes and contains support facts/evidence.

Artifact `11323453311` (`phase7-v8-consumed-requalification-100`) has ZIP SHA-256 `2bdfe26920ed5e67a24859b69ca0c84b2d7863a7c21a2e22e47dfbd529aafef9`.

A complete 46-row artifact audit found zero evidence defects: each claim has one exact evidence record with row hash, snapshot hash, source row number/key, retrieval time, matching award date, exact `recipient org: <target>` span, and source-backed currency semantics.

The verifier failed only because V7 report accounting counted canonical facts using:

`fact["type"] == "public.official_support_award"`

but canonical facts correctly encode:

- `type = "support_award"`
- `canonical_field = "public.official_support_award"`.

Therefore the report incorrectly said `published_claims=46` / `published_canonical_facts=0` even though the output contained all 46 facts. The verifier correctly rejected that inconsistent report.

This run remains a **failed promotion gate** and must not be relabelled as qualified.

## Report-counter correction

The report bug is fixed by counting the canonical field, with a dedicated regression:

- source fix: `d027fbadb5dac2f6ac07ef9a3b5cba97a5caf788`;
- regression head: `6695a5c4a8c8bd2a4499db1d3b30752f6a817c60`.

The final docs-inclusive head must pass Baseline CI again, followed by another exact-wrapper consumed V8 run on the same already-consumed cohort.

## Corrected request theorem

For actual V8 on 100 companies with a 2,000 conservative-request cap:

1. V8 supplies 2,000 to V7.
2. V7 reserves 1 Støtteregisteret shared request (charge 2) and forwards 1,998 to V2.
3. Unchanged V2 reserves 1 BRREG change-feed request (charge 2) and forwards 1,996 to immutable V1.
4. V1 fixed company + Wikidata ceiling is 901 logical; under 1,996 conservative it has 97 H2g annual-report slots.
5. V1 theoretical total = 998 logical / 1,996 conservative.
6. Add BRREG change feed = 999 logical / 1,998 conservative.
7. Add support dataset = **1,000 logical / exactly 2,000 conservative**.

No additional request can be added without re-proving the theorem and deliberately reallocating a slot.

## Promotion gate

Before merge require all of the following on the final clean PR head:

1. exact-head Baseline CI green;
2. exact-head actual-V8 consumed requalification on the already-consumed certified 100;
3. 100% terminal output and zero contract/canonical/synthesis/registry-change/support integrity failures;
4. support report count equals actual support claims and canonical facts;
5. one support request, combined theoretical conservative ceiling <=2,000, runtime <= wrapper ceiling, $0 third-party cost, zero search API requests;
6. evaluator-facing V6 product contains support facts/evidence;
7. complete support-fact audit with exact primary-recipient identity and full row/snapshot provenance;
8. temporary qualification workflow removed and final PR diff clean;
9. final exact-head Baseline CI green after cleanup.

Only after those gates pass may PR #97 merge with expected-head protection. Then require post-merge Baseline CI and pin the exact production SHA/run. After that, advance to Phase 11 fresh evaluator-shaped release qualification. Do not submit a Builderr revision merely because this source merged.
