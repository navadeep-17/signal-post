# Signalpost — Current Continuation State

Last updated: 2026-10-04 (Asia/Kolkata)

Repository state and live GitHub metadata are authoritative over chat history. Historical detail belongs in `docs/IMPLEMENTATION_LOG.md`; architecture and phase order belong in `docs/70_PLUS_IMPLEMENTATION_PLAN.md`.

## 1. Current source of truth

Repository: `navadeep-17/signal-post`

Production branch: `main`

Live `main` immediately before this update:

`2140105da59fbf77769f9fd95b9643de589c8b62`

That tip is documentation-only on top of Phase-A production merge `8a729036350c019e107cd68a08641f1fff6796f6`; production code semantics remain Phase A / V8. Open PRs #76, #78 and #84 remain historical/experimental and are not the active production path.

No Phase-2 or NAV experiment is qualified or merged.

Latest completed experiments:

- `experiment/phase2-registry-secondary-identity-screen`, measured head `03b9ab870c00ac681cbf47ca74a57920e9a76e5f`: **DROP**.
- `experiment/nav-exact-org-vacancy-screen`, measured head `c156fda6a5ac711b285e864270273446262d19ac`: **DROP**.

## 2. Lifecycle state

### Phase 1 / collected-vs-emitted exact BRREG recovery

- **IMPLEMENTED:** yes
- **TESTED:** yes
- **QUALIFIED:** yes
- **MERGED:** yes
- **POST-MERGE GREEN:** yes

Phase 1 is closed.

### Phase 2 / exact website-discovery improvement

- **IMPLEMENTED:** experiment-only strategies; no new production strategy merged
- **TESTED:** yes
- **QUALIFIED:** no
- **MERGED:** no
- **STATE:** **CANDIDATE-SOURCE CONSTRAINED / SHELVED under the current $0, rights-safe source set**

Do not keep generating more legal-name domain guesses without a genuinely new rights-safe candidate source. The measured bottleneck is candidate generation, not identity verification.

### Phase 3 / bounded verified-site activity discovery

- **IMPLEMENTED:** not yet
- **TESTED:** not yet
- **QUALIFIED:** no
- **MERGED:** no
- **STATE:** **ACTIVE NEXT PHASE**

## 3. Retained Phase-A baseline

Second untouched qualification run `37203580574`:

- fresh cohort: 100 unique, overlap 0
- cohort SHA: `4078579d4a581da0b8d56e4d03d567c4032d43e93c8bb94ee3c02b140b651e40`
- 100/100 terminal
- evidence/contract/canonical/synthesis errors: 0
- logical requests: 666
- conservative charge: 1,332/2,000
- runtime: 460.916 s
- third-party cost: $0
- search API requests: 0
- artifact: `phasea-final-fresh-disjoint-100-v2`, ID `11304401011`, digest `sha256:31e12e11f2746dcf8c0b6454ab6052ab44281176363b6934889d22d57a08800b`

Consumed Phase-2 reruns show 7–8 exact verified websites because live page/network state drifts slightly.

## 4. Phase-2 experiment decisions

### Norid organisation-number domain lookup

Decision: **DROP / DO NOT IMPLEMENT**.

Public lookup rights/purpose restrictions are incompatible with Signalpost production use; anonymous RDAP does not provide an equivalent organisation-number subscriber-domain search path.

### Exact-parent BRREG subunit homepage hints

Decision: **DROP**.

- branch `experiment/phase2-subunit-homepage-screen`
- run `37208360582`: PASS
- artifact ID `11306100222`
- 3 candidate companies / 3 attempts / **0 accepted exact target sites**
- 6 logical / 12 conservative requests; $0; zero wrong-company publications

### Exact-parent BRREG subunit email-domain hints

Decision: **DROP**.

- branch `experiment/phase2-subunit-email-domain-screen`
- head `5321ab9689d754bd2f2415f392a8d0179050b6ae`
- run `37209911261`: PASS
- artifact ID `11306935410`, digest `sha256:fab8b2d62950eea9e5991bcf1cf61512a4532680ddcc9f1330c30ba36b19038e`
- 10 unresolved companies with non-generic domain candidates / 10 attempts / **0 accepted**
- 16 logical / 32 conservative requests; $0; zero wrong-company publications
- `AGILE SOLUTIONS AS` matched its legal name at `agilesolutions.no` but lacked the predeclared exact organisation-number or BRREG-location proof; do not weaken the rule post-hoc

### Same-domain secondary identity verification for quarantined BRREG websites

Decision: **DROP**.

- branch `experiment/phase2-registry-secondary-identity-screen`
- exact measured head `03b9ab870c00ac681cbf47ca74a57920e9a76e5f`
- run `37211887561`: PASS
- artifact `phase2-registry-secondary-identity-screen`, ID `11307036767`
- digest `sha256:b552fe0a4961148a9a0e3dfac520dc9535cfe3171af624cf3efc90a885c59937`
- publication disabled; full regressions passed
- 4 loaded quarantined registry-linked sites / 4 secondary attempts / **0 accepted**
- decisions: 1 conflicting explicit organisation number, 1 insufficient proof, 2 secondary pages unavailable
- 8 logical / 16 conservative screen charge; runtime 9.468 s; $0/search0
- request theorem held: existing registry homepage 2 + one secondary page max 2 = four logical site requests, no fifth request
- positive proof was hardened to be page-local to the secondary page; homepage + secondary split evidence is explicitly regression-rejected

Manual conflict audit: `VIKHOV B4 BORETTSLAG` at `bonitas.no/personvernerklaering` explicitly identified organisation number `987579773`, not the target, so rejection was correct.

## 5. Phase-2 failure funnel / root cause

Frozen consumed-cohort evidence shows the dominant failure is candidate generation:

- H1c deterministic legal-name `.no`: 96 attempts
  - 79 blocked
  - **78 failed because hostname did not resolve**
  - 12 loaded
  - 5 source errors
  - 3 exact websites ultimately verified
- H1g hyphenated `.no`: 73 attempts
  - **73/73 failed because hostname did not resolve**
  - 0 verified

Combined with 0/3 subunit-homepage, 0/10 subunit-email-domain and 0/4 secondary-identity transfer, this is sufficient negative evidence to stop spending cycles on more speculative $0 domain heuristics. Identity precision remains intact; the missing ingredient is a genuinely new candidate source.

## 6. NAV exact-org vacancy-feed screen

Decision: **DROP / DO NOT PROMOTE / NOT MERGED**.

NAV was screened as an exact-ID alternative to website-dependent hiring acquisition.

- branch `experiment/nav-exact-org-vacancy-screen`
- exact measured head `c156fda6a5ac711b285e864270273446262d19ac`
- first run `37213928445` failed before any NAV request because the workflow referenced the wrong frozen-report key; full regressions were green and the harness-only issue was corrected
- corrected run `37214017085`: PASS
- artifact `nav-exact-org-vacancy-screen`, ID `11307433276`
- digest `sha256:917ad28cc991fdeb70a8f78617cbb8c0c1fbbf49e8c6ce598455630127d7e5db`
- publication disabled; personal contact fields not retained
- 180-day feed window; 10,000 events/page
- feed requests: 38
- feed bytes: 181,234,775
- raw events: 368,428
- unique vacancies: 90,917
- active unique vacancies: 9,723
- feed traversal complete: yes
- shortlisted target/subunit business-name vacancies: **0**
- detail requests: 0
- exact active vacancies: 0
- exact active-vacancy target companies: **0/100**
- NAV logical requests: 39
- NAV conservative charge: 78
- projected combined charge with Phase-A baseline: **1,410/2,000**, 590 headroom
- runtime: 62.381 s
- third-party cost: $0; search API requests: 0; wrong-company publications: 0

The screen would authorize a detail only when `employer.orgnr` equals the main target organisation number or an exact BRREG subunit organisation number whose recorded parent is the target. No candidate reached that detail stage. The public experiment token is also not a stable production-access mechanism. Do not spend a fresh cohort or broaden name matching post-hoc against this consumed cohort.

## 7. Precision and budget invariants

- exact organisation number remains the legal-entity anchor
- candidate generation is never publication proof
- parent/subsidiary/subunit relation alone cannot authorize a website claim
- exact BRREG subunit -> parent mapping may authorize only the specific relation semantics explicitly designed for that source
- wrong-company publication is a hard failure
- exact-page provenance remains mandatory
- missing/blocked/ambiguous stays explicit
- third-party API spend remains $0
- no paid/search API path is active
- four logical site requests/profile remains the production site ceiling
- new site enrichment must fit by adaptive ordering/substitution, not a fifth site request
- fresh cohorts remain reserved for promotion after meaningful consumed-cohort transfer

## 8. Verified-site surface inventory

On the frozen consumed 100 there are 7 exact verified sites. Across those 7 homepages:

- homepage careers links: 0 companies
- homepage news-detail links: 0 companies
- structured homepage job candidates: 0 companies
- explicit homepage publication-date candidates: 0 companies
- social links: present on 3 companies
- same-domain identity/contact-type links: present on 6 companies

The prior idle contact-page experiment already failed to add net-new contact-family coverage, so the next experiment must not simply repeat a generic contact fallback.

## 9. Selected next strategy

Advance to **Phase 3 / Phase 7 combined consumed-cohort screen: bounded RSS/sitemap discovery for dated first-party activity on already verified exact domains**.

Why this is the next distinct opportunity:

- it uses only domains whose legal identity is already verified
- it addresses a scored information family that current verified homepages do not expose
- C12 M3 currently depends on homepage-nominated news detail links, which are absent on all 7 frozen verified homepages
- RSS/Atom or sitemap metadata can nominate dated article/detail URLs without weakening company identity
- only page-local explicit dates / structured `NewsArticle` or `Article` evidence can support publication
- the screen can consume only currently idle final site-request capacity and must remain within the existing four-request theorem

Initial experiment rules:

1. publication disabled
2. consumed cohort only; no fresh cohort
3. verified exact domains only
4. at most one discovery fetch plus one detail fetch per eligible verified company
5. prefer homepage-declared feed/sitemap hints; otherwise deterministic same-domain `/sitemap.xml` or common RSS endpoint only when the request theorem permits
6. never crawl an entire sitemap; rank at most a tiny bounded set of recent article/news candidates
7. detail page must remain same verified registered domain
8. require explicit page-local publication date and concrete article/update content
9. preserve URL, retrieval timestamp, content hash and exact supporting evidence
10. PROMOTE only for meaningful net-new dated-activity company coverage with zero identity/evidence errors

## 10. Exact next 1–3 actions

1. Create `experiment/phase3-dated-activity-discovery` from current `main`.
2. Build a publication-disabled RSS/sitemap activity discovery screen on the same frozen consumed 100, limited to verified exact sites and two idle logical site requests/company.
3. Measure discovery reach, dated-detail acceptance, exact page evidence, request/runtime cost and manually audit every accepted activity before any promotion decision.

## 11. NEXT

**NEXT: Phase 3 consumed-cohort RSS/sitemap dated-activity screen on already verified exact domains; at most one discovery + one detail page, publication disabled, no fresh cohort.**
