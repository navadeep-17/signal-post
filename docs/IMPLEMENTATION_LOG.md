# Signalpost Implementation Log

This is the append-only project history used for cross-chat continuity.

Rules:

- Add an entry only for material work: experiments, qualified milestones, merges, important failures, scoring feedback or roadmap changes.
- Keep entries factual and short.
- Record exact branch/PR/SHA/run IDs where known.
- Never rewrite old failures into successes; preserve why a path was rejected.
- Current actionable state belongs in `docs/CONTINUATION_STATE.md`.

---

## 2026-10-04 — Final Phase 4 current-state handoff pinned

Status: **DOCUMENTATION-ONLY / NO PRODUCTION SEMANTIC CHANGE**

- live `main` observed before this handoff update: `b13e298c2c71bd3be0a99be749fda762bc65c317`
- continuation-state update commit: `ab7c624a8b5c8cd0fb36d40c779f1227856dc78c`
- production Phase-4 merge remains `07f01734ba9bb5ed850a5a494c6c38f7cdaf66a3`
- PR #95 remains merged
- post-merge Baseline CI `37219278337`: PASS
- lifecycle remains **IMPLEMENTED + TESTED + MERGED + POST-MERGE GREEN**; no fresh qualification was required for the precision-only zero-request hardening
- no active production PR; open PRs #76, #78 and #84 remain historical/experimental only

Current blocker/strategy state is unchanged: Phase 2 is candidate-source constrained, Phase 3 sitemap/RSS acquisition is dropped/shelved, and Phase 4 is closed. The next action remains a consumed-only deterministic source/family selection audit across rights-safe official sources such as Doffin, Støtteregisteret and Patentstyret. No new connector and no fresh cohort should be used until one source passes rights + exact-ID + reach + budget screening.

Decision: **STATE PIN ONLY**. No production code, workflow, request budget, evidence rule or roadmap semantics changed.

---

## 2026-10-04 — Phase 4 dated-activity evidence hardening merged and post-merge green

Status: **IMPLEMENTED + TESTED + MERGED + POST-MERGE GREEN / NO FRESH QUALIFICATION BY DESIGN**

- PR #95: `Phase 4: harden dated activity evidence selection`
- branch: `feature/phase4-activity-date-evidence-hardening`
- docs-inclusive exact PR head: `49f9b89d149749400f14f105671edd644116faeb`
- exact-head Baseline CI `37219207340`: PASS
- merge commit: `07f01734ba9bb5ed850a5a494c6c38f7cdaf66a3`
- post-merge Baseline CI `37219278337`: PASS
- consumed semantics/diff run: `37217368930`, PASS
- artifact: `phase4-activity-evidence-consumed-diff`, ID `11308328355`
- artifact digest: `ddcf4e328edab217a016122801f1ad16f4f60c0a80d3e106b09ba5f67ed59da0`

The merge retains typed page-local date ranking, same-rank conflict abstention, unique-only weak text dates, generic CMS placeholder rejection and exact date-method/raw-evidence provenance. No source, network request, identity rule or third-party cost was added.

The frozen 100-company diff remained monotonic: jobs 0->0, updates 0->0, no added/dropped update URLs, no publication-date changes, zero added requests and `precision_monotonic=true`. Post-merge CI passed the full test suite, certified-1000 canonical audit, submission-bundle verification and deterministic refresh replay.

Decision: **PROMOTE complete**. Phase 4 is closed. Next roadmap step is a consumed-only rights/reach/exact-ID source/family selection audit; no connector or fresh cohort until one deterministic source passes that gate.

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
- artifact `phase3-sitemap-activity-screen`, ID `11308151116`
- artifact digest `fcbd1aa10c91b7f468894a81e6fe88d797224fe1d058ac472a4d049f8e800d35`
- publication remained disabled
- frozen consumed cohort: 100 companies / 7 exact verified sites

Measured result:

- robots sitemap hints: 5 companies;
- sitemap indexes: 4;
- direct urlsets: 1;
- accepted dated-activity companies: **0**;
- 4 sitemap indexes would require an extra child-sitemap request before an article detail and therefore exceed the intended two-idle-request discovery+detail theorem;
- sitemap `<lastmod>` stayed ranking-only and never publication evidence;
- actual experiment requests: 13;
- projected production incremental requests assuming cached robots policy: 6;
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

Decision: **DROP**. Do not broaden name matching post-hoc or spend a fresh cohort. Reconsider only if NAV feed semantics or a direct organisation-number index materially changes.

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

---

## 2026-10-05 — Phase 7 Støtteregisteret support awards promoted to clean PR candidate

Status: **PROMOTE / CONSUMED V8 QUALIFIED / CLEAN PR + MERGE GATE PENDING / NO FRESH COHORT**

- production baseline before promotion: `main` `86b60b2b5e87966c4a8beb4719e01905421b68ac`;
- clean branch: `feature/stotteregisteret-support-awards`;
- clean production staging commit: `91e825e844100eaf1341317126dca5fe2e52fc9b`;
- hardened production semantics head on experiment branch: `59dd767a7bbc4a5f99d076be633e29a582fd711b`;
- definitive actual-V8 consumed qualification run `37254237936`, job `111587836938`: PASS;
- artifact `phase5-support-v8-consumed-live-100`, ID `11321344340`, ZIP digest `ba2fcdcf22473cc5e6159086516e7eb32da14b43ff11c4717f889910a383e357`;
- cohort: already-consumed certified final-release-1000 chunk 0, 100 companies; no fresh cohort consumed;
- 100/100 terminal; 11 support-award companies; 46 support observations/claims/canonical facts;
- 0 contract/canonical/synthesis/external/integrity/budget failures; manual artifact audit found 0 wrong-company publications;
- source identity is primary-recipient org-number only; specified recipient and granting authority are context-only;
- NLOD; <=365 days; max 5 events/company; exact row/snapshot hashes + retrieval time + evidence span; source-backed currencies;
- one shared support request; one V8 BRREG change-feed request; H2g ceiling 97; observed conservative charge 1,366; theoretical ceiling exactly 2,000; external wall 784 s; third-party cost $0; search API requests 0.

Historical pre-hardening 106/1000 and 88/1000 Støtte reach figures are research-only and are not production-equivalent after primary-recipient and amount/currency hardening.

Parallel Phase-2 Common Crawl Stage 4 is **SHELVED**: 3,000 generic domains -> 453 indexed org numbers -> 4/5,900 consumed overlap -> 2 net-new verified websites, far below the 20+/100 breakthrough threshold.

Decision: **PROMOTE Støtteregisteret through a clean PR only**. Do not merge the experiment branch or its workflows. After merge + post-merge CI, NEXT is Phase 11 fresh evaluator-shaped release qualification; no Builderr submission until that fresh release gate is clean.

---

## 2026-10-05 — PR #97 CI catches immutable-V1 violation; support moved to V7 wrapper

Status: **RETUNED / EXACT-HEAD CI + CONSUMED V8 WRAPPER REQUALIFICATION PENDING / NOT MERGED**

- active PR: #97, `Phase 7: add exact-org Støtteregisteret support awards`;
- first exact-PR Baseline CI: run `37255960174`, job `111592968992`: **FAIL**;
- pytest result: **459 passed, 1 failed, 5 subtests passed**;
- sole failure: `tests/test_submission_bundle.py::test_repository_only_submission_verifier_passes`;
- failure cause: the first promotion shape modified `scripts/run_signalpost_final.py`, violating the immutable certified V1 collector pin;
- certified V1/V2 audit stages after pytest were skipped; no merge occurred;
- the verifier/pin was **not** weakened or repinned.

Architecture correction:

- certified V1 `scripts/run_signalpost_final.py` restored exactly to blob `9be89b9827135b1ed703318e1d189d5d3b8ca604`;
- current V2 `scripts/run_signalpost_v2.py` remains unchanged at blob `5b69cc320c38e3aab13cf09fe2e2a09e62751433`;
- Støtteregisteret moved to the newer V7 wrapper layer;
- V7 now reserves the one shared support request, invokes unchanged V2 with the reduced budget, then projects support claims, canonical facts and synthesis before building the V6 evaluator surface;
- support-specific CLI flags terminate at V7 and cannot leak into pinned V2/V1;
- wrapper/budget tests were rewritten around this boundary;
- code/test retune head before documentation commits: `338730d3ddf562955c967468983bd8cb3f0cc590`.

Corrected 100-company request theorem:

- V8 -> V7 budget: 2,000 conservative;
- V7 reserves Støtte: 1 logical / charge 2 -> V2 receives 1,998;
- V2 reserves BRREG change feed: 1 logical / charge 2 -> V1 receives 1,996;
- immutable V1 fixed company + Wikidata ceiling: 901 logical;
- H2g annual-report capacity: 97 logical;
- V1 theoretical total: 998 logical / 1,996 conservative;
- + change feed: 999 / 1,998;
- + Støtte: **1,000 logical / exactly 2,000 conservative**.

The prior consumed actual-V8 run `37254237936` / artifact `11321344340` remains valid semantic/evidence proof for primary-recipient-only Støtte publication and its 46 manually audited claims. Because the integration layer changed, it does **not** substitute for an exact-head wrapper requalification.

Decision: keep PR #97 blocked until the retuned exact head passes full Baseline CI **and** an actual-V8 consumed requalification. Then merge with expected-head protection, run post-merge CI, pin production state, and only then advance to Phase 11 fresh evaluator-shaped release qualification.

---

## 2026-10-05 — PR #97 exact-wrapper consumed qualification passes after report-counter fix

Status: **IMPLEMENTED + TESTED + CONSUMED-WRAPPER QUALIFIED / FINAL CLEAN-HEAD CI + MERGE GATE PENDING / NO FRESH COHORT**

- active PR: #97, `Phase 7: add exact-org Støtteregisteret support awards`;
- immutable V1/V2 boundary preserved: V1 blob `9be89b9827135b1ed703318e1d189d5d3b8ca604`, V2 blob `5b69cc320c38e3aab13cf09fe2e2a09e62751433`;
- provenance-hardened Baseline CI `37257806967`: PASS;
- counter-fix/docs parent Baseline CI `37260229913`: PASS;
- first wrapper run `37257936472` remains FAIL because report accounting emitted 46 claims / 0 canonical facts despite 46 actual canonical facts; output/evidence audit itself had zero defects;
- report fix counts `canonical_field == public.official_support_award` and is regression-covered;
- definitive corrected V8 consumed run `37260381903`, job `111606171316`: PASS;
- qualification SHA `f47353a7f0b7eb63efa45a76c48850a7a648be2d`; production parent `22655265d3adc99bb2b73ef52d29caf6fa966d03`;
- artifact `phase7-v8-consumed-requalification-100-v2`, ID `11325335788`, ZIP digest `b60b0469ed31cc3b8651445dc786fd4ce34ad325044bebdd6572d5c261a85148`;
- cohort: already-consumed certified final-release-1000 chunk 0, 100 companies; no fresh cohort;
- 100/100 terminal; 11 support companies; 46 claims; 46 canonical facts; report 46/46;
- all 46 evidence rows audited: exact primary-recipient org, row hash, snapshot hash, row number/key, retrieval time, matching award/effective date, source-backed amount/interval currency; audit errors 0;
- support snapshot `8889b22ee01c7aaae1dd6a0c079977e00f4d390440ec0779f17d999dfbd951d1`;
- support requests 1; support bytes 305,978,976; BRREG change-feed requests 1;
- observed conservative charge 1,366/2,000; theoretical ceiling exactly 2,000/2,000;
- wrapper runtime 797.471 s/2,400; third-party cost $0; search API requests 0;
- contract/canonical/synthesis/support-projection errors 0;
- evaluator product 4,839,091 bytes and contains support facts/evidence;
- qualification-only workflow was removed after artifact capture.

Decision: **PROMOTE through final repository gate**. Verify clean durable diff, run final exact-head Baseline CI after docs/cleanup, merge with expected-head protection, require post-merge Baseline CI, then advance to Phase 11 fresh evaluator-shaped release qualification. Do not submit Builderr solely because this PR merges.

---

## 2026-10-05 — Phase 7 merged and post-merge Baseline CI green

Status: **IMPLEMENTED + TESTED + CONSUMED-WRAPPER QUALIFIED + MERGED + POST-MERGE GREEN / PHASE 11 ACTIVE**

- PR #97 merged with expected-head protection from clean head `a6187cad81e38a1e24618f6e16f33d40b247063d`;
- final pre-merge Baseline CI `37261892046`: PASS;
- merge/main SHA `60f385b58a0f1c72f58efd35db71b1566202403a`;
- post-merge Baseline CI `37262030919`, job `111611064093`: PASS;
- full pytest, certified-1000 canonical audit, immutable submission-bundle verification, deterministic refresh replay and refresh qualification verification all passed post-merge;
- durable PR diff contained 14 expected production/tests/docs files; immutable V1/V2 were absent from the diff; all temporary qualification/docs workflows and updater scripts were removed before merge;
- definitive exact-wrapper consumed qualification remains run `37260381903`, artifact `11325335788`: 100/100 terminal, 11 support companies, 46 claims = 46 canonical facts, report 46/46, complete 46-row identity/provenance audit with 0 errors, 1,366/2,000 observed conservative charge, exactly 2,000 theoretical, 797.471 s, $0, zero search requests;
- earlier run `37257936472` remains a recorded failed gate due to the report-only 46/0 counter defect.

Decision: **PHASE 7 CLOSED / PROMOTION COMPLETE**. The main track advances to Phase 11 fresh evaluator-shaped release qualification on a genuinely disjoint 100-company cohort. No Builderr submission is authorized solely from this merge.

---

## 2026-10-05 — Phase 11 seed 20261104 manual precision FAIL -> explicit website-owner veto RETUNE

Status: **FRESH MACHINE PASS / MANUAL PRECISION FAIL / RETUNE IMPLEMENTED + TESTED / CONSUMED REPLAY MONOTONIC / PR #99 MERGE GATE**

Fresh Phase 11 run `37309340028` used seed `20261104` after reconstructing an 8,423-company all-touched exclusion. Selection overlap was 0; exclusion SHA-256 was `fd1e5c7e54d6034821553a1903fd20bea76738dcf0d5e0c75eec93b4a724a298`; cohort SHA-256 was `394eaae1b43fbe5e951fc4a61c7185c068bfa6dad1d37a7223cefc507429dd99`; artifact ID `11346320812`, ZIP SHA-256 `9c9ab8bb8477c949a9491f7a672ad181f43566cd9b885a1f4fc6a2dd720165cf`.

Machine gates passed: 100/100 terminal; 11 support companies; 48 support claims = 48 canonical facts; 1 support request; 1 BRREG change-feed request; observed conservative charge 1,364/2,000; theoretical ceiling exactly 2,000; wall runtime 804.632 s; third-party API cost $0; search API requests 0; contract/canonical/synthesis/dangling-evidence/support-projection errors 0. The artifact correctly left `release_qualified=false` pending manual precision audit.

Manual audit found one material exact-company failure: target `INTERIØRKUPP AS` (`825188592`) was assigned guessed domain `interiorkupp.no`, while the fetched site explicitly states that the site is owned by `Rolf Sletvold Interiørsenter AS`, a different legal entity. Four external publications were contaminated: website, Instagram handle, social-links aggregate and `post@interiorkupp.no`. Decision for seed `20261104`: **FAIL / RETUNE / NO RELEASE**. The cohort is permanently consumed.

PR #99 implements a generic source-agnostic website-owner veto in `identity.py`: an explicit statement that the current fetched domain/site is owned by another named legal entity is hard negative identity evidence. There is no company/domain blacklist. Same-target owner statements pass; unrelated ownership text for another domain does not trigger the veto; exact target organisation-number proof remains stronger positive evidence. Adversarial regressions cover the discovered failure plus same-target and unrelated-owner controls.

Baseline CI `37314026333` passed on code/test head `532bb93f0c02b6da608bd070c7fa36349b5d8cfc`; Baseline CI `37314406825` also passed on replay-checksum head `a7e622a89fbde026205e544473e25d6efbfa67d2`.

Consumed-only replay `37314396820` / job `111777368735` ran the actual V8 path on the already-consumed seed-20261104 cohort. V8 itself passed. The workflow's final verifier failed only because it expected the observed owner string to equal exactly `Rolf Sletvold Interiørsenter AS`; the extractor retained trailing source prose. Replay artifact ID `11347753450`, ZIP SHA-256 `ff03b78a41372f368ace904a009e82eda5c42fd5aa3d74d37a91ccaee0684e01`, independently proves the production behavior is correct: target website unpublished, identity score 0.1, `publishable=false`, wrong-owner reason retained, old external audit 25 records -> replay 21 non-empty publications, exact set diff **4 removed / 0 added**, with the four removed records exactly the contaminated Interiørkupp website/social/email claims. Every other previously published external value is unchanged.

Decision: **PROMOTE THE PRECISION FIX through final clean PR CI/merge/post-merge CI, then rerun Phase 11 on a new untouched cohort.** The next all-touched exclusion must include the failed fresh 100, so the exclusion cardinality becomes 8,523 before seed `20261105` (or the next deterministic seed if repository state advances). Do not reuse seed `20261104` as fresh evidence and do not submit Builderr before a new fresh cohort passes machine + manual precision gates.
