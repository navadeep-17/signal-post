# H2d Wikidata social experiment

This branch evaluates whether the existing exact organisation-number Wikidata lookup can provide additional company profile-handle candidates without increasing production request count.

## P4264-only qualification

The first pass deliberately tested only Wikidata property `P4264` (LinkedIn company or organization ID), because its semantics are organization-specific and therefore give the strongest precision boundary.

Qualification run: `35012657214`

Qualified head: `a1c2ffe7edfb4e06ee0ea6cd34f40f07b1675393`

Artifact: `h2d-wikidata-linkedin-qualification`

Artifact ID: `10414695731`

Artifact digest: `sha256:f3835b26303429af17397621868c8fc90e25fcf22ca7c119e89d4f0fa5aaa299`

Fresh cohort:

- 300 companies
- seed `20260927`
- 4,600 previously touched companies excluded
- overlap: 0
- manifest SHA256: `73ffeb9a5010c6bc86a5b7ab2ed07e6d18e206b6db2f016a4ba4fe4e7d56e55c`

Results:

- existing production H2a LinkedIn companies: 2/300
- exact P2333 -> P4264 candidates: 1/300 (0.33%)
- overlap with existing H2a: 0
- net-new candidate companies: 1/300 (0.33%)
- prospective LinkedIn company coverage after H2d: 3/300
- experimental WDQS requests: 3 bounded batches
- projected added production requests if folded into the existing H1e batch lookup: 0
- third-party cost: $0
- prospective observation validation errors: 0

The only candidate was:

- organisation `910968955` — DNB EIENDOM AS
- Wikidata item `Q11964320`
- P4264 identifier `dnbeiendom`
- candidate profile `https://www.linkedin.com/company/dnbeiendom/`

Manual external verification confirmed that this is the DNB Eiendom organisation profile and that its company identity/location align with DNB EIENDOM AS.

## Decision

**Do not merge the P4264-only implementation.**

The single audited candidate is correct, but the fresh transfer yield is too small to justify a production integration on its own. The broader Wikidata same-request hypothesis remains open: next test the remaining organization-account properties on exact P2333-matched items, then only promote a combined path if aggregate net-new company coverage is materially better while preserving the same ambiguity guards and zero projected request delta.
