# V9 M10 Gate A — Qualified Manual Precision Audit

## Immutable evidence

- Gate A source branch: `experiment/v9-m10-consumed-gates`
- Qualified exact Gate A code SHA: `2848ed505103b3cbb0a3bf8d6313ee1ba7a25ecf`
- Baseline CI: `37565183837` **PASS**
- Consumed 20 exact-head run: `37565180008` **SUCCESS**
- Artifact ID: `11458838045`
- Artifact ZIP digest:
  `sha256:928e9ff4f11eb2ad078b0455c66e574c6c6bb7ec6e2ef2a8ccce123a73808e9f`
- Human/manual signoff recorded in draft PR #154,
  comment ID `6030312390` on 2026-10-07.
- Fresh company cohort use: **0**.

## Gate A numerical results

Seven scored company families, frozen V8 to V9 challenger:

| Family | Baseline | Challenger | Net new | Lost |
|---|---:|---:|---:|---:|
| Verified website | 2 | 3 | +1 | 0 |
| Social | 1 | 2 | +1 | 0 |
| External contact | 0 | 3 | +3 | 0 |
| Careers surface | 1 | 2 | +1 | 0 |
| Company-authored hiring intent | 0 | 1 | +1 | 0 |
| Specific active jobs | 0 | 0 | 0 | 0 |
| Dated first-party activity | 0 | 0 | 0 | 0 |

Total net-new company-family edges: **+7**. Lost: **0**.
External publications added: **11**. Lost: **0**.
Conservative observed request charge: **286 -> 278**.
Conservative theoretical charge: **406 -> 406**.
Wall runtime: **558.150 -> 555.359 seconds**.
Search API requests: **0**. Third-party API cost: **$0**.
Machine screen: `MANUAL_AUDIT_REQUIRED` with `errors=[]`;
the machine does not promote a release.

## Every new exact-head publication was manually inspected

**11/11 reviewed / 11/11 accepted / zero wrong-company / zero scope errors / zero evidence defects.**

All 11 exact-head publication signatures (organisation number, field, value,
page source URL, page SHA-256 and bounded claim span) match 11 previously
independently manually reviewed rows, with zero omissions or additions.

- ENTALPY AS, `927097532`: exact verified homepage
  `https://entalpy.no/`, SHA
  `93a79060f7be5743eee904890ea9accb37bd62aff587cd59f777788672232a12`;
  exact-domain structured email `frank@entalpy.no`,
  same-entity structured phone `+4790564983`, explicit company-authored
  recruitment intent from bounded `Vi søker` language.
  Hiring intent is **not** evidence of a current specific vacancy. 3/3.
- VOLF AS, `979943377`: exact verified homepage `https://volf.no/`,
  SHA `083de1273a66bcf99be8faec8c028caebd6f789f2922e4af7ce628ce9dcb7ef4`;
  structured same-domain email `post@volf.no` and exact-org structured
  phone `+4770275662`. 2/2.
- DEN GLADE GRIS AS, `999096298`: exact verified site
  `https://www.dengladegris.no/`, SHA
  `a9d8388c0b1eee0547f2800964a98fbc3835deaea584c18eabd1998bdda12889`;
  official website, declared same-host careers surface, homepage-declared
  Facebook/Instagram handles, bounded same-domain contact email
  `booking@dengladegris.no` and structured same-company phone
  `+4722111710`. Careers surface **does not** assert active hiring/job. 6/6.

All source hashes, retrieval timestamps, linked spans and typed exact-company
identity / per-field corroboration satisfy the governing head's full evidence
audit, with no audit checks failed.

## Authorization and next boundary

**Gate A: PASS.** Run Gate B on the locked, already-consumed 100 manifest
**only after checking the Gate-A artifact digest and BRREG snapshot SHA**.

The Gate B branch may add this documentation and an isolated workflow but
may not change production `src/`, `scripts/`, tests, dependency pins or
the independent exact-company verifier. The comparator must use the same 100
companies and the same BRREG snapshot for both baseline and challenger.

If the registry bulk snapshot bytes have changed since Gate A, fail closed;
do not silently run a different evaluation. All new Gate B publications
require 100% additional manual precision review before any M10 PROMOTE
decision. No fresh qualification cohort is authorized by Gate A.
