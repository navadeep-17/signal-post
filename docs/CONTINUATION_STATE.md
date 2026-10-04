# Signalpost — Current Continuation State

Last updated: 2026-10-04

This is the **first file every new implementation chat must read**. It is intentionally short and current. Historical detail belongs in `docs/IMPLEMENTATION_LOG.md`; strategy belongs in `docs/70_PLUS_IMPLEMENTATION_PLAN.md`.

## 1. Current source of truth

Repository: `navadeep-17/signal-post`

Production branch: `main`

Current production `main` SHA:

`fb4c8711b9a3c58c16c6ff1c26aada93c036938a`

Latest merged PR:

- PR #90 — `feat(c12): qualify current first-party job surfaces`
- merge commit: `fb4c8711b9a3c58c16c6ff1c26aada93c036938a`

Post-merge Baseline CI:

- run `37183602277`
- status: **PASS**

Do not infer state from older chat messages if GitHub disagrees with this file.

## 2. Current Builderr snapshot

Verified from the live Builderr challenge page on 2026-10-04:

- scoring: 50 recall / 30 precision-evidence / 12 synthesis / 8 UX;
- qualification: >=65 overall on an official run;
- public board reviewed 2026-10-03;
- Navadeep public-board entry shown there: **52.41/100** = 12.83 recall + 26.92 evidence + 9.46 synthesis + 3.20 UX;
- current board leader shown there: 60.51/100;
- 0 qualified at that review point;
- up to five total versions: first submission + four revised commit hashes.

Important: the public-board score can correspond to an older submitted SHA. It does **not** prove the current `main` score.

Internal next-major-revision target:

- recall 22-24+
- evidence 28-29+
- synthesis 12
- UX 8
- total 70-73+

## 3. What is already productionized

### Official / canonical foundation

- exact organisation-number identity anchor;
- BRREG live/bulk data;
- financials;
- roles;
- locations/workplaces;
- group/registry context where available;
- canonical claims + evidence;
- availability states;
- deterministic refresh/change tracking;
- one terminal envelope/company;
- output-contract projection;
- request/runtime/cost accounting.

### Website discovery and identity

Production includes hardened:

- registry website handling;
- registry-email-domain discovery;
- deterministic `.no` discovery;
- legal/contact identity corroboration;
- exact-org Wikidata website candidate path;
- hyphenated `.no` fallback;
- parked/hosting/service-provider/parent/franchise/namesake conflict guards.

Publication remains fail-closed.

### External facts already productionized

- verified company-declared social handles;
- first-party contact emails;
- registry workforce snapshots;
- official annual-report OCR workforce snapshots;
- annual-report business/company description fallback;
- C12 current first-party social provenance improvements;
- C12 bounded dated first-party news detail;
- C12 bounded current first-party job postings.

## 4. Latest completed milestone — C12 M4 jobs

PR #90 is merged.

Production behavior:

- generic careers page is **not** a job posting;
- careers follow-up is only spent when an exact verified homepage exposes an explicit positive vacancy-count signal;
- current company-owned role cards / `JobPosting` evidence can materialize specific jobs;
- job publication requires exact employer context and a concrete role/application URL;
- expired jobs abstain;
- parent targets cannot inherit subsidiary jobs;
- third-party ATS URLs may be carried only as action URLs, not employer identity proof;
- C12 M3 news remains the fallback when no qualified careers follow-up is justified;
- site ceiling remains four logical site requests/profile;
- third-party API cost remains $0.

Live proofs used for M4:

- Granne `838797172`: exact site, vacancy count 0, no wasted careers follow-up, 0 jobs.
- AF GRUPPEN ASA `938702675`: exact site, homepage vacancy count 31, bounded careers surface, current jobs published within 4/4 site requests.

M4 live proof artifact:

- `c12-m4-live-proof`
- artifact ID `11295658686`
- digest `b51f1ea151329ef3ad98f1c6f66ae09ced0b5d6aaa699e132312b580cac7fe4c`

## 5. Known measured production strengths

From prior certified/release qualification work:

- exact terminal-output behavior is strong;
- evidence completeness and hashes are strong;
- refresh/idempotency is strong;
- runtime/request accounting is strong;
- $0 third-party API policy is preserved;
- workforce coverage became near-universal after H2g;
- website precision has been protected through repeated manual audits and regressions.

Do not weaken these strengths to chase recall.

## 6. Primary remaining risk

**Recall / company coverage.**

The project is no longer mainly blocked by infrastructure. It needs more checked information types across more companies while preserving exact identity and evidence.

The next effort must optimize **net-new companies covered per information family**, especially:

- concrete jobs;
- dated first-party activity;
- contact/social/people/location facts unlocked by verified sites;
- any broad exact-ID official source that reaches companies without requiring a website.

Do not optimize merely for total claim count.

## 7. Exact next action

Do **not** immediately start another connector.

Start with Phase A from `docs/70_PLUS_IMPLEMENTATION_PLAN.md`:

1. run a fresh evaluator-shaped cohort on current M4 `main`;
2. build a matrix of data collected internally vs canonical claims actually emitted;
3. measure unique-company coverage by information family;
4. identify zero-risk collected-but-unpublished facts;
5. quantify what C12 M3/M4 changed on fresh companies;
6. only then select the next feature based on measured recall gain.

The likely next architecture work after that audit is verified-site enrichment 2.0 + adaptive request allocation, not a frontend rewrite.

## 8. Do-not-repeat decisions

- Do not loosen exact website identity to recover recall.
- Do not treat generic careers pages as jobs.
- Do not revive guessed `.com` discovery without new evidence; the prior H1f screen had no useful net gain and namesake risk.
- Do not scrape LinkedIn/Facebook/Glassdoor for production.
- Do not rely on random review scraping.
- Do not use paid search/API services under the current $0 project constraint.
- Do not submit after every small patch.
- Do not tune against Builderr's checked collection.
- Do not use an old local scoring rubric when the live challenge page differs.

## 9. Session handoff protocol

Before doing implementation work, a new chat must:

1. read this file;
2. read `docs/70_PLUS_IMPLEMENTATION_PLAN.md`;
3. inspect current `main` SHA and open PRs;
4. verify any time-sensitive Builderr rule against the live official page;
5. continue from the exact `NEXT` item below.

At the end of every substantial work session, update this file before stopping.

Required fields to update:

- date/time;
- current `main` SHA;
- active branch;
- active PR and state;
- exact branch head SHA;
- what changed;
- tests/CI runs;
- live/qualification run IDs and artifacts;
- baseline vs new company-coverage metrics;
- precision findings;
- request/runtime/cost impact;
- blockers;
- exact next 1-3 actions.

Never write `done` merely because code exists. Distinguish:

- IMPLEMENTED
- TESTED
- QUALIFIED
- MERGED
- POST-MERGE GREEN

## 10. NEXT

**NEXT:** Current-main M4 evaluator-shaped coverage audit and collected-vs-emitted claim audit.

After that audit, update this section with the selected next implementation branch and exact acceptance criteria.
