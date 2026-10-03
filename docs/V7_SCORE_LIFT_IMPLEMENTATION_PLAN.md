# V7 score-lift implementation plan

This plan is driven by the latest official Builderr evaluation for the current production line:

- Recall / coverage: 12.83 / 50
- Precision / evidence: 26.92 / 30
- Synthesis: 9.46 / 12
- UX: 3.20 / 8
- Total: 52.41 / 100

The public board reviewed 3 October 2026 shows that several leading entries reach 12/12 synthesis and 8/8 UX while remaining in roughly the same recall band. The release strategy therefore prioritizes proven score headroom first, then targeted recall improvements that directly match Builderr's feedback.

## Ground rules

1. Exact organisation number remains the identity anchor.
2. No production strategy may weaken the current wrong-company publication gate.
3. Every positive summary claim must remain traceable to canonical evidence.
4. Missing information is explicit; absence is never converted to zero or to an unsupported negative claim.
5. Experiments that already produced a measured NO-GO are not repeated without new evidence.
6. Each milestone lives on its own branch/PR and is merged only after CI and milestone-specific gates pass.
7. The existing `feature/v6-ui` branch stays isolated until the backend/synthesis milestones are ready for final integration.

## Already-screened ideas that are not current milestones

The following have already been measured and rejected or deferred:

- paid search-assisted discovery;
- deterministic/ML website-candidate ranking on the tested candidate family;
- broad deep crawl of currently verified websites at current website reach;
- annual-report website-domain nomination;
- NAV feed scan using the tested broad exact-org strategy;
- BRREG subunit site/email hints as parent-company website evidence.

A small zero-network recovery of exact-homepage social declarations has already been promoted to `main`.

## Milestone 1 — Synthesis score lift

**Goal:** move the evaluator-facing synthesis toward the public 12/12 pattern without adding sources or facts.

Add a richer deterministic decision brief over existing canonical facts:

- what is this company;
- what does it do;
- how big is it;
- who runs it;
- hiring status / known hiring facts;
- digital footprint;
- what changed;
- what remains unknown;
- explicit evidence trace with source URL, retrieval date, claim span, reporting/effective date where available.

Compatibility requirements:

- preserve existing `sections`, `what_changed`, `unknowns`, and `evidence_ids` fields;
- preserve the pre-V5 `what_changed` shape for historical contracts with no registry-change facts;
- deterministic, zero network, no LLM, no new facts.

**Gate:** full test suite + synthesis validator + explicit regressions for source/date traceability and unknown handling.

## Milestone 2 — First-party hiring and dated-news signal semantics

**Goal:** address Builderr's explicit 0% dated-news and 0% hiring feedback without mislabelling evidence.

Separate truthful fact types:

- `hiring.careers_page` / verified careers signal;
- `hiring.job_listing_page` where a company-owned listing index is specific enough;
- `hiring.job_posting` only for a concrete role;
- `public.dated_update` for a specific company-owned dated article/update.

Use only exact-verified first-party sites and bounded extraction from existing retained pages or a narrowly justified crawl. Prefer structured data (`JobPosting`, `NewsArticle`, `Article`), explicit `<time datetime>`, RSS/Atom, and sitemap-discovered first-party URLs.

**Gate:** fresh or untouched transfer cohort, zero wrong-company publications, 100% evidence linkage, meaningful non-zero hiring and/or dated-news company coverage within request budget.

## Milestone 3 — High-yield official/free recall sources

**Goal:** add recall only where a new strategy has better expected information gain than previously rejected screens.

Priority candidates are screened one at a time. Rejected NAV/feed-wide logic is not repeated unchanged. New NAV work is only justified if it uses a materially different retrieval/indexing route with demonstrably better exact-employer reach or request economics.

**Gate:** measured net-new checked-family company coverage on an untouched cohort with zero material identity errors.

## Milestone 4 — Website discovery revisit only with a new signal

**Goal:** improve website coverage only if a genuinely new candidate source is available.

Do not repeat the rejected `.com`, ML/rules ranking, annual-report-domain, or subunit-site candidate approaches unchanged. Any new discovery route must first prove candidate-set reach offline or on consumed data before a fresh cohort is spent.

**Gate:** material net-new verified websites per charged request, zero material wrong-company publications.

## Milestone 5 — Evidence polish

**Goal:** move evidence from 26.92 toward the 28–29 range by making already-correct evidence easier for the evaluator to consume.

Focus on:

- effective/reporting/publication dates;
- source URL and retrieval time on every summary-visible claim;
- claim spans;
- explicit availability state;
- deterministic summary-to-evidence mapping;
- no orphan evidence references.

No new data collection is required unless a milestone-specific gap demands it.

## Milestone 6 — V6 UI integration and final release

Rebase `feature/v6-ui` onto the final backend/synthesis base and wire it into the evaluator-facing product path.

Required UX surfaces:

- search/discovery;
- company profile;
- evidence drawer;
- comparison;
- changes timeline;
- explicit unknowns/data gaps;
- grounded Ask SignalPost;
- responsive desktop/mobile behavior.

Then update current-product/verifier lineage, run the complete qualification suite, freeze the exact submission commit, and prepare the revision email.

## Score strategy

The target is not to force all remaining points out of Recall. A realistic qualification path is to combine:

- synthesis near 12/12;
- UX near 8/8;
- evidence in the high-20s;
- Recall in roughly the mid/high teens.

Official scoring remains evaluator-owned; local milestone metrics are promotion evidence, not claimed competition scores.
