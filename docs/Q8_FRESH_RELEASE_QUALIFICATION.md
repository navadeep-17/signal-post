# Q8 Fresh Release Qualification — Attempt 4

Date: 2026-10-06  
Decision: **GO / RELEASE QUALIFIED**

## Production under qualification

- repository: `navadeep-17/signal-post`
- qualified production main: `200f056a5a60cad23610a3958b6bec62dfb624a5`
- evaluator entrypoint: `scripts/run_signalpost_v8.py`
- exact qualification harness head: `93d3501fe5216f70f246c9ac97905bf2a1b14a4a`
- qualification workflow: `37403982422`
- qualification artifact: `11386579108`
- artifact name: `q8-fresh-release-attempt4-100`
- artifact ZIP SHA-256: `74401ccf2e1c11832bc91563ce02c8cb4ff040491542c563052049205a1b995e`

The qualification harness contained no production-code delta. It selected and ran a fresh cohort against the pinned production main.

## Freshness lineage

Seeds `20261104`, `20261105`, `20261106`, and `20261107` are permanently consumed.

Attempt 4:

- prior touched companies excluded: **8,723**
- exclusion SHA-256: `891773d05f4dd35b7ba8bc31d56c714df0c23d66ffeb868efe42dc84c5b65b0c`
- deterministic seed: **20261107**
- fresh cohort: **100**
- overlap with prior touched set: **0**
- fresh cohort SHA-256: `444304a8ac88154efceb121b61efecfa6541b16b4682f9f6bd5dc8f0b7c44b1b`

Two stale workflow executions were cancelled before cohort selection. Only workflow `37403982422` crossed the freshness boundary.

## Machine gates

| Gate | Result |
|---|---:|
| Terminal companies | 100 / 100 |
| Available claims | 4,600 |
| Core-evidence complete | 4,600 / 4,600 |
| Reopenable source | 4,600 / 4,600 |
| Identity-sensitive claims | 164 |
| Identity proof visible | 164 / 164 |
| Extraction method visible | 164 / 164 |
| Evidence-visibility issues | 0 |
| Precision guard idempotent | true |
| Precision guard residuals | 0 |
| Support companies | 12 |
| Support claims | 42 |
| Contract errors | 0 |
| Canonical errors | 0 |
| Synthesis errors | 0 |
| Dangling evidence references | 0 |
| Support projection errors | 0 |
| Observed conservative request charge | 1,376 / 2,000 |
| Theoretical conservative ceiling | 2,000 / 2,000 |
| Wall runtime | 629.722 s |
| Third-party API cost | $0.00 |
| Search API requests | 0 |

## Manual exact-company precision audit

The machine verifier intentionally did not finalize release status by itself. Every evaluator-visible external publication and every official support row was manually reviewed after the artifact was frozen.

### External publications

Reviewed: **20 rows across 5 companies**

Composition:

- 5 official websites
- 9 explicit company-declared social/profile handles
- 4 social-link aggregate claims
- 2 same-domain contact emails
- 0 careers claims
- 0 job-posting claims
- 0 company-update claims

Companies reviewed:

- `982762618` — OSLO TENNISARENA AS
- `931102036` — NORLANDIA OMSORGSBYGG AS
- `990989982` — GULLFUGL AS
- `911712148` — GEOPROVIDER AS
- `932219670` — VVS EKSPERTEN AS

Result: **0 known wrong-company publications**.

The previously observed failure families from attempt 3—service links as careers, tenant/profile links as careers/news, future activity dates, and default CMS posts—did not recur.

### Official support rows

Reviewed: **42 rows across 12 companies**

All rows passed:

- exact primary recipient organisation number equals the target;
- recipient legal name equals the cohort legal name;
- official Brønnøysundregistrene Støtteregisteret source;
- unique source-row key and row SHA-256;
- frozen source snapshot SHA-256;
- required `official_support_registry_primary_recipient_exact_org_v1` extraction method;
- no future dates;
- no rows outside the configured lookback;
- no duplicate row keys or row hashes;
- no amount/interval anomalies.

Result: **0 support audit anomalies**.

## Release decision

**Q8 GO.**

Production `main@200f056a5a60cad23610a3958b6bec62dfb624a5` passed both the fresh machine gate and the independent manual precision gate. The seed-`20261107` artifact is frozen evidence and must not be regenerated as a fresh qualification run.

The historical certified 1,000-company artifacts remain compatibility evidence only. Builderr supplies the official company batch at scoring time, so the current submission should pin the qualified V8 evaluator and include the fresh 100-company smoke/qualification report rather than claim that the historical corpus is the scored input.
