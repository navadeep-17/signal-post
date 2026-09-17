# H2g — Official Annual-Report Workforce OCR

Updated: 2026-09-17

## Decision

**PROMOTED TO PRODUCTION.**

H2g fills the workforce/jobs information family for companies where the live BRREG entity endpoint does not expose an employee count. It reads the latest official BRREG annual-account copy for the exact organisation number and publishes only an explicit company-scope employee/FTE phrase.

Production merge: PR #26

Production application SHA: `b14ef3c277d8f1512064f865d4028e23dcd8bacf`

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
- OCR uses at most 8 pages at 110 DPI and one OpenMP thread per Tesseract process.
- Isolated source/OCR failures are auditable abstentions and do not invalidate otherwise-terminal company outputs.

## Qualification history

### Transport correction

The first annual-report screen incorrectly sent `Accept: application/pdf`, causing HTTP 406 responses. A BRREG negotiation probe showed the copy endpoint works with the binary response path; production uses `Accept: application/octet-stream` and verifies `%PDF` bytes.

### OCR and concurrency qualification

The reports tested were image-only to `pypdf`, so OCR was required. Small screens established the conservative extractor before release-scale work:

- 5-report probe: 5/5 accepted.
- 20-report screen: 19/20 accepted; one conflicting report correctly abstained.
- 8-page screen: 20/20 accepted, including 0.30, 2.60 and 1.00 FTE values.
- the first 4-worker 300 transfer was rejected because Tesseract oversubscribed CPU and timed out;
- after setting `OMP_THREAD_LIMIT=1`, the 20-company concurrency regression returned 20/20 accepted with zero OCR/runtime errors in 88.4 seconds.

### Independent fresh-300 transfer

Run: `35104937900`

Artifact: `h2g-annual-workforce-qualification-v2`

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
- combined H2e + H2g workforce coverage: **296/300 = 98.67%**
- official BRREG PDF requests: 260
- H2g runtime: about 1,054 seconds
- exact organisation number recovered: 260/260
- observation/contract/execution errors: 0
- third-party API cost: $0

The four abstentions were three reports with no qualifying workforce phrase and one report with conflicting employee counts. All 256 accepted observations used explicit FTE evidence; values ranged from 0 to 21 FTE, including 60 non-zero observations.

## Integrated production qualification

Run: `35123345239`

Artifact ID: `10459426440`

Digest: `sha256:1b9403359af549873a964d28cbf8ca0927f491df57bac709fff2f85701a28f8f`

Results:

- final objects: 300/300
- workforce companies: **296/300 = 98.67%**
- H2g accepted: 256/260
- H2g requests: 260
- execution errors: 0
- external validation errors: 0
- contract errors: 0
- observed conservative charge: 4,106 / 6,000
- structural ceiling: 6,000 / 6,000
- wall runtime: 1,277.63 seconds / 2,400 seconds
- third-party API cost: $0

The production runner keeps isolated BRREG/OCR failures as auditable abstentions rather than turning one source failure into a batch failure. Qualification CI remains stricter and requires zero execution errors.

## Default 100-company production smoke

Run: `35123401363`

Artifact ID: `10459195879`

Digest: `sha256:d4fa5ad79ebe9c381757aaeeb267685f8b8bd74bab563f70dd31f0d02367e88c`

Results using runner defaults:

- final objects: 100/100
- workforce companies: **100/100**
- H2g eligible/selected: 84/84
- H2g accepted: 84/84
- execution/validation/contract errors: 0
- H2g requests: 84
- observed conservative challenge charge: 1,370 / 2,000
- structural challenge ceiling: 2,000 / 2,000
- total wall runtime: 427.825 seconds
- third-party API cost: $0

## Request theorem

The pre-H2g final runner has a 1,802 conservative structural charge for a 100-company evaluation. Under the official 2,000-request budget, H2g receives only the remaining structural slots:

`floor((2000 - 1802) / 2) = 99` annual-report logical requests.

The same calculation is derived dynamically from the configured budget. H2g cannot consume requests reserved by the already-qualified base pipeline.

## Runtime/setup

The qualified OCR implementation requires `pdftoppm` (Poppler) and Tesseract. If they are unavailable, H2g abstains and the rest of the terminal runner remains functional. Linux setup is documented in the README.

## Current status

H2g is no longer experimental. It is part of the production one-command runner and should be treated as the current workforce fallback in release and submission documentation.