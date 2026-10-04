# Signalpost Implementation Log

This is the append-only project history used for cross-chat continuity.

Rules:

- Add an entry only for material work: experiments, qualified milestones, merges, important failures, scoring feedback or roadmap changes.
- Keep entries factual and short.
- Record exact branch/PR/SHA/run IDs where known.
- Never rewrite old failures into successes; preserve why a path was rejected.
- Current actionable state belongs in `docs/CONTINUATION_STATE.md`.

---

## 2026-10-04 — Phase 4 dated-activity evidence hardening passes consumed gate

Status: **IMPLEMENTED + TESTED / MERGE PENDING / NOT FRESH-QUALIFIED / NOT MERGED**

- PR #95: `Phase 4: harden dated activity evidence selection`
- branch: `feature/phase4-activity-date-evidence-hardening`
- measured semantics head: `a220089fccefd63f88555d675194ebefcdd44723`
- release-shaped code/test head before docs-only commits: `a4b8789a746f6e194186db1ea7dd2a40c78bf7b9`
- consumed diff run `37217368930`: PASS
- artifact: `phase4-activity-evidence-consumed-diff`, ID `11308328355`
- artifact digest: `ddcf4e328edab217a016122801f1ad16f4f60c0a80d3e106b09ba5f67ed59da0`
- exact-head Baseline CI `37217488481`: PASS
- full regressions: PASS
- fresh cohort: not consumed by design

What changed:

- page-local publication dates are evaluated by semantic strength instead of concatenated regex order;
- stronger explicit publication metadata wins over generic/dynamic labelled dates;
- equally strong conflicting dates abstain;
- unstructured page text is accepted only when exactly one unique date remains;
- standard CMS placeholder updates such as WordPress `Hello world!` are rejected;
- retained update evidence records the selected extraction method and raw date evidence;
- no new source or network request was added.

Consumed 100-company deterministic diff:

- baseline jobs 0 -> Phase-4 jobs 0;
- baseline updates 0 -> Phase-4 updates 0;
- added update URLs: 0;
- dropped update URLs: 0;
- publication-date changes: 0;
- network requests added: 0;
- third-party cost added: $0;
- search API requests added: 0;
- `precision_monotonic=true`.

Adversarial regressions prove strong publication metadata beats unrelated dynamic dates, same-rank conflicts abstain, multiple weak text dates abstain, unambiguous text dates remain supported and generic WordPress placeholders cannot become company activity.

Decision: **PROMOTE after repository docs + merge/post-merge gate**. A fresh cohort is intentionally not required for this precision-only, zero-request hardening.

---

## 2026-10-04 — Phase 3 hardened RSS/Atom dated-activity screen rejected

Status: **IMPLEMENTED + TESTED + MEASURED / DROP / NOT QUALIFIED / NOT MERGED**

- branch: `experiment/phase3-dated-activity-discovery`
- exact hardened head: `5ed4f3a83eab592c0a2a2c7d96e0865cf874bce0`
- workflow run `37215793652`: PASS
- artifact: `phase3-rss-activity-screen`, ID `11308790825`
- artifact digest: `f2c10fbeb86d0f04bdd8a53e3594bd2aaf2e1ef957ae36eb5bdfd29c41714cde`
- full regressions: PASS
- publication remained disabled
- frozen consumed cohort: 100 companies / 7 exact verified sites

The first RSS run (`37215447605`, artifact `11308540417`) appeared to produce one dated update for `BIKE2WORK AS`, but manual audit found a precision defect: the RSS item was the standard WordPress `Hello world!` placeholder dated 16 Nov 2021 while the detail extractor selected a separate `04/10/2026` date-labelled element on the page.

The experiment was hardened before any promotion:

- standard CMS placeholder posts are rejected;
- feed dates remain ranking/conflict-veto metadata only and can never create a published fact;
- a clear feed-year/detail-year contradiction vetoes an apparent detail fact;
- existing page-local C12 activity acceptance remains the positive evidence gate.

Hardened result:

- 7/7 exact verified sites screened;
- declared feed hints: 2 companies;
- RSS feeds parsed: 2;
- precision-clean dated-activity companies: **0**;
- decisions: 4 no feed hint, 1 no feed activity candidate, 1 robots unavailable, 1 generic CMS placeholder reject;
- actual experiment requests: 16;
- actual bytes: 1,631,210;
- projected production incremental site requests: 3;
- projected combined conservative charge: 1,338/2,000;
- runtime: 13.374 s;
- third-party cost: $0;
- search API requests: 0;
- wrong-company publications: 0.

Decision: **DROP** the current bounded RSS/Atom acquisition path. The experiment exposed a real generic page-date precision weakness, so the next phase is page-level evidence/date hardening before further source expansion.

---

## 2026-10-04 — Phase 3 sitemap dated-activity screen rejected

Status: **IMPLEMENTED + TESTED + MEASURED / DROP / NOT QUALIFIED / NOT MERGED**

- branch: `experiment/phase3-dated-activity-discovery`
- exact measured head: `5f6540fffe5ce3656f2c8611da8cc390409ecddd`
- workflow run `37215062164`: PASS
- artifact: `phase3-sitemap-activity-screen`, ID `11308151116`
- artifact digest: `fcbd1aa10c91b7f468894a81e6fe88d797224fe1d058ac472a4d049f8e800d35`
- publication remained disabled
- frozen consumed cohort: 100 companies / 7 exact verified sites

Measured result:

- robots sitemap hints: 5 companies;
- sitemap indexes: 4;
- direct urlsets: 1;
- accepted dated-activity companies: **0**;
- 4 sitemap indexes would require a child-sitemap request before an article detail and therefore exceed the intended two-idle-request discovery+detail theorem;
- sitemap `<lastmod>` stayed ranking-only and never became publication evidence;
- actual experiment requests: 13;
- projected production incremental requests assuming cached homepage robots policy: 6;
- projected combined conservative charge: 1,344/2,000;
- runtime: 8.614 s;
- cost $0; search API requests 0; wrong-company publications 0.

Decision: **DROP** sitemap-only dated-activity discovery on the current verified-site cohort. RSS/Atom remained the only budget-compatible Phase-3 retune and was screened separately.

---

## 2026-10-04 — NAV exact-org vacancy-feed screen rejected

Status: **IMPLEMENTED + TESTED + MEASURED / DROP / NOT QUALIFIED / NOT MERGED**

- branch: `experiment/nav-exact-org-vacancy-screen`
- exact measured head: `c156fda6a5ac711b285e864270273446262d19ac`
- corrected workflow run `37214017085`: PASS
- artifact: `nav-exact-org-vacancy-screen`, ID `11307433276`
- artifact digest: `917ad28cc991fdeb70a8f78617cbb8c0c1fbbf49e8c6ce598455630127d7e5db`
- first run `37213928445` failed before any NAV request due a harness-only frozen-report key mismatch; full regressions were green and the workflow was corrected without changing matching semantics
- publication remained disabled and personal contact fields were not retained

Measured result:

- complete 180-day feed traversal;
- 38 feed requests, 181,234,775 bytes;
- 368,428 raw feed events;
- 90,917 unique vacancies;
- 9,723 active unique vacancies;
- target/main-or-exact-subunit shortlist candidates: **0**;
- vacancy-detail requests: 0;
- exact active vacancies: 0;
- target companies with exact active vacancies: **0/100**;
- NAV logical requests: 39;
- conservative NAV charge: 78;
- projected combined charge with Phase-A baseline: 1,410/2,000;
- runtime: 62.381 s;
- third-party cost: $0;
- search API requests: 0;
- wrong-company publications: 0.

The detail gate would authorize only `employer.orgnr == target` or an exact BRREG subunit organisation number whose recorded parent is the target. No candidate reached detail lookup. The public experiment token is also not a stable production credential.

Decision: **DROP**. Do not broaden name matching post-hoc or spend a fresh cohort. Reconsider only if NAV feed semantics or an exact organisation-number index materially changes.

---

## 2026-10-04 — Phase 2 same-domain secondary identity screen rejected

Status: **IMPLEMENTED + TESTED + MEASURED / DROP / NOT QUALIFIED / NOT MERGED**

- branch: `experiment/phase2-registry-secondary-identity-screen`
- exact measured head: `03b9ab870c00ac681cbf47ca74a57920e9a76e5f`
- workflow run `37211887561`: PASS
- artifact: `phase2-registry-secondary-identity-screen`, ID `11307036767`
- artifact digest: `b552fe0a4961148a9a0e3dfac520dc9535cfe3171af624cf3efc90a885c59937`
- full regressions: PASS
- publication remained disabled

The experiment selected only loaded, quarantined `registry_linked_company_website` records and substituted one same-domain legal/contact identity page for the remaining H1c slot. Positive proof was hardened to be page-local to the secondary page; split homepage+secondary proof is regression-rejected.

Measured result:

- eligible quarantined registry sites: 4;
- secondary attempts: 4;
- accepted exact target sites: **0**;
- decisions: 1 conflicting explicit organisation number, 1 insufficient target proof, 2 secondary pages unavailable;
- 8 logical / 16 conservative screen charge;
- runtime: 9.468 s;
- third-party cost: $0;
- search API requests: 0;
- request theorem held: existing registry homepage 2 + secondary page max 2 = four site requests.

Manual conflict audit: `VIKHOV B4 BORETTSLAG` at `bonitas.no/personvernerklaering` explicitly identified organisation number `987579773`, not the target.

Decision: **DROP**. Combined with the deterministic-domain DNS failure funnel, Phase 2 is candidate-source constrained under the current $0 rights-safe source set.

---

## 2026-10-04 — Phase 2 exact-parent subunit email-domain screen rejected

Status: **IMPLEMENTED + TESTED + MEASURED / DROP / NOT QUALIFIED / NOT MERGED**

- branch: `experiment/phase2-subunit-email-domain-screen`
- exact measured head: `5321ab9689d754bd2f2415f392a8d0179050b6ae`
- workflow run `37209911261`: PASS
- artifact: `phase2-subunit-email-domain-screen`, ID `11306935410`
- artifact digest: `fab8b2d62950eea9e5991bcf1cf61512a4532680ddcc9f1330c30ba36b19038e`
- full regressions: PASS
- publication remained disabled
- cohort: already-consumed Phase-A seed-`20261103` 100

The experiment retained exact-parent `overordnetEnhet` plus public subunit `epostadresse` from the BRREG locations response already fetched by production, filtered generic mailbox providers with the existing registry-email rules, and independently fetched candidate email domains. Exact parent/subunit relation remained nomination evidence only; acceptance required the target main entity to be proven on the fetched page.

Measured result:

- baseline V8: 100/100 terminal, `passed=true`, 8 exact verified websites, 666 logical requests, 1,332/2,000 conservative charge, 439.185 s, $0, search API requests 0;
- exact-parent subunit email rows: 19;
- companies with exact-parent subunit email: 19;
- unresolved companies with non-generic deduplicated candidate domains: 10;
- attempted candidates: 10;
- accepted exact target sites: **0**;
- decisions: 9 existing identity-gate rejects, 1 target-proof reject;
- wrong-company publications: 0;
- screen logical site requests: 16;
- conservative screen charge: 32;
- screen runtime: 32.192 s;
- screen bytes: 151,186;
- third-party cost: $0;
- search API requests: 0.

Notable consumed case: `AGILE SOLUTIONS AS` at `agilesolutions.no` matched the complete legal name on the homepage but lacked the predeclared exact organisation-number or registry-location corroboration. The gate was not weakened post-hoc.

Decision: **DROP**. Do not integrate or fresh-qualify this candidate path. Next Phase-2 screen targets one same-domain secondary identity page for BRREG-declared websites that already load but remain quarantined; the secondary request must substitute for the current failed H1c attempt so the four-site-request ceiling is unchanged.

---

## 2026-10-04 — Phase 2 exact-parent subunit homepage screen rejected

Status: **IMPLEMENTED + TESTED + MEASURED / DROP / NOT QUALIFIED / NOT MERGED**

- branch: `experiment/phase2-subunit-homepage-screen`
- exact measured head: `afe25ce63219c9c0eba532cac8b498fd012a9194`
- workflow run `37208360582`: PASS
- artifact: `phase2-subunit-homepage-screen`, ID `11306100222`
- artifact digest: `b856eba533cf5a1ee3eef4e92054fd294878480b4b3f0adc4b88e803f3314ffd`
- full regressions: PASS
- cohort: already-consumed Phase-A seed-`20261103` 100

The experiment retained `hjemmeside` and `overordnetEnhet` from the BRREG underunit/location response that production already fetches, then independently screened only exact-parent subunit homepage hints against the target main entity.

Measured result:

- baseline exact verified websites: 7/100;
- unresolved website companies: 93;
- companies with subunit homepage hints: 3;
- candidate attempts: 3;
- accepted exact target sites: **0**;
- one candidate (`bonitas.no` for target `VIKHOV B4 BORETTSLAG`) explicitly identified a different organisation number and was correctly rejected;
- two other candidates failed the existing identity gate / fetch requirement;
- wrong-company publications: 0;
- screen logical site requests: 6;
- conservative screen charge: 12;
- runtime: 6.019 s;
- third-party cost: $0;
- search API requests: 0.

Decision: **DROP**. Do not integrate this candidate path or spend a fresh cohort. Next Phase-2 screen: exact-parent subunit email-domain hints from the same already-paid BRREG locations response, using existing generic-email filtering and exact-page target-company verification.

Norid organisation-number domain lookup was also screened conceptually and rejected before implementation because its public lookup terms/purpose restrictions are incompatible with Signalpost production use.

---

## 2026-10-04 — Phase A exact-live BRREG breadth merged and post-merge green

Status: **QUALIFIED + MERGED + POST-MERGE GREEN**

- PR #94: `Phase A: exact-live BRREG zero-request breadth recovery`
- branch: `feature/phaseb-idle-contact-enrichment`
- qualified measurement head: `a7192c4fe9f47e26fcc2a0d3b632e86a1586cfe0`
- cleaned branch reconciled with new main roadmap using merge head `d36ea6edefc58e38ad656042d93c6a409c4f02e7`
- exact-head Baseline CI `37205694426`: PASS
- merge commit: `8a729036350c019e107cd68a08641f1fff6796f6`
- post-merge Baseline CI `37205739214`: PASS

The one new `main` commit before merge (`ea79bf6283497dd991a9a106d7dffb8f3001d418`, Phase 0–11 roadmap) was preserved exactly during reconciliation. Final PR scope contained only continuation/history docs, `official.py`, `v2_registry_projection.py`, `canonical_projection.py`, and two focused Phase-A regression files.

Retained production behavior: exact-live BRREG postal address, foundation/articles dates, Foretaksregisteret state/date, institutional sector, registered capital, VAT state/date and forced-dissolution status, all with exact source lineage and zero added source requests.

Fresh qualification evidence remained run `37203580574`: 100 unique companies, 0 overlap after 8,323 exclusions, 100/100 terminal, zero evidence/contract/canonical/synthesis errors, 666 logical requests, 1,332/2,000 conservative charge, 460.916 s, $0, search requests 0. Artifact `phasea-final-fresh-disjoint-100-v2`, ID `11304401011`, digest `31e12e11f2746dcf8c0b6454ab6052ab44281176363b6934889d22d57a08800b`.

The external homepage-phone feature and idle contact-page network fallback remain rejected. The homepage-phone feature was precision-correct but added zero net-new phone-family companies on both fresh cohorts, so it was removed before merge.

Decision: **PROMOTE complete**. Phase 1 / collected-vs-emitted exact BRREG recovery is closed. Next architecture stage: Phase 2 exact website-discovery improvement.

---

## 2026-10-04 — Phase A exact-live BRREG breadth fresh-qualifies; duplicate external-phone feature dropped

Status: **QUALIFIED / RELEASE CLEANUP / NOT YET MERGED**

Active PR: #94, branch `feature/phaseb-idle-contact-enrichment`.

Second untouched qualification:

- exact measurement head: `a7192c4fe9f47e26fcc2a0d3b632e86a1586cfe0`;
- run `37203580574`: PASS end-to-end;
- failed seed-`20261102` cohort was included in the exclusion before selection;
- all-touched exclusion: 8,323 unique companies;
- exclusion SHA `ae5a1e78a883d75332d93bd0cd88f123e7f1a88300ee3d795067fc73c4cb2f85`;
- seed `20261103`;
- fresh cohort 100 unique, overlap 0;
- cohort SHA `4078579d4a581da0b8d56e4d03d567c4032d43e93c8bb94ee3c02b140b651e40`;
- coverage / 100: forced dissolution 100, foundation 100, articles date 99, Foretaksregisteret state 100/date 98, sector 100, capital 98, VAT state 100/date 48, postal address 23, registration date/address 100;
- V8 passed, 100/100 terminal;
- evidence / contract / canonical / synthesis errors: 0;
- observed logical requests 666;
- conservative charge 1,332/2,000;
- runtime 460.916 s;
- third-party cost $0;
- search requests 0;
- artifact `phasea-final-fresh-disjoint-100-v2`, ID `11304401011`, digest `31e12e11f2746dcf8c0b6454ab6052ab44281176363b6934889d22d57a08800b`.

Decision: retained exact-BRREG/postal Phase-A behavior **QUALIFIES**.

External homepage phone transfer decision:

- consumed Phase-1 cohort had +2 net-new phone-family companies;
- first fresh cohort had 3 external-phone companies but registered phone/mobile union 38 and combined union still 38 -> 0 net-new;
- second fresh cohort had 1 external-phone company but registered phone/mobile union 33 and combined union still 33 -> 0 net-new;
- fresh case `VEST GULV AS` (`924516941`) was precision-correct; homepage explicitly showed `Tel: +47 22 20 11 70`, but exact BRREG live already carried the same registered phone.

Decision: **DROP** external homepage phone from PR #94 before merge because the consumed gain did not transfer at company-family level. Restore email-only external-contact code, remove phone tests/canonical mapping, and remove one-off consumed/fresh workflows from merge scope. This is a monotonic scope reduction after qualification.

Next: exact-head CI on the cleaned branch; if green, retitle/mark PR #94 ready, merge, then verify post-merge `main` CI.

---

## 2026-10-04 — Phase A3 zero-request breadth passes consumed gate; first final fresh qualification fails optional postal floor

Status: **IMPLEMENTED + TESTED / FIRST FRESH QUALIFICATION FAILED / NOT MERGED**

Active PR: #94, branch `feature/phaseb-idle-contact-enrichment`.

Phase A3 consumed gate:

- exact measured head: `ddd35f0679a9b05bdea5a26cd1b5b8f83a1fc59f`;
- run `37200794754`: PASS;
- artifact `phasea3-consumed-e2e`, ID `11302927164`;
- digest `9c7b0014d0e08686f6801e541411da8141a36d331500cd9ca11c6f181e258578`;
- 100/100 terminal;
- company coverage: forced dissolution 100, foundation 98, articles date 96, Foretaksregisteret state 100/date 98, sector 95, capital 91, VAT state 100/date 48, postal address 30;
- external labelled homepage phone 1, external email 3, registered phone/mobile 29, combined phone family 30;
- evidence / contract / canonical / synthesis errors 0;
- 669 logical requests, 1,338 conservative charge, theoretical ceiling 2,000;
- runtime 473.27 s; cost $0; search requests 0.

Before fresh qualification, branch ancestry was reconciled with live `main` `1589e4c5fd8c9cdc44e28574c961ee1912e47bf9` using merge commit `0b0c8e154bf6ac7391f1a01316f739cc9ff3892c`.

First final fresh attempt:

- exact head: `525b80126ac48e8662886422fbb606cce29e2a20`;
- Baseline CI `37201687696`: PASS;
- qualification run `37201683517`;
- seed `20261102`;
- exact exclusion: 8,223 unique, SHA `4ed34945be5f6363a287487fd32ea87b47ab43445a22e2378a32f31695cf94ae`;
- fresh cohort: 100 unique, overlap 0, SHA `f74aed4f1c3a389e2a88699f2df02edb01815c1f81cf87d6858cc276dacd5c29`;
- V8 evaluator execution: PASS, 100/100 terminal;
- fresh coverage: forced dissolution 100, foundation 99, articles date 97, enterprise state 100/date 98, sector 100, capital 93, VAT state 100/date 57, postal address 17, registration date 100, business address 100;
- external homepage phone 3, external email 7, registered phone/mobile 38;
- contract/canonical/synthesis/budget errors: 0;
- 702 observed logical requests, 1,404 conservative charge, theoretical ceiling 2,000;
- runtime 451.153 s; cost $0; search requests 0;
- artifact `phasea-final-fresh-disjoint-100`, ID `11302933473`, digest `44045fa0727fb3fab5e79f7721e706d4a2a0cf2478644f3f61983291def12aa0`.

Qualification result: **FAIL**. The only failed promotion assertion was `postal_address >= 20`; actual untouched-cohort prevalence was 17. The production path, exact evidence checks, evaluator, budget and output validations were otherwise clean.

Decision:

- do not retroactively relabel the failed run as qualified;
- treat seed `20261102` cohort as consumed;
- retune validation criteria so broad near-universal fields retain strong floors, while optional source-prevalence fields are reported/exact-evidence audited rather than universal hard floors;
- next untouched exclusion is 8,323 unique companies, SHA `ae5a1e78a883d75332d93bd0cd88f123e7f1a88300ee3d795067fc73c4cb2f85`;
- run a second untouched cohort with seed `20261103`; only a green second fresh gate can qualify PR #94.

---

## 2026-10-04 — Phase A audit found more zero-request BRREG recall; idle contact-page fallback rejected

Status: **AUDITED + TESTED CANDIDATE / NETWORK EXPERIMENT REJECTED / NOT QUALIFIED**

Active PR: #94, branch `feature/phaseb-idle-contact-enrichment`.

Measured candidate lineage:

- exact consumed Phase-1 E2E head: `74527e8d072bd1456b11ba55dc3d85c27f75ac0f`;
- Baseline CI `37196448235`: PASS;
- consumed Phase-1 E2E `37196444699`: PASS;
- artifact `phaseb-consumed-e2e`, ID `11300583926`;
- artifact digest `fe0eee5d099c9128ab24cce616a7f4c7c3884ddebd5934889c56a879187c5c70`.

Candidate result on frozen 100:

- postal address available: 30 companies;
- external labelled homepage phone: 2 companies;
- registered phone/mobile + external-phone union: 31 vs 29 baseline, +2 net-new companies;
- contract/canonical/synthesis errors: 0;
- logical requests 673;
- conservative charge 1,346/2,000;
- cost $0; search requests 0.

A deeper collected-vs-emitted audit found additional broad exact BRREG fields still dropped before projection: foundation date (~98/100), Foretaksregisteret registration date (~98/100), statutes date (~96/100), institutional sector (~95/100), capital (~91/100), enterprise-register state (100/100), VAT state (100/100) and VAT registration date (~48/100). Decision: Phase A remains open; implement these exact-live zero-request facts before consuming a fresh promotion cohort.

Idle network contact-page experiment:

- measured head: `e80577f1e846dcfa8252132017e9f949e0acb7d7`;
- workflow `37197243641`;
- V8 execution: PASS, 100/100 terminal;
- promotion assertion: FAIL;
- one contact-surface phone company `977117186`, but it was not net-new at company contact-family level;
- logical requests 679 before V5 wrapper / 680 combined;
- conservative charge 1,358 before V5 wrapper / 1,360 combined;
- runtime 438.254 s;
- cost $0; search requests 0;
- artifact `phaseb-m5-consumed-transfer`, ID `11302125123`, digest `448635d91a6d141771cd116d54e15222327434f1671597c19c5e7e3d19a6cd2d`.

Decision:

- **DROP** the idle contact-page network fallback because it failed the roadmap promotion bar of measurable net-new company coverage.
- Restore bounded Wikidata behavior; remove the M5 transfer workflow and contact-surface-specific tests.
- Keep the exact-live postal-address projection and continue Phase A2 exact-live BRREG zero-request recovery.

---

## 2026-10-04 — Phase 1 exact BRREG lost-claim recovery merged

Status: **QUALIFIED + MERGED + POST-MERGE GREEN**

- PR #92: `Phase 1: recover evaluator-visible exact BRREG claims`
- branch: `phase1/lost-claim-registry-live`
- qualified semantics head: `381a370e36b2e40b36f48e405c5b122191cb199c`
- merge commit: `911ecef4f785bb5f2b5aa7cf75a52efd6f7c3051`
- qualification run: `37192494569`
- artifact: `phase1-fresh-disjoint-100`, ID `11299633898`
- artifact digest: `812941edf79709cc2324b907d9efc4b889fc56ee7df9e095bfad2890a9ba5f3d`
- post-merge Baseline CI: `37193327713`, PASS

What changed:

- retained exact-live BRREG registration date, activity, registered purpose, email, phone and mobile instead of discarding them during normalization;
- projected registration date, registered business address and registered contact fields with exact live source-field lineage;
- allowed registry narrative projection from exact-live `aktivitet` / `vedtektsfestetFormaal` with BRREG array cleanup;
- exposed registration date, registered address, registered purpose and registered contact fields in canonical company facts;
- added fail-closed exact-evidence, narrative-array, canonical and idempotence regressions.

Fresh 100-company results vs same-cohort baseline:

- company description: **100 vs 14**;
- registered purpose: **96 vs 0**;
- registration date: **100 vs 0**;
- registered address: **100 vs 0**;
- registered email: **21 vs 0**;
- phone: **17 vs 0**;
- mobile: **16 vs 0**;
- terminal outputs: 100/100;
- evidence audit: 100 rows, 0 errors;
- output-contract errors: 0;
- canonical errors: 0;
- synthesis errors: 0;
- logical requests: 669;
- conservative charge: 1,338/2,000;
- runtime: 449.589 s;
- third-party cost: $0;
- search requests: 0.

Decision: GO. This demonstrated material evaluator-visible recall increase with no new source/request by recovering facts already present in exact official evidence.

---

## 2026-10-04 — C12 M4 current first-party jobs merged

Status: **MERGED + POST-MERGE GREEN**

- PR #90: `feat(c12): qualify current first-party job surfaces`
- branch: `feature/c12-current-first-party-jobs`
- qualified head: `c474be97e47ea19613b4301f027f1c03da86c858`
- merge commit / production main at time of entry: `fb4c8711b9a3c58c16c6ff1c26aada93c036938a`
- post-merge Baseline CI: run `37183602277`, PASS
- live proof run: `37183411443`
- proof artifact: `c12-m4-live-proof`, artifact ID `11295658686`
- proof digest: `b51f1ea151329ef3ad98f1c6f66ae09ced0b5d6aaa699e132312b580cac7fe4c`

What changed:

- explicit homepage vacancy-count signal can spend the bounded careers follow-up slot;
- generic careers page remains non-job evidence;
- company-owned role cards / `JobPosting` can produce concrete current jobs;
- specific role/application URL and exact employer context are required;
- expired roles abstain;
- parent targets do not inherit subsidiary jobs;
- C12 M3 news remains fallback when careers follow-up is not warranted;
- four-logical-site-request ceiling preserved;
- $0 third-party API spend preserved.

Decision: GO; merged after exact-head CI and live positive/negative proofs.

---

## 2026-10-04 — 70+ continuity system introduced

Status: **DOCUMENTATION BRANCH**

Branch: `docs/70-plus-continuation-system`.

Added `docs/70_PLUS_IMPLEMENTATION_PLAN.md`, `docs/CONTINUATION_STATE.md`, and `docs/IMPLEMENTATION_LOG.md` so repository state, not conversation history, governs continuation.
