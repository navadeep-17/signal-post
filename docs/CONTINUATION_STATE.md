# Signalpost — Current Continuation State

Last updated: 2026-10-04 (Asia/Kolkata)

Repository state and live GitHub metadata are authoritative over chat history. Historical detail belongs in `docs/IMPLEMENTATION_LOG.md`; architecture and phase order belong in `docs/70_PLUS_IMPLEMENTATION_PLAN.md`.

## 1. Current source of truth

Repository: `navadeep-17/signal-post`

Production branch: `main`

Live `main` observed immediately before this state-only reconciliation:

`6863ffb763bdc0b0ed2eee7c1b360612291f59bf`

That tip is documentation-only on top of Phase-A production merge `8a729036350c019e107cd68a08641f1fff6796f6`; production code semantics remain Phase A. Recent documentation commits include implementation-history update `472c8453370fbb5aa9a1b847991fa90e7834f335` and roadmap update `6863ffb763bdc0b0ed2eee7c1b360612291f59bf`.

Open PRs #76, #78 and #84 are historical/experimental and are not the active production path.

Latest completed Phase-2 experiment branch:

- branch: `experiment/phase2-subunit-email-domain-screen`
- exact measured head: `5321ab9689d754bd2f2415f392a8d0179050b6ae`
- PR: none
- state: **IMPLEMENTED + TESTED + MEASURED / DROP / NOT QUALIFIED / NOT MERGED**

No Phase-2 production branch is currently qualified or merged.

## 2. Lifecycle state

### Phase 1 / collected-vs-emitted exact BRREG recovery

- **IMPLEMENTED:** yes
- **TESTED:** yes
- **QUALIFIED:** yes
- **MERGED:** yes
- **POST-MERGE GREEN:** yes

Phase 1 is closed.

### Phase 2 / exact website-discovery improvement

- **IMPLEMENTED:** experiment-only strategies only; no new production strategy merged
- **TESTED:** yes, two consumed-cohort screens completed
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

Website reach on consumed Phase-2 reruns is **7–8/100** because live website content/network outcomes drift slightly between runs. The email-domain screen baseline had 8 exact verified websites; this is observed source drift, not a Phase-2 feature gain.

## 4. Phase-2 experiment decisions

### Norid organisation-number domain lookup

Decision: **DROP / DO NOT IMPLEMENT**.

Reason: public lookup rights/purpose restrictions are incompatible with Signalpost production use; anonymous RDAP does not provide an equivalent organisation-number subscriber-domain search path.

### Exact-parent BRREG subunit `hjemmeside` hints

Decision: **DROP**.

- branch: `experiment/phase2-subunit-homepage-screen`
- head: `afe25ce63219c9c0eba532cac8b498fd012a9194`
- run `37208360582`: PASS
- artifact `phase2-subunit-homepage-screen`, ID `11306100222`
- digest `sha256:b856eba533cf5a1ee3eef4e92054fd294878480b4b3f0adc4b88e803f3314ffd`
- 93 unresolved companies; 3 companies had subunit homepage hints; 3 candidates attempted; **0 accepted exact target sites**
- one candidate explicitly identified another organisation number; two failed the existing identity/fetch gate
- screen requests 6 logical / 12 conservative; runtime 6.019 s; $0; wrong-company publications 0

### Exact-parent BRREG subunit email-domain hints

Decision: **DROP**.

- branch: `experiment/phase2-subunit-email-domain-screen`
- exact measured head: `5321ab9689d754bd2f2415f392a8d0179050b6ae`
- workflow run `37209911261`: PASS
- artifact `phase2-subunit-email-domain-screen`, ID `11306935410`
- artifact digest `sha256:fab8b2d62950eea9e5991bcf1cf61512a4532680ddcc9f1330c30ba36b19038e`
- publication enabled: false
- full regressions: PASS
- consumed cohort: exact Phase-A seed-`20261103` 100

Baseline V8 on that run:

- 100/100 terminal; `passed=true`
- exact verified websites: 8/100
- observed logical requests: 666
- conservative charge: 1,332/2,000
- runtime: 439.185 s
- p50 request latency: 571 ms; p95: 2,319 ms
- third-party cost: $0
- search API requests: 0

Email-domain screen:

- exact-parent subunit email rows: 19
- companies with exact-parent subunit email: 19
- unresolved companies with non-generic deduplicated email-domain candidates: 10
- attempted candidates: 10
- accepted exact target sites: **0**
- decisions: 9 existing identity-gate rejects; 1 target-proof reject
- wrong-company publications: 0
- screen logical site requests: 16
- conservative screen charge: 32
- screen runtime: 32.192 s
- screen bytes: 151,186
- third-party cost: $0
- search API requests: 0

Notable case: `AGILE SOLUTIONS AS` at `agilesolutions.no` matched the complete legal name on the homepage but did not contain the predeclared exact organisation-number or registry-location proof. Do **not** weaken the rule post-hoc to accept this consumed example.

## 5. Precision and budget invariants

- exact organisation number remains the legal-entity anchor;
- candidate generation is never publication proof;
- parent/subsidiary/subunit relation alone cannot authorize a website claim;
- wrong-company publication is a hard failure;
- exact-page provenance remains mandatory;
- missing/blocked/ambiguous stays explicit;
- third-party API spend remains $0;
- no paid/search API path is active;
- at most four logical site requests/profile remains the production ceiling;
- new discovery strategies must fit that ceiling by ordering/substitution, never by adding a fifth site request;
- fresh cohorts remain reserved for promotion only after meaningful consumed-cohort transfer.

## 6. Known rejected / do-not-repeat Phase-2 paths

Do not revive without genuinely new evidence:

- guessed `.com` expansion;
- broad rule/ML legal-name candidate ranking with zero net-new exact sites;
- annual-report domain hints after prior zero-yield screen;
- Norid public lookup because rights/purpose terms are incompatible;
- exact-parent subunit homepage hints: 0/3 exact target sites;
- exact-parent subunit email-domain hints: 0/10 exact target sites;
- provider-dependent model/search PRs #78/#84 unless Builderr resolves provider/key/budget and the $0 constraint changes.

## 7. Selected next Phase-2 strategy

Screen **secondary identity verification for BRREG-declared websites that already load but remain quarantined after homepage-only identity assessment**.

Why this is different and bounded:

- the domain is already a registry-declared main-entity website candidate; no new candidate source is introduced;
- current production already spends 2 logical requests on its homepage;
- if that homepage remains ambiguous, production currently spends the remaining 2 site requests on one deterministic H1c guess;
- the experiment will instead substitute one same-domain legal/contact identity page for that H1c attempt, keeping the four-site-request ceiling unchanged;
- use an existing homepage-discovered `identity_links` URL when available; otherwise one deterministic same-domain `/kontakt` fallback for `.no` candidates;
- accept only if the secondary page proves the target by exact organisation number or full legal name + BRREG location and has no conflicting explicit organisation number;
- publication stays disabled during the screen.

## 8. Exact next 1–3 actions

1. Create a new experiment branch from current `main`; do not merge either rejected subunit experiment.
2. On the same consumed 100, select only non-publishable `registry_linked_company_website` records that loaded successfully. Spend at most one secondary-page fetch per selected company, substituting for the current H1c attempt. Measure exact accepted sites and manually audit every accepted/rejected legal-ID case.
3. PROMOTE only with meaningful net-new exact-site coverage, zero wrong-company findings, and a demonstrated four-site-request integration theorem. Otherwise RETUNE/SHELVE/DROP. No fresh cohort yet.

## 9. NEXT

**NEXT: Phase 2 consumed-cohort screen of one same-domain secondary identity page for quarantined BRREG-declared websites. Substitute, do not add, the remaining H1c site slot; publication disabled.**
