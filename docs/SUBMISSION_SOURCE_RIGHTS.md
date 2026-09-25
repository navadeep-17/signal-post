# Final source, licence, acquisition and runtime declaration

Updated: 2026-09-25

This document describes the production submission path used by `scripts/run_signalpost_v2.py`. V2 invokes the unchanged qualified V1 collector (`scripts/run_signalpost_final.py`), then performs zero-network projections over evidence and exact-company page snapshots already retained by that collector. Experimental scripts elsewhere in the repository are not enabled by the evaluator path and must not be interpreted as submission sources.

This is an engineering/source-rights declaration, not legal advice. When a source does not grant a blanket content-reuse licence, the system intentionally minimizes retained material and publishes bounded factual evidence with provenance instead of republishing source pages.

## Production source register

| Source | Production use | Acquisition | Licence / rights basis | What is retained/published | Important boundary |
|---|---|---|---|---|---|
| Brønnøysundregistrene entity bulk/live API | exact identity anchor, legal name/form, municipality, industry/status facts, employee count, latest-account metadata | Official bulk download and official REST API | BRREG open-data datasets are published under NLOD 2.0. Attribution: Brønnøysundregistrene. | normalized facts plus source URL, retrieval time, hash/evidence metadata | 404/absence is not converted to zero; org number remains the anchor |
| BRREG roles/group/subunits | leadership roles, group relationships, registered establishments | Official REST APIs | BRREG open-data datasets under NLOD 2.0 | company-centric role/location/group facts and provenance | birth dates are discarded; inactive/departed appointments are not presented as current V2 people facts |
| BRREG normalized accounts | annual financial fields | Official REST API | BRREG open-data datasets under NLOD 2.0 | period-aware normalized financial claims and evidence | missing records/source errors remain explicit; financial values are not imputed |
| BRREG annual-account copy | latest-year company-scope workforce phrase when registry employee count is unavailable | Official BRREG account-copy endpoint; local PDF text extraction/OCR | Official BRREG service. The submission stores claim evidence/hash metadata and does not redistribute the full filing PDF in the repository. | source URL, retrieval time, PDF SHA-256, effective year and bounded employee/FTE claim span | target org number must be recovered from document text/OCR; group phrases/conflicts abstain |
| Wikidata structured data | candidate discovery for an official website | Bounded WDQS batches keyed by Norwegian organisation number (P2333) and official website (P856) | Wikidata structured data is CC0 | candidate URL and lookup diagnostics sufficient for discovery | never proves the website by itself; the nominated page must independently pass exact-company verification |
| Verified company-owned website | official-site proof and bounded description/contact/social/job/update evidence | bounded public HTTP retrieval with safe URL/redirect handling and robots behavior | No blanket content-reuse licence is assumed | source URL, retrieval time, hash, bounded factual claim span, normalized outbound URL/email, and narrowly scoped role/update fact when strict eligibility is met | exact-company proof required; ambiguous/wrong-entity pages abstain; full pages are not republished; generic careers/news indexes are not facts |

Official references:

- BRREG open data: https://www.brreg.no/bruke-data-fra-bronnoysundregistrene/apne-data/
- BRREG Enhetsregisteret open-data documentation: https://data.brreg.no/enhetsregisteret/api/dokumentasjon/en/index.html
- NLOD 2.0: https://data.norge.no/nlod/en/2.0
- Wikidata licensing: https://www.wikidata.org/wiki/Wikidata:Licensing

## V2 projection boundary

V2 does not add a crawler, search provider, job platform or social-platform source. After the unchanged V1 collector completes, V2 reads:

- the final source-backed output envelope; and
- the exact-org internal profile/page snapshots already retained in the run work directory.

It then performs three local projections with **zero additional network requests**:

1. evaluator-facing BRREG registry projection for official fields retained in the exact-org profile but not reliably exposed by the V1 envelope;
2. strict first-party job/update projection over already-fetched pages from the verified company-owned site;
3. canonical grouping/typing and static product rendering.

The V1 base runner and output adapter are machine-verified against their submitted Git blob identities by `scripts/verify_submission_bundle.py`.

## Company-owned page policy

The web layer is used to establish exact company identity and retain narrowly scoped factual evidence. It does not treat public accessibility as permission to republish an entire site.

Production behavior:

- validates URL/redirect destinations and blocks unsafe/private-network targets;
- uses bounded page retrieval rather than open-ended crawling;
- follows the repository's robots/safe-HTTP policy;
- stores source URL, retrieval time, content hash and bounded evidence span;
- publishes a website only after exact-company identity evidence passes;
- treats parent, brand, franchise and namesake pages as non-exact unless the target legal entity is proven;
- does not infer a missing value from a page that was not successfully qualified.

### Strict first-party hiring boundary

A generic careers page, careers keyword, navigation link or section index is never a hiring fact. V2 can publish a job only from an already-retained page on the exact verified company-owned site when all strict conditions hold: a job/career-like **detail URL**, a specific non-generic title, a job-detail marker and an explicit apply/application action. Cross-domain pages and generic filtered indexes are rejected.

The claim records the role title/page URL plus bounded evidence/provenance. It does not assert that a job is still open after retrieval time or infer organization-wide hiring intensity.

### Strict first-party company-update boundary

A generic news/blog/press index is never a company-update fact. V2 can publish an update only from an already-retained same-site **detail page** with a specific non-generic title and an explicit date. Undated section pages are rejected.

The system retains only the normalized title/URL/date and bounded evidence metadata; it does not republish the article body.

## Social-platform boundary

The production runner makes **zero requests to social platforms**.

`external.profile_handle` claims are derived only from social URLs explicitly declared by an exact verified company-owned page. The claim therefore means:

> the verified company page declared this profile URL at retrieval time.

It does **not** mean:

- the platform page was fetched;
- the handle is currently controlled by the company;
- the account is platform-verified;
- the account is active;
- any follower/engagement metric is known;
- any sentiment or hiring signal is known.

LinkedIn, Meta, YouTube, TikTok and X are therefore URL destinations in this claim family, not scraped production data sources.

## Contact-email boundary

`external.contact_email` is a zero-network projection over already retained verified company-page evidence. Publication requires the email to appear in a bounded footer/contact/legal context and its registered domain to match the verified company website registered domain.

The claim does not assert mailbox deliverability, inbox ownership, response likelihood or consent for marketing use.

## Models and local processing

The production runner invokes **no LLM and no sentiment model**.

The optional sentiment dependencies and experimental sentiment scripts in the repository are not enabled by `scripts/run_signalpost_v2.py` and produce no submitted claims.

Annual-report extraction may use local:

- Poppler `pdftoppm` for PDF rasterization;
- Tesseract OCR with language `eng`;
- `pypdf` for digital-text extraction.

These are local processing tools, not paid external inference APIs. If the OCR executables are unavailable, the workflow abstains on OCR-dependent workforce extraction and continues producing terminal company output.

## API, request and cost declaration

Production policy:

- paid third-party APIs: **none**;
- LLM APIs: **none**;
- search APIs: **none**;
- social-platform APIs/scraping: **none**;
- third-party API spend: **$0.00**;
- conservative request ceiling: **2,000 per 100 companies**;
- V2 registry/activity/canonical/product projections add **zero** network requests;
- annual-report PDF requests are allocated only from structural request capacity left after the base pipeline.

The certified V1 1,000-company replay observed 13,628 conservative requests across ten 100-company chunks and zero search-API requests. V2 fresh-validation metrics, when cited, are diagnostics rather than an official Builderr score.

## Cache and retention declaration

The production runner writes local per-run work artifacts such as normalized profiles and internal envelopes. Evidence records contain provenance metadata required for auditability: source URL, retrieval timestamp, content hash and bounded claim span.

The submission does not require a hosted database or a persistent third-party cache. The BRREG bulk file is a run input/snapshot. Wikidata candidate responses are not treated as publication evidence; the independently fetched qualifying company page is.

## Hosting declaration

No external hosting is required to execute or inspect the submission. The V2 evidence workspace is a static HTML artifact generated locally from the final V2 JSONL. A deterministic product built from the immutable certified corpus is also committed at `submission/signalpost-v2.html`.

## Explicitly excluded from the production stack

The following experiments or ideas are not submission sources:

- paid/permitted search-provider experiments;
- direct LinkedIn guest/profile/jobs collection;
- Meta platform collection;
- Google Maps/review scraping;
- Fagfolkguiden/Google-derived review publication;
- NAV job-feed publication;
- independent-news sentiment;
- Hugging Face sentiment models;
- guessed `.com` fallback;
- broad additional guessed-domain variants beyond the qualified website-discovery order.

Historical design documents may discuss these experiments. `SUBMISSION.md`, `submission/manifest.json`, this file and `docs/FINAL_RELEASE_1000_AUDIT.md` are authoritative for the submitted path.
