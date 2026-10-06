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

## Integrated consumed gate decision

Decision: **PROMOTE** the M2+M4 integrated candidate as the base for the next isolated milestone.
Do not merge it to production `main` yet.

Exact qualified head: `ce0efaf7a2abba82b66726111ed488bf5185fa3a`.

Qualification evidence:

- Baseline CI run `37496552802`: **PASS**;
- M4 structured-contact replay run `37496552655`: **PASS**;
- exact-head integrated consumed gate run `37496552710`: **PASS**;
- integrated artifact ID: `11429661159`;
- integrated artifact digest:
  `sha256:a39d110a13edc21935c3c1e19613f5407cc1c012e4c40f209b0dba868e882977`;
- cohort: 100 already-consumed companies, including all **54** M2 behaviorally affected companies,
  **33** preserved-email controls and **13** no-email controls;
- fresh companies used: **0**.

Exact-head family transfer:

- verified website companies: **8 -> 9**, net-new **+1**, lost **0**;
- social companies: **5 -> 6**, net-new **+1**, lost **0**;
- external-contact companies: **4 -> 6**, net-new **+2**, lost **0**;
- careers-surface companies: **2 -> 3**, net-new **+1**, lost **0**;
- company-authored hiring-intent companies: **0 -> 0**;
- specific active-job companies: **0 -> 0**;
- dated first-party activity companies: **2 -> 2**, lost **0**;
- total net-new scored family-company edges: **+5**;
- total lost scored family-company edges: **0**;
- new evaluator-family publications: **8**;
- lost evaluator-family publications: **0**;
- new verified websites: **1**;
- lost verified websites: **0**.

Cost / runtime / contract:

- observed logical requests: **801 -> 709**;
- observed conservative challenge charge: **1602 -> 1418**;
- theoretical conservative ceiling: **2000 -> 2000**;
- wall runtime: **683.788 s -> 668.892 s**;
- third-party API cost: **$0**;
- search API requests: **0**;
- contact-email network requests: **0**;
- contact-phone network requests: **0**;
- terminal outputs: **100/100**;
- contract validation: **PASS**;
- canonical validation errors: **0**;
- synthesis validation errors: **0**;
- external-observation validation errors: **0**;
- structured-contact-phone projection is explicitly zero-network.

Manual precision audit completed for **8/8** new external publications:

1. VOLF AS (`979943377`) structured email `post@volf.no`: exact website gate 0.95,
   same registered domain, and the individual schema.org Organization node carries exact
   organisation number `979943377`.
2. VOLF AS structured phone `+4770275662`: same exact website and exact structured-node
   organisation-number identity.
3. DEN GLADE GRIS AS (`999096298`) website `https://www.dengladegris.no/`: exact identity
   0.98 with all legal-name tokens plus same-domain secondary identity corroboration.
4. DEN GLADE GRIS AS careers surface `/ledige-stillinger`: same-host homepage declaration;
   published only as careers presence, not active hiring intent or a specific vacancy.
5. DEN GLADE GRIS AS Facebook handle: explicitly declared by the exact homepage and independently
   token-compatible with the legal name.
6. DEN GLADE GRIS AS Instagram handle: same bounded homepage-declaration rule.
7. DEN GLADE GRIS AS email `booking@dengladegris.no`: bounded company-page contact evidence and
   exact registered-domain match.
8. DEN GLADE GRIS AS phone `+4722111710`: schema.org Organization node matched the legal name
   `Den Glade Gris` on the exact company homepage.

Manual result: **8 reviewed / 8 accepted / 0 wrong-company / 0 material page-scope ambiguity**.

The integrated candidate therefore satisfies the consumed promotion gate: positive scored-family
lift, zero regressions, lower observed request usage, unchanged worst-case theorem, zero paid/search
cost, complete evidence, and zero wrong-company publications.

Fresh qualification is still locked. The next milestone is **M5 hiring semantics**, implemented
on a new isolated branch from this exact promoted integrated head.


### CI correction during integration

The first integrated wiring attempt modified `scripts/run_signalpost_final.py`. Baseline CI
correctly rejected that with `V1 base file drifted`. The integration was moved one layer up to
`scripts/run_signalpost_v8.py`, and the pinned V1 runner was restored byte-for-byte. This keeps
the submission immutability check meaningful while still putting M4 phone recovery on the actual
V8 evaluator path.
