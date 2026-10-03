# Signalpost V9 score-expansion plan

Updated: 2026-10-03

Goal: maximize verified recall without weakening exact-company precision, while preserving the current V8 evaluator compatibility and certified V5/V7 lineage.

Builderr's current scoring weights are 50 recall/coverage, 30 precision/evidence, 12 synthesis and 8 UX. The latest internal V7 qualification already has near-complete official/structured coverage but only 7/100 verified company sites and 4/100 companies with hiring/public-activity coverage. V9 therefore prioritizes external-company recall.

## Global invariants

- Exact-company publication gate remains stricter than candidate-discovery logic.
- Search/provider output is nomination-only and is never persisted as company evidence.
- Every published external fact must be backed by an independently fetched source belonging to the exact legal entity.
- Missing/blocked/ambiguous remains explicit; never fabricate negatives or fill unknowns with zero.
- V8 evaluator compatibility stays intact until a later production milestone is separately qualified.
- One production milestone at a time; experiments stay off the default evaluator path until fresh-cohort qualification passes.
- A material wrong-company publication is an automatic NO-GO regardless of recall gain.

## M0 — baseline and scoring guardrails

Status: ACTIVE

Baseline to preserve:

- 100/100 company record
- 100/100 financials
- 99/100 people/locations
- 99/100 workforce
- 99/100 company descriptions
- 100/100 decision briefs
- 7/100 verified company sites in the latest release qualification
- 4/100 hiring/public-activity coverage in the latest release qualification
- 0 canonical/synthesis validation errors

Target outcome for V9: materially increase company-level coverage in website, hiring and public-activity categories without degrading precision/evidence.

## M1 — Website Discovery 2.0

### M1a — diversified search nomination

Reuse the existing H1b safety architecture but improve recall before any production integration:

1. generate multiple bounded query variants per unresolved company;
2. score and deduplicate candidates by registered domain;
3. retain up to two independently crawlable candidates instead of only one;
4. keep provider title/snippet/query/rank transient;
5. never publish from search evidence itself.

Offline gate:

- directory/social hosts always rejected;
- duplicate domains collapse deterministically;
- search rank never becomes an identity signal;
- exact organisation-number evidence can nominate acronym/brand domains for crawl;
- name-only weak candidates remain quarantined.

### M1b — current exact-company verifier integration

Each nominated candidate must be independently fetched using the current bounded website path and then pass exact-company proof.

Preferred proof order:

1. target organisation number on independently fetched page;
2. full legal name + registry-location corroboration;
3. full legal name + exact legal-name domain;
4. otherwise ambiguous/review, never publish.

Parent pages, namesakes, directory records and conflicting explicit organisation numbers remain hard rejects.

### M1c — 20-company live screen

Use a fresh unresolved cohort, not a previously tuned set.

GO threshold:

- at least 5 net-new verified sites out of 20 queried companies (>=25% yield);
- zero wrong-company publications after manual audit;
- no persisted provider snippets/raw results;
- bounded requests/runtime;
- declared external API cost remains within Builderr's official-run budget.

Anything below 3 verified sites out of 20 is a NO-GO unless a clearly isolated provider/configuration issue explains the miss.

### M1d — fresh 100 qualification

If M1c passes, run on a fresh 100-company cohort.

Production GO threshold:

- target >=25 verified company sites / 100 total, or >=18 net-new verified sites over the current discovery path;
- zero wrong-company publications;
- 100 terminal outputs;
- zero contract/canonical/synthesis validation errors;
- exact evidence/source/date requirements preserved.

### M1e — production integration

Only after M1d passes:

- wire Website Discovery 2.0 into the evaluator path behind explicit resource accounting;
- keep search nomination transient;
- preserve independent fetch + exact-company publication gate;
- qualify exact production head before merge.

## M2 — structured first-party discovery

Run only on already verified domains.

Discovery order:

1. `sitemap.xml` / sitemap indexes;
2. RSS/Atom feeds;
3. homepage JSON-LD/microdata already fetched;
4. bounded same-domain candidate URLs.

Extract only URLs likely to represent news, press, careers, jobs or articles.

GO threshold:

- meaningful net-new company-level surfaces on a fresh cohort;
- explicit same-domain and date requirements;
- no generic deep crawl explosion.

## M3 — verified careers surface to ATS jobs

A third-party ATS is eligible only when reached from an already verified company-owned careers surface.

Strict job-posting requirements:

- specific role URL;
- specific title;
- employer identity tied back to the verified company;
- explicit application action or structured JobPosting evidence;
- current/active evidence where available.

A careers page alone remains `hiring.careers_page` and never becomes an active vacancy.

GO threshold: >=5 companies with newly qualified specific jobs in a fresh 100, zero wrong-employer publications.

## M4 — dated company updates

Use only verified company-owned first-party sources discovered through sitemap/RSS/structured data.

Require:

- specific article/update URL;
- non-generic title;
- explicit publication date;
- exact verified company domain.

Target: 15-30 companies with at least one dated company-authored update in a fresh 100 if available.

## M5 — low-cost enrichment from fetched pages

Without materially increasing network cost, project additional verified facts from pages already downloaded:

- contact emails and phones;
- company-declared social profiles;
- additional office/location evidence;
- Organization/LocalBusiness/Person JSON-LD;
- products/services and descriptive text only when company-scoped and evidence-backed.

Prefer company-level coverage gains over duplicate fact volume.

## M6 — final production qualification and score revision

1. fresh 100-company qualification;
2. wrong-company manual audit of all newly published external domains/facts;
3. large-batch operational check compatible with Builderr-supplied batch sizes;
4. exact-head CI green;
5. merge;
6. post-merge `main` green;
7. pin release ref;
8. submit one revised SHA only after the improvement is materially qualified.

## Stop conditions

Do not promote a milestone when:

- any material wrong-company publication occurs;
- coverage gain is too small to justify added cost/complexity;
- provider terms/reproducibility are unclear;
- evaluator credentials cannot be supplied independently of the builder's personal account;
- runtime or request growth threatens one-result-per-company completion.

A NO-GO experiment is considered successful engineering if it prevents a low-value or precision-damaging production change.
