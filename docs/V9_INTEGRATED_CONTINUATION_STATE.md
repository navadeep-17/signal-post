# Signalpost V9 Integrated Candidate State

Last updated: 2026-10-06

## Frozen boundary

- production baseline: `72f1bf2892ec1c1e35674aa383433c9a37afdaca`
- integrated branch: `experiment/v9-integrated-candidate`
- branch point: promoted M2 head `5fda04cd81f1cbba77ee741361e3b5bd064a0d86`
- V8 release/submission refs remain untouched
- no fresh cohort is authorized at this stage

## Qualified components entering integration

M2 is PROMOTE from its isolated branch: all 54 behaviorally affected consumed companies were
included in the targeted gate; verified websites moved 8 -> 9 with zero losses; scored
family-company coverage gained +4 with zero losses; five new publications were all manually
reviewed with zero wrong-company results; observed conservative request charge fell 1602 -> 1418;
the theoretical ceiling remained 2000; search requests and third-party API cost remained zero.

M4 is PROMOTE from isolated PR #143 / head
`e931519d58f82c79fc96b8e7fd54cb5143819b71`: the frozen consumed-1000 replay moved contact
email companies 53 -> 58, contact phone companies 0 -> 19, and any external contact companies
53 -> 60. All 26 new contact claims were manually reviewed with zero wrong-company or ambiguous
structured-node publications, zero existing-contact losses, zero non-contact changes and zero
network requests.

## Integration-specific change

The standalone M4 experiment deliberately kept the pinned V1 runner immutable, and integration
preserves that invariant. Structured email recovery takes effect through the already-called
company-site contact module. Structured phone recovery is wired at the V8 wrapper's zero-network
post-processing stage over the retained exact-site profile: `external.contact_phone` is
projected into the output contract and canonicalized as `website.contact_phone` without
changing the pinned V1 collector file.

Contact recovery remains zero-network and outside request accounting. No site identity rule,
wrong-organisation veto, evidence rule, or four-logical-site-request ceiling is weakened.

## Gate before later milestones

The integrated candidate must pass full CI, the frozen-1000 M4 replay, and an identical consumed
baseline/challenger transfer with zero verified-site losses, zero scored-family losses, zero
existing-contact losses, positive net-new scored-family coverage, request charge no higher than
baseline, theoretical charge <= 2000, zero search/paid API usage, complete evidence, and manual
precision review of every new external publication.

Fresh qualification remains locked until this integrated consumed gate passes.


### CI correction during integration

The first integrated wiring attempt modified `scripts/run_signalpost_final.py`. Baseline CI
correctly rejected that with `V1 base file drifted`. The integration was moved one layer up to
`scripts/run_signalpost_v8.py`, and the pinned V1 runner was restored byte-for-byte. This keeps
the submission immutability check meaningful while still putting M4 phone recovery on the actual
V8 evaluator path.
