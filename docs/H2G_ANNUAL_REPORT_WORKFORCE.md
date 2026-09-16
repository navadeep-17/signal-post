# H2g — Official Annual-Report Workforce OCR

## Decision

**PROMOTE**, subject to the final integrated 300-company production qualification remaining green.

H2g fills the workforce/jobs score dimension for companies where the live BRREG entity endpoint does not expose an employee count. It reads the latest official BRREG annual-account copy for the exact organisation number and publishes only an explicit company-scope employee/FTE phrase.

## Claim boundary

Published claims mean only:

> The latest submitted official BRREG annual-account copy for this exact legal entity contains the quoted company-scope workforce phrase with the reported employee/FTE value.

H2g does **not** infer group workforce, current payroll, growth, trend, headcount from FTE, or FTE from headcount. Group-labelled phrases and conflicting values abstain.

## Identity and source controls

- Official BRREG annual-account endpoint keyed by exact organisation number and submitted-account year.
- Exact target organisation number must also be recovered from the report text/OCR.
- PDF magic and a 20 MB bound are enforced.
- Source URL, retrieval time, content SHA-256, effective year and evidence span are preserved.
- Acquisition mode: `official_api`; rights status: `approved`.
- BRREG requests start at least 2.1 seconds apart.
- OCR uses 8 pages at 110 DPI and one OpenMP thread per Tesseract process.
- Isolated source/OCR failures are recorded as abstentions and do not invalidate otherwise-terminal company outputs.

## Qualification history

### Transport correction

The first annual-report screen incorrectly sent `Accept: application/pdf`, causing HTTP 406 responses. A BRREG negotiation probe showed the copy endpoint works with the advertised binary response path; production uses `Accept: application/octet-stream` and verifies `%PDF` bytes.

### Image-only diagnosis

A corrected 60-company screen downloaded all reports successfully but `pypdf` extracted zero text characters from all 60. The source was available; OCR was required.

### OCR screens

- Five-report probe: 5/5 accepted.
- Twenty-report screen: 19/20 accepted; the one conflict correctly abstained.
- Eight-page screen: 20/20 accepted, including non-zero 0.30, 2.60 and 1.00 FTE values.

### First fresh 300 transfer attempt

The first 4-worker transfer run was **not accepted as evidence**. 253/254 selected reports hit Tesseract subprocess timeouts because concurrent Tesseract processes oversubscribed CPU. This was an execution failure, not a BRREG or evidence failure.

### Thread-bounded concurrency fix

Each Tesseract process was constrained with `OMP_THREAD_LIMIT=1` while keeping four report workers.

Known 20-company concurrency regression:

- 20/20 accepted
- 20/20 exact organisation numbers recovered
- zero OCR/runtime errors
- same non-zero values preserved
- runtime: 88.4 seconds

### Independent fresh transfer qualification

Run: `35104937900`

Artifact: `h2g-annual-workforce-qualification-v2`

Artifact digest: `sha256:99ffeeb6c5f21ec5abf9863a923642cc670e14760d3edd844039387b22beb9fa`

Fresh cohort:

- seed: `20260930`
- prior excluded companies: 5,500
- cohort size: 300
- overlap: 0
- manifest SHA-256: `abaa68d267355ee7f24e59c82408aabb513b8e146706aa6b380b6dc3e0946404`

Results:

- existing H2e workforce companies: 40/300
- H2g eligible/selected: 260/260
- H2g accepted: 256/260 = 98.46%
- H2g net-new company coverage: 256/300 = 85.33%
- combined H2e + H2g workforce coverage: 296/300 = 98.67%
- official BRREG PDF requests: 260
- added conservative challenge charge: 520
- projected structural challenge charge: 5,926 / 6,000 for 300
- third-party API cost: $0
- H2g runtime: 1,055.667 seconds
- exact organisation number recovered: 260/260
- validation errors: 0
- contract projection errors: 0
- execution errors: 0

Status counts:

- accepted: 256
- no employee/FTE phrase: 3
- conflicting employee counts: 1

All 256 accepted transfer observations used the explicit FTE measure. Values ranged from 0 to 21 FTE; 60 were non-zero. The four abstentions were preserved rather than guessed.

### Integrated production attempt and resilience fix

The first fully integrated 300-company run (`35119391999`) preserved all 300 terminal objects, stayed within the request/runtime budget, and produced 295 workforce companies, but one BRREG PDF response ended with `IncompleteRead`. Production originally treated any H2g execution error as a global failure even though that company correctly had no H2g claim.

The runner was corrected so isolated H2g source/OCR execution failures remain auditable abstentions rather than invalidating the full terminal batch. Qualification CI separately keeps a strict zero-execution-error assertion.

### Default 100-company production smoke

Run: `35123401363`

Artifact: `h2g-default-100-production-smoke`

Artifact digest: `sha256:d4fa5ad79ebe9c381757aaeeb267685f8b8bd74bab563f70dd31f0d02367e88c`

Results using the runner defaults, with no request-budget override:

- final objects: 100/100
- workforce companies: 100/100
- H2g eligible/selected: 84/84
- H2g accepted: 84/84
- H2g execution errors: 0
- H2g requests: 84
- observed conservative challenge charge: 1,370
- structural challenge ceiling: 2,000
- total wall runtime: 427.825 seconds
- third-party API cost: $0
- validation errors: 0
- contract errors: 0
- budget errors: 0

## Request theorem

The base final runner has a 1,802 conservative structural charge for a 100-company evaluation. Under the official 2,000-request budget, H2g receives only the remaining structural slots:

`floor((2000 - 1802) / 2) = 99` annual-report logical requests.

The same calculation is derived dynamically from the configured budget. H2g cannot consume requests reserved by the already-qualified base pipeline.

## Runtime/setup

The qualified OCR implementation requires `pdftoppm` (Poppler) and Tesseract. If they are unavailable, H2g abstains and the rest of the terminal runner remains functional. Linux setup is documented in the README.
