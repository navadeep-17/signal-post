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

## Broader exact-P2333 account screen

Because P4264 was correct but sparse, the same locked fresh 300 was screened for five additional Wikidata account properties:

- `P2002` — X username
- `P2003` — Instagram username
- `P2013` — Facebook username
- `P2397` — YouTube channel ID
- `P7085` — TikTok username

Screen run: `35013714592`

Screen head: `88dd7cafe1961cf84ecba306fa5104367f73fa6b`

Artifact: `h2d-wikidata-org-account-screen`

Artifact ID: `10414881239`

Artifact digest: `sha256:890d75326301a9503966a4b20bc5dd4508d8b1ff317f06868071b0b6aa5fbd62`

The screen reused and hash-verified the exact H2d fresh cohort rather than selecting a new sample. It made three bounded WDQS requests and cost $0.

Results:

- candidate companies: 2/300 (0.67%)
- candidate identifiers: 3
- Facebook: 2
- Instagram: 1
- X: 0
- YouTube: 0
- TikTok: 0
- ambiguous organisation mappings: 0
- ambiguous per-platform identifiers: 0
- projected added production requests if folded into the existing H1e batch: 0

Candidates:

1. `910968955` — DNB EIENDOM AS — Facebook `dnbeiendom`
2. `910968955` — DNB EIENDOM AS — Instagram `dnbeiendom`
3. `987345683` — OLAV ØVERLIS MINNE STI — Facebook `etnedalkommune`

Manual audit:

- DNB Eiendom's Facebook and Instagram identifiers are consistent with the DNB Eiendom organisation and add handles for the same company already discovered by P4264.
- The `OLAV ØVERLIS MINNE STI -> etnedalkommune` mapping is **not acceptable as an exact legal-entity profile-handle claim**. BRREG identifies OLAV ØVERLIS MINNE STI as a distinct foundation (`987345683`), while the candidate username is the Etnedal municipality account. Wikidata itself currently stores that municipality username on the foundation item, demonstrating that exact P2333 item matching does not make generic social-account properties exact-entity-safe.

Therefore the broader properties produced **zero additional correct company coverage beyond the single DNB company already found by P4264**, while introducing a false exact-entity candidate.

## Final decision

**REJECT H2d. Do not merge any Wikidata social-handle code into production.**

Reasons:

- P4264-only fresh net-new company coverage is only 1/300 (0.33%).
- The broader five-property screen reaches only 2/300 companies (0.67%).
- After manual audit, the only additional company is a false exact-entity match.
- Aggregate audited correct company gain remains 1/300 (0.33%).
- The challenge rewards company recall much more than multiple handles for the same already-covered company, so extra DNB handles do not justify the production complexity.
- Generic Wikidata social identifiers weaken the precision boundary because related/parent organisations can be stored on an exact P2333-matched item.

Production `main` remains unchanged at the H1g merge. The next coverage experiment should target a different external field/source rather than further Wikidata social-property expansion.
