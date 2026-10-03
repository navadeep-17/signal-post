# V7 M2C — verified homepage careers signals

## Purpose

Builderr's official diagnostic explicitly cited company-owned careers pages as missed hiring signals. M2C publishes a narrow hiring-presence fact from an exact-verified company homepage without claiming that a specific vacancy is open.

## Production boundary

- The company website must already pass the existing exact-company publication gate.
- Careers discovery happens while the already-budgeted homepage HTML is in memory.
- Only explicit same-registered-domain careers/hiring links are retained.
- External ATS/job-board URLs are not represented as company-owned careers pages.
- No careers URL is fetched by M2C.
- The claim type is `external.careers_page`; it is never `external.job_posting`.
- Canonical fact: `hiring.careers_page`.
- Synthesis says hiring presence is known while explicitly stating when no specific active job is independently verified.
- Incremental network requests: 0.
- Third-party API cost: $0.

## Evidence

The evidence is the exact verified homepage that declared the careers link, including its retrieval timestamp, content hash and bounded link text.

## Promotion evidence

The preceding experiment (PR #61) transferred to a fresh unseen 100-company cohort with 2 companies exposing exact same-domain careers surfaces and zero wrong-company publications. The production implementation removes the experiment's homepage re-fetch, so discovery uses zero extra requests.
