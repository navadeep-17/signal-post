# H1 domain discovery

Status: **HARDENED EXPERIMENTAL STRATEGY — integrated into the competition runner behind an off-by-default flag**

H1 exists because the frozen first-100 baseline showed 93/100 companies without a registry website and only 2/100 canonical websites already passing the exact-entity gate. The publication invariant never changes:

> Discovery may nominate a domain. Only independently fetched exact-entity evidence may publish it as the canonical company website.

## H1a — BRREG registry-email-domain candidate

For companies whose BRREG website field is missing:

1. Read the public `epostadresse` already present in official registry evidence.
2. Reject clearly generic consumer mailbox domains.
3. Treat any remaining email domain as a candidate, never as a company fact.
4. Fetch the candidate through the existing safe URL, robots and redirect controls.
5. Apply the general website identity gate plus the H1 page-level hardening gate.
6. Require independently fetched page evidence; hostname-only similarity cannot publish.
7. Protect against parent, franchise, namesake, manager/service-provider, hosting-placeholder and customer-subdomain failure modes.
8. Allow the narrow deterministic corroboration paths covered by regression tests.
9. Promote only exact independently verified sites; quarantine review/uncertain/error cases.
10. Record requests, bytes, latency, evidence and $0 third-party API cost.

The strategy uses no search provider.

## Dangerous false positive found and fixed

An early validation run incorrectly marked `mesco.no` exact for `MESCO AS`. The domain resolved to a generic Norwegian hosting/webhotel placeholder; a single legal-name token plus hostname evidence was too permissive.

The correction is generic rather than company-specific:

- Norwegian registered-domain/webhotel placeholder language is detected;
- H1 requires page-derived identity rather than hostname-only identity;
- parent/franchise/namesake/service-provider regressions are permanent tests;
- `mesco.no` remains quarantined.

This is why H1 remains biased toward abstention.

## Frozen initial 200-company experiment

Development slice:
- first 100 companies of deterministic seed `20260823`
- SHA-256 `51a96f25f79532b9ba285304d540887e0f17410907909dbe6c85c0b41b8341d3`

Zero-overlap validation slice:
- rows 101–200
- SHA-256 `5cdbe6e976eb7e7011dd47b0617e80410b4410de13819465c21c9cc099a325c7`

Final audited results from that stage:

### Development 100
- eligible email-domain profiles: 14
- exact/promoted: 1
- quarantined: 13
- requests: 74
- third-party API cost: $0
- promoted: `ARKITEKTFIRMA JON VIKØREN AS` / `985589003` -> `arkjv.no`

### Zero-overlap validation 100
- eligible email-domain profiles: 7
- exact/promoted: 1
- quarantined: 6
- requests: 30
- third-party API cost: $0
- promoted: `MASTER SURGERY SYSTEMS AS` / `993550116` -> `mastersurgerysystems.no`

Both promotions were manually audited as correct. Two examples were not enough to claim production precision, so H1 was not promoted at that stage.

## Larger 600-company qualification audit

A later qualification branch froze rows 201–800 of the same deterministic 1,000-company manifest and left rows 801–1000 untouched for later release validation.

Frozen hashes:
- qualification 600: `5a910aadec1c1a7c453e34bc5cb31df2ab8c31e536d1753451609654d424181a`
- untouched final 200: `fb81f7695ee91606d1af7eee00e8323a326ebc33b79b3cb1a4f046573ae3368f`

One frozen Builderr organisation was absent from the current BRREG snapshot. The corpus was **not** replaced or resampled; snapshot drift is recorded explicitly.

Final qualification result:
- frozen companies: 600
- present in current BRREG snapshot: 599
- snapshot-missing: 1
- eligible H1 candidates: 62
- promoted exact sites: 8
- quarantined candidates: 54
- requests: 267
- third-party API cost: $0
- H1 wall runtime: about 84 seconds
- previously observed ~15s long tail reduced by bounded concurrency / shorter normal timeout

All eight promoted sites were manually audited as the exact legal entity. The quarantined set included realistic parent/group/manager/provider hard negatives rather than only synthetic cases.

This still does not statistically prove a 99.5% production-precision target. The strategy therefore remains optional and conservative.

## Competition-runner integration

`run_competition_batch.py` now supports:

```text
--enable-email-domain-discovery
--email-domain-timeout 8
--email-domain-retry-timeout 15
--email-domain-max-candidates 2
```

The strategy is **off by default**. Without the flag, baseline runner behavior is unchanged.

When enabled:

```text
BRREG official modules
        ↓
registry website present?
   yes       no
    ↓         ↓
normal      H1a candidate discovery
website       ↓
flow       independent fetch
              ↓
         hardened exact-entity gate
              ↓
         exact? promote : quarantine
```

Resume semantics also account for the H1 attempt. A no-registry-website profile is not considered complete under an H1-enabled resume unless `website_email_discovery` evidence exists.

## Frozen 100-company runner benchmark

The opt-in integration was evaluated on the exact original development corpus:

- manifest SHA-256: `51a96f25f79532b9ba285304d540887e0f17410907909dbe6c85c0b41b8341d3`
- baseline requests: 536
- H1-enabled requests: 622
- request delta: +86
- baseline canonical exact websites: 2
- H1-enabled canonical exact websites: 3
- exact-site uplift: +1
- H1 candidate domains: 14
- H1 exact promotions: 1
- H1 quarantined: 13
- third-party API cost: $0
- terminal envelopes: 100/100
- zero silent drops: yes
- runner duration: about 94 seconds
- request p50: 640 ms
- request p95: 761 ms

The single H1 promotion was the previously audited `arkjv.no` case. This demonstrates a real but modest coverage gain with comfortable resource headroom.

## H1b — licensed search-provider fallback

Only companies unresolved by registry website + H1a should reach H1b. Search output may nominate candidate URLs only; publication still requires independent fetch and exact-company proof.

H1b remains blocked on provider selection and rights review.

### Brave Search API

Standard terms reviewed for this project are not approved for the H1 benchmark because of restrictions around retention and evaluating/benchmarking AI services. The existing Brave script remains reference/experimental unless custom terms explicitly permit our use.

### Other providers

Any Tavily/Serper/other search path remains `PLANNED / RIGHTS REVIEW` until exact plan terms, storage/transient handling, benchmark use and cost are documented.

## Current decision

- Keep H1a implementation, tests and qualification tooling on `main`.
- Keep competition-runner integration **off by default**.
- Use the flag for controlled benchmarks and later strategy-freeze experiments.
- Do not lower the identity threshold to improve recall.
- Do not touch the untouched final 200-company holdout yet.
- Move development attention to H1b provider selection and/or company-owned signal extraction after the opt-in runner PR lands.

## Promotion / strategy-freeze gate

Before H1a becomes part of the final default submission strategy, require:

1. current acquisition rights remain valid;
2. candidate discovery and publication evidence stay separate;
3. every promoted site has independently fetched URL/time/hash/exact-entity reasoning;
4. no wrong-company publication appears in audited corpora;
5. gain transfers beyond the original development examples;
6. request/runtime/cost remain comfortably within the final 100-company budget;
7. refresh/resume/idempotency semantics remain correct;
8. final strategy is frozen before touching the untouched release holdout.
