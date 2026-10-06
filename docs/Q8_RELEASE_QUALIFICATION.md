# Q8 Fresh Release Qualification — Attempt 4

Updated: 2026-10-06

Status: **GO / RELEASE-QUALIFIED**

This document records the final fresh evaluator-shaped qualification for the current Signalpost production candidate. It is release evidence, not a claim about Builderr's official score.

## Production candidate

- production branch: `main`
- qualified production commit: `200f056a5a60cad23610a3958b6bec62dfb624a5`
- post-merge Baseline CI: `37403437730` — **PASS**
- evaluator entry point: `scripts/run_signalpost_v8.py`
- third-party API cost: **$0**
- search API calls: **0**

The qualification harness lived only on PR #124 / `qualification/q8-fresh-release-attempt4`. That PR is intentionally **closed without merge**. Its harness files are not production code and must not be merged into the evaluator path.

## Freshness boundary

Earlier qualification seeds `20261104`, `20261105`, and `20261106` are permanently consumed.

Attempt #4 reconstructed the prior **8,623-company** exclusion from the successful attempt-3 artifact, appended the exact 100-company seed-`20261106` cohort, and produced **8,723 unique exclusions** before selecting the next cohort.

Fresh attempt #4:

- seed: `20261107`
- excluded prior companies: **8,723**
- selected companies: **100**
- overlap with prior touched companies: **0**
- fresh cohort SHA-256: `444304a8ac88154efceb121b61efecfa6541b16b4682f9f6bd5dc8f0b7c44b1b`

Seed `20261107` is permanently consumed and must never be regenerated as fresh evidence.

## Qualification execution

- workflow: `37403982422` — **SUCCESS**
- exact qualification head: `93d3501fe5216f70f246c9ac97905bf2a1b14a4a`
- exact-head Baseline CI: `37403985583` — **PASS**
- artifact: `q8-fresh-release-attempt4-100`
- artifact ID: `11386579108`
- artifact ZIP SHA-256: `74401ccf2e1c11832bc91563ce02c8cb4ff040491542c563052049205a1b995e`

Two stale armed runs were cancelled before cohort selection. Only workflow `37403982422` crossed the freshness boundary.

## Machine gate

The run passed all machine gates:

- **100/100** terminal company outputs
- **4,600/4,600** available claims with complete core evidence
- **4,600/4,600** available claims with reopenable sources
- **164/164** identity-sensitive claims with evaluator-visible identity proof
- **164/164** identity-sensitive claims with extraction method
- **0** evidence-visibility issues
- final external precision guard idempotent with **0 residual removals**
- **42** official Støtteregisteret support claims across **12** companies
- observed conservative request charge: **1,376 / 2,000**
- wall runtime: **629.722 s**
- third-party API cost: **$0**
- contract errors: **0**
- canonical errors: **0**
- synthesis errors: **0**
- dangling-evidence errors: **0**
- support-projection errors: **0**

## Manual precision gate

Every evaluator-visible external publication in the fresh run was manually reviewed.

External publication audit:

- total evaluator-visible external publications: **20**
- official websites: **5**
- company-declared social/profile handles: **9**
- social-link aggregates: **4**
- same-domain contact emails: **2**
- careers claims: **0**
- job-posting claims: **0**
- company-update/activity claims: **0**
- wrong-company publications: **0**

The five companies with external publications were:

- OSLO TENNISARENA AS (`982762618`)
- NORLANDIA OMSORGSBYGG AS (`931102036`)
- GULLFUGL AS (`990989982`)
- GEOPROVIDER AS (`911712148`)
- VVS EKSPERTEN AS (`932219670`)

All **42** official Støtteregisteret rows were also reviewed:

- exact recipient organisation number: **42/42**
- recipient legal name match: **42/42**
- official `stotte.brreg.no` source: **42/42**
- valid source-row key/hash and frozen snapshot hash: **42/42**
- expected extraction method: **42/42**
- future dates: **0**
- out-of-lookback rows: **0**
- duplicate row keys/hashes: **0**
- amount/interval anomalies: **0**
- support audit anomalies: **0**

## Decision

**Q8 attempt #4 is release-qualified.**

The current production code at `main@200f056a5a60cad23610a3958b6bec62dfb624a5` passed the required fresh machine gate and the independent manual precision gate.

Release discipline from this point:

1. do not merge PR #124 or its qualification harness into production;
2. do not consume another fresh cohort before the release decision;
3. allow documentation-only finalization, followed by exact-head Baseline CI;
4. freeze a release ref only after the final documentation PR is green;
5. submit that frozen production revision to Builderr;
6. treat any later production-code change as requiring a new qualification decision.

The previously submitted V8 revision remains authoritative on Builderr until a new revision is explicitly submitted.
