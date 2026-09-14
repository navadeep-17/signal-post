# H1c frozen-100 precision audit — 2026-09-14

## Decision

H1c remains a conservative zero-cost website discovery path. The preliminary page/domain gate is not sufficient by itself; publication must also pass `h1c_registry_risk_guard_v1`.

## Corpus

- Frozen development corpus: 100 companies
- Manifest SHA256: `51a96f25f79532b9ba285304d540887e0f17410907909dbe6c85c0b41b8341d3`
- Parent H1a exact websites: 3
- H1a requests: 622

## Preliminary H1c run

- Eligible profiles: 97
- Candidate attempts: 170
- H1c counted requests: 44
- H1c wall runtime: 17.314 s
- Search API requests: 0
- Third-party API cost: $0
- Preliminary H1c promotions: 4
- Combined requests: 666

Preliminary promotions:

1. `924585463` — RB PROFF PARTNER AS — `rbproffpartner.no`
2. `927210657` — OUT OF BOUNDS AS — `out-of-bounds.no`
3. `982942942` — BRANDMAKER AS — `brandmaker.no`
4. `991429999` — HØILAND GARD AS — `hoiland-gard.no`

## Manual audit findings

### Keep — RB PROFF PARTNER AS

The candidate site identifies RB Proff Partner AS and exposes the same Oslo address/phone context as the registered company. The company activity and website activity are consistent with building/renovation services.

### Quarantine — OUT OF BOUNDS AS

The Norwegian registry target is organisation `927210657`, registered in Bærum/Haslum and described as an entity whose purpose is to acquire, own and manage shares/interests. The candidate `out-of-bounds.no` is an operating golf-ball shop and identifies `Out of Bounds Sweden AB` in Sweden. This is a wrong-legal-entity collision despite the matching brand words and domain.

This failure motivated `zero_cost_registry_guard.py`:

- exact organisation-number proof still wins;
- same-core foreign legal-entity markers are quarantined;
- registry entities with unspecified/holding-oriented activity require registry-location corroboration when no exact organisation number is present.

### Keep — BRANDMAKER AS

Single-token-name protection requires independent location evidence. The site contains Bergen context matching the registered company, so the candidate survives the stricter guard.

### Keep — HØILAND GARD AS

The site identifies Høiland Gard and Årdal/Ryfylke context consistent with the registered Hjelmeland/Årdal entity.

## Qualified result after registry-risk guard

- H1c promotions retained: 3
- H1c promotions quarantined: 1
- Exact websites before H1c: 3
- Exact websites after hardened H1c: 6
- Net exact-site uplift: +3
- Combined counted requests: 666
- Combined third-party API cost: $0
- Search API requests: 0

## Promotion status

H1c is suitable to proceed as an opt-in zero-cost discovery component, subject to the existing exact-entity, request-budget, refresh and output-contract gates. It should not be treated as a search replacement for every unresolved company; it is a bounded high-precision heuristic.
