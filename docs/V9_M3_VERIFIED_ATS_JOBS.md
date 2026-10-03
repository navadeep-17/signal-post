# V9 M3 verified careers → ATS jobs

Status: **EXPERIMENT / SUPPORTING INFRASTRUCTURE — NOT PRODUCTION-PROMOTED**

Updated: 2026-10-03

M3 tests whether an exact verified company-owned careers page can provide a precision-safe provenance chain to a specific external ATS job posting.

## Trust chain

A job can only progress through:

1. exact verified company website;
2. same-company careers page;
3. direct outbound link from that careers page to a recognised provider-specific ATS destination;
4. specific ATS role page;
5. structured `JobPosting` employer/currentness validation.

Careers presence and ATS provenance are not active-vacancy claims by themselves.

## M3a offline gate

The experiment supports conservative recognition for Teamtailor, Greenhouse, Lever, Workday, Jobbnorge, SmartRecruiters and Recruitee.

A structured role can reach `publishable=True` only when:

- the ATS link chain is trusted;
- the role stays on the company-linked ATS provider;
- a specific job title exists;
- structured `hiringOrganization` exactly aligns with the target company after ordinary legal-suffix normalisation;
- `datePosted` is explicit;
- `validThrough` is explicit and not expired at qualification time.

Wrong employer/parent/namesake records are rejected. Missing currentness evidence remains review-only.

Exact-head Baseline run `37113645718` passed the full repository suite, certified 1,000-company audit, frozen submission verifier and refresh checks.

## M3b reused-careers screen

Workflow run: `37113791875`

Artifact: `v9-m3-reused-careers-screen` (`11270501724`)

The screen reused the two company-owned careers pages already qualified in the earlier careers milestone. It consumed no fresh qualification cohort.

Measured result:

- careers surfaces attempted: 2;
- network requests: 4 / 4 ceiling;
- third-party API cost: $0.00;
- companies with a supported direct ATS link: 1/2;
- supported ATS links: 1.

Results:

- `LUCERNA AS` (`982897327`) directly linked from `https://www.lucerna.no/karriere` to Jobbnorge role `300075`, `drifts-og-vedlikeholdsmedarbeider`;
- `BK VENTILASJON AS` (`936618200`) exposed no supported ATS link on its qualified careers page.

This proves the company-owned careers → specific ATS-role provenance chain occurs in the real sample.

## M3c specific ATS target qualification

Workflow run: `37113915037`

Artifact: `v9-m3-linked-ats-qualification` (`11271131902`)

The exact Jobbnorge target was fetched with a two-request ceiling (robots + role page), as-of `2026-10-03`.

Measured result:

- targets: 1;
- requests: 2 / 2 ceiling;
- third-party API cost: $0.00;
- structured jobs seen: 0;
- publishable jobs: 0;
- role-page fetch did not yield an eligible page to the bounded runner, so Signalpost abstained.

Contemporary indexed copies of the same role identify it as inactive. That external observation is useful for diagnosis only and is not production evidence.

## Decision

**HOLD / no direct production promotion yet.**

M3 demonstrated a real high-confidence provenance chain, but the tiny reused sample yielded zero current publishable jobs. The implementation is therefore retained for future websites/careers pages unlocked by M1 rather than being wired into production now.

This is a precision-preserving NO-GO: the system found an ATS role but did not mislabel an unavailable/inactive posting as current hiring.

Next:

- keep M3 as supporting infrastructure;
- let M1 website discovery expand the eligible careers population;
- prioritize M4 dated first-party company updates while waiting for Builderr's model-key/budget clarification.
