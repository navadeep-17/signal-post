# Signalpost — Current Continuation State

Last updated: 2026-10-04 (Asia/Kolkata)

Repository state and live GitHub metadata are authoritative over chat history. Historical detail belongs in `docs/IMPLEMENTATION_LOG.md`; architecture and phase order belong in `docs/70_PLUS_IMPLEMENTATION_PLAN.md`.

## 1. Current source of truth

Repository: `navadeep-17/signal-post`

Production branch: `main`

Production-code `main` SHA before this documentation handoff:

`bef9ba9d4cc789ee36b6577ff251c7304fc3abed`

That commit is documentation-only on top of Phase-A production merge `8a729036350c019e107cd68a08641f1fff6796f6`; production semantics remain Phase A.

Open PRs #76, #78 and #84 are historical/experimental and are not the active production path.

Latest Phase-2 experiment branch:

- branch: `experiment/phase2-subunit-homepage-screen`
- exact measured head: `afe25ce63219c9c0eba532cac8b498fd012a9194`
- PR: none
- status: **IMPLEMENTED + TESTED + MEASURED / DROP / NOT QUALIFIED / NOT MERGED**

## 2. Lifecycle state

### Phase 1 / collected-vs-emitted exact BRREG recovery

- **IMPLEMENTED:** yes
- **TESTED:** yes
- **QUALIFIED:** yes
- **MERGED:** yes
- **POST-MERGE GREEN:** yes

Phase 1 is closed.

### Phase 2 / exact website-discovery improvement

- **IMPLEMENTED:** experiment-only strategies only; no new production discovery strategy merged
- **TESTED:** yes, first consumed-cohort screen completed
- **QUALIFIED:** no
- **MERGED:** no
- **POST-MERGE GREEN:** not applicable

Phase 2 is active.

## 3. Phase-A baseline retained for Phase 2

Second untouched Phase-A qualification run `37203580574`:

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

Website baseline on that same consumed cohort:

- exact verified websites: **7/100**
- not available: 87
- ambiguous: 4
- failed: 2
- external social-profile claims: 10
- external first-party contact-email claims: 6

Interpretation: exact website reach remains the dominant unlock for later contact/social/jobs/activity phases.

## 4. Phase-2 experiment decisions

### Norid organisation-number domain lookup

Decision: **DROP / DO NOT IMPLEMENT**.

Reason: public lookup rights/purpose terms are incompatible with Signalpost production use; repeated lookup is rate-limited/anti-bot protected, and anonymous RDAP does not provide an equivalent organisation-number subscriber-domain search path.

### Exact-parent BRREG subunit `hjemmeside` hints

Decision: **DROP**.

Experiment:

- branch: `experiment/phase2-subunit-homepage-screen`
- measured head: `afe25ce63219c9c0eba532cac8b498fd012a9194`
- workflow run: `37208360582` — PASS
- artifact: `phase2-subunit-homepage-screen`
- artifact ID: `11306100222`
- artifact digest: `sha256:b856eba533cf5a1ee3eef4e92054fd294878480b4b3f0adc4b88e803f3314ffd`
- publication enabled: false
- full regressions: PASS
- consumed cohort: exact Phase-A seed-`20261103` 100

Measured screen:

- baseline verified websites: 7/100
- unresolved website companies: 93
- companies with exact-parent subunit homepage hints: 3
- deduplicated hints: 3
- attempted candidates: 3
- accepted exact target sites: **0**
- decision counts: 1 conflicting explicit organisation number, 2 existing identity-gate rejects
- wrong-company publications: 0
- screen logical site requests: 6
- conservative screen charge: 12
- screen runtime: 6.019 s
- screen bytes: 95,698
- third-party cost: $0
- search API requests: 0

Manual/audit cases:

- `VIKHOV B4 BORETTSLAG` candidate `bonitas.no` explicitly identified a different organisation number (`987579773`) -> correctly rejected.
- `MOG AUTOMASJON AS` candidate `mogautomasjon.no` returned a source error -> no publication.
- `ROBA UTVIKLINGSFOND STI` candidate `robautviklingsfond.no` lacked strong target-company identity evidence -> correctly rejected.

The exact-parent relationship is useful provenance for candidate generation but did not transfer to any exact verified target website. Do not integrate or spend a fresh cohort on this path.

## 5. Precision and budget invariants

- exact organisation number remains the legal-entity anchor;
- candidate generation is never publication proof;
- parent/subsidiary/subunit relationship alone cannot authorize a website claim;
- wrong-company publication is a hard failure;
- exact-page provenance remains mandatory;
- missing/blocked/ambiguous stays explicit;
- third-party API spend remains $0;
- no paid/search API path is active;
- at most four logical site requests/profile remains the Phase-2 production ceiling;
- new discovery strategies must fit that ceiling by ordering/substitution, never by silently adding a fifth site request;
- fresh cohorts remain reserved for promotion only after meaningful consumed-cohort transfer.

## 6. Known rejected / do-not-repeat Phase-2 paths

Do not revive without genuinely new evidence:

- guessed `.com` expansion;
- broad rule/ML legal-name candidate ranking with zero net-new exact sites;
- annual-report domain hints after the prior zero-yield screen;
- Norid public lookup because rights/purpose terms are incompatible;
- exact-parent subunit homepage hints after run `37208360582` yielded 0/3 exact target sites;
- provider-dependent model/search PRs #78/#84 unless Builderr resolves provider/key/budget and the $0 constraint changes.

## 7. Exact next 1–3 actions

1. Screen exact-parent BRREG subunit **email-domain** hints from the already-paid locations response. This is distinct from production H1a main-entity registry-email discovery. Retain `epostadresse` only for experiment measurement; filter generic mailbox providers using existing `GENERIC_EMAIL_DOMAINS` logic.
2. On the same already-consumed 100-company cohort, independently fetch a bounded candidate set and require exact target-page proof under the existing identity rules. Publication remains disabled. Report hint prevalence, candidates attempted, accepted exact sites, rejects, requests/runtime/cost and wrong-company findings.
3. PROMOTE only if the screen yields meaningful net-new exact websites with zero wrong-company findings and can fit the existing four-site-request ceiling. Otherwise RETUNE/SHELVE/DROP and record the result. Do not consume a fresh cohort yet.

## 8. NEXT

**NEXT: Phase 2 consumed-cohort screen of exact-parent BRREG subunit email-domain candidates. Reuse existing registry-email domain filtering and exact-page verification; publication disabled; no fresh cohort.**
