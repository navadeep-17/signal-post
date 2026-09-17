# Signalpost final pre-submission scoring/readiness audit

Updated: 2026-09-18

This document records the final pre-submission risk assessment. Builderr's live challenge page remains authoritative for scoring and qualification. Local diagnostics are not converted into an invented official score.

## Final implementation identity

- production application behavior SHA: `b14ef3c277d8f1512064f865d4028e23dcd8bacf`
- certified release harness SHA: `550bba0cce64a0a26d878c3b7f41eb20a55dc10e`
- certified 1,000 replay: `35246833190`
- final release audit: `docs/FINAL_RELEASE_1000_AUDIT.md`
- final submission declaration: `SUBMISSION.md` + `submission/manifest.json`

The post-release F4/F5/pre-submit commits change UX, documentation, verification and repository packaging only; they do not change certified production collection behavior.

## What is directly established

| Requirement | Evidence | Status |
|---|---|---|
| Exactly one terminal result/company | certified 1,000: 1,000 unique, 1,000 completed | PASS |
| Output contract | 17,098 claims, 17,050 deduplicated evidence, 0 canonical errors | PASS |
| Financial honesty | deterministic BRREG path; unavailable is not zero | PASS |
| Exact-company identity | org-number anchor + strict website gates + wrong-company regressions | PASS implementation; evaluator precision authoritative |
| Refresh/idempotency | deterministic replay: expected changes only, zero duplicates on rerun | PASS |
| Request ceiling | structural 2,000/100; max observed certified chunk 1,404 | PASS |
| Wall time | slowest certified 100-company chunk 458.803 s | PASS |
| Third-party cost | $0 | PASS |
| Source rights / URL safety | final rights register + hardened web path | PASS implementation |
| Server-side secrets | none required; explicitly declared | PASS |
| 1,000 submitted profiles + manifest | exact certified manifest/output committed under `submission/` | PASS |
| Reproducibility | pinned `uv.lock`, one runner command, bundle verifier, CI | PASS |
| Evidence-bounded UX | final output-contract workspace, desktop/mobile verified | PASS implementation; evaluator UX score authoritative |

## What remains evaluator-owned

The following cannot be honestly proven from local data:

- official coverage points (minimum 21/35);
- weighted external company recall (minimum 60%);
- official external precision percentage (minimum 95%);
- overall score (minimum 65/100).

Builderr builds a versioned checked union from submissions and its own collectors, so local site rates are not the official denominator.

## Certified release breadth

On the fresh zero-overlap 1,000:

- workforce evidence: 990/1,000;
- verified websites: 107/1,000;
- company-declared social-handle companies: 48/1,000;
- qualifying contact-email companies: 53/1,000.

These are real supported claims, but they do not substitute for absent job/review/activity/sentiment/platform-metric families.

## Main competitive risk

**Coverage is the main remaining risk.** Current reviewed Builderr entries show that a total score above 65 can still fail qualification when coverage is below the minimum. Our accuracy/evidence posture is deliberately conservative, while website/contact/social/public-activity breadth is narrower.

The project previously screened additional zero-cost sources and rejected/shelved them when measured yield, rights or exact-entity safety did not justify promotion. Do not weaken identity thresholds or revive unqualified scraping solely to inflate local counts.

## Pre-submission decision

Submit the clean certified version first. Builderr allows revised commits during the challenge. If the first concrete evaluator report identifies a deficient weighted field family, use a later revision for a measured, rights-safe connector targeted to that field. Do not tune against the frozen 1,000 release corpus.
