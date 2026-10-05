# Q8 legacy first-party activity provenance retune

Status: **CONSUMED-COHORT RETUNE — no fresh qualification credit**.

Fresh Q8 seed `20261105` is permanently consumed. Its actual V8 production run completed successfully, but the post-run evaluator-visible evidence gate found exactly one identity-sensitive claim without visible identity proof or extraction method:

- organisation `885588522` — `HEMSEDAL MØBLER AS`;
- field `external.company_update`;
- page `https://www.hemsedalmobler.no/garderobe/`;
- evidence ID `ev-first-party-46dab620049bff6587c7`;
- core evidence and reopenability were already complete.

The cause is architectural: the older page-backed C12 activity projector predates the evaluator-visible provenance convention used by the newer RSS/Atom path. The claim is already restricted to a same-site detail page under an exact verified company website, but its final evidence row omitted those retained semantics.

This retune adds a deterministic, zero-network final-contract backfill for legacy `ev-first-party-*` page-backed job/update evidence only. It requires:

- an available `official_website` claim with evaluator-visible identity proof;
- company-site platform and the expected job/update signal type;
- claim URL and evidence source on the exact verified site;
- `source_class=company_owned`;
- a valid SHA-256 content hash;
- for updates, evidence `effective_at` exactly equal to the published date;
- legacy `ev-first-party-*` evidence, explicitly excluding `ev-first-party-feed-*`.

It never overwrites existing provenance. The exposed extraction methods are:

- `verified_same_site_dated_detail_page_v1`;
- `verified_same_site_job_detail_page_v1`.

The consumed replay must prove exactly one Q8 evidence row gains only these provenance fields, while claims, evidence IDs, source URLs/hashes and all other fields remain unchanged; evaluator-visible coverage must move from 164/165 to 165/165 with zero remaining evidence issues.

This provenance fix does **not** make Q8 release-qualified. Manual review of the same consumed cohort found additional precision defects in social, feed-activity and careers extraction. Those are separate retune milestones and must be closed before any next fresh attempt.
