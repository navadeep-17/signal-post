# V10 M24 — permission-first consumed-development cohort

Date: 2026-10-08
Decision: **OFFLINE COHORT FROZEN / RIGHTS NOT CLEARED / NO LIVE RUN / NO MERGE**
Qualified V8 parent: 200f056a5a60cad23610a3958b6bec62dfb624a5
Related offline search-nomination prototype: PR #173

## Exact scope

M21 established that 259 of 300 previously evaluated companies lacked a qualified website. M22 established that a potential search-plus-independent-first-party-fetch must replace existing site requests, not add a new request family. M23 created and tested a synthetic, no-network Tavily nomination adapter, not a live evaluator.

M24 freezes the **development-only** next gate, without running it:

- Input: only three previously consumed, archive-verified batches: M19 Gate A (run 37670190338, artifact 11505218381), M19 Gate B (run 37717545307, artifact 11525046472), M20 Gate A (run 37720279568, artifact 11525304908).
- Each original ZIP and embedded cohort manifest SHA256 is pinned in scripts/freeze_v10_m24_consumed_dev.py, and each ZIP contains an already-successful V8 report, 100 original profiles, and 100 original published outputs.
- Required eligibility: legal name and municipality present; no registered website seed; no published available official_website claim.
- Fixed selection: within each previously consumed batch, ascending SHA256 of "signalpost-v10-m24-consumed-development-v1|" plus Norwegian organisation number, select respectively 7, 7 and 6 entries.
- evaluation/v10_m24_consumed_dev_20.json contains the exact 20 selected IDs and their list SHA256. Its entries are public identifiers, but they are purposefully disclosed DEVELOPMENT subjects, never fresh qualification data.
- The dedicated M24 CI downloads only those three archived evidence artifacts, verifies content digests and 300-company disjointness, re-selects the 20, compares exact IDs and checksum, and negatively tests one-byte archive tampering.
- We did not open M20 sealed Gate B, fetch any new company pages, spend API credits or money, publish new facts, change main or alter qualified V8.

This cohort is deliberately enriched for unseeded website discovery, **not representative of all Norwegian companies** and NOT an independent post-development transfer test.

## Provider terms and account gate

Primary source: https://www.tavily.com/terms (Platform Terms dated 2026-05-04).
Section 2 bars third-party use of customer API/agent keys without prior written consent. It is NOT established whether an independent Builderr evaluator may run a project key in its environment or requires written authorization/separate credentials.
Section 3.2(x) restricts disclosure of performance information or analyses concerning Tavily's services. It is NOT established whether publishing Signalpost's aggregate challenge results alongside provider details is permitted.
Source https://www.tavily.com/pricing: Researcher Free advertises 1,000 credits/month and no card. Source https://help.tavily.com/articles/6938147944-basic-vs-advanced-search-what-s-the-difference: Basic search is 1 credit. Source https://help.tavily.com/articles/3240802908-rate-limits: dev keys have a published 100-request/min limit, which is NOT an end-to-end 2,400-second guarantee.
No actual account key, current quota, free-account billing state, third-party evaluator agreement or written rights approval is established. A connected ChatGPT Tavily app is not a usable standalone evaluator key.

## Permission inquiry, NOT SENT

To: support@tavily.com
Subject: Usage permission — Tavily Basic Search in student-built Signalpost software challenge

Hello Tavily Support,

We are developing Signalpost, a student-built Norwegian company-intelligence application for an external software challenge. We are considering the Tavily Researcher Free / Basic Search API only to nominate candidate public homepages of organisations identified by Norwegian company registration numbers. We would independently fetch those public websites and require exact legal-entity proof before publishing any company facts. We would NOT retain or publish Tavily result snippets, provider scores/rankings or generated answers as evidence.

Could you please confirm in writing:
1. Is this student competition and third-party evaluation use allowed under Researcher Free?
2. Under your Platform Terms section 3.2(x), may we publish aggregate metrics about Signalpost's own factual company coverage in a challenge report, avoiding Tavily-specific performance comparisons and latency disclosures?
3. Under section 2, may an independent external evaluator run our application with a server-side, non-disclosed Tavily key, or is separate written consent or an evaluator-owned key required?
4. Subject to current monthly credit balance and published rate caps, is up to 100 Basic Search API requests per 100-company evaluator batch allowed at no charge? Are there other relevant retention, redistribution, or attribution restrictions if provider results are transient?
5. May we make our own application code public without provider keys or search result redistribution?

We would not run provider searches or assume third-party access rights before clarifying these points. Thank you.

Source for support address: https://help.tavily.com/articles/9386896045-welcome-to-tavily (support@tavily.com), and the official contact page https://www.tavily.com/contact.

## Predeclared future gates

**Do not begin the live 20-company pilot unless all pass:**
1. Actual provider-terms clearance covering competition use, public report scope and evaluator access.
2. Appropriately authorized server-side key in the evaluator, no credentials in Git.
3. Verified free account credits and explicit no-pay-as-you-go / no-upgrade stance.
4. Production-code proof of request-slot substitution under the existing conservative 2,000 / 100-company limit. 1 provider search + max 2 logical independent homepage requests must fit inside the four site slots. Naive extra calls would exceed the ceiling.
5. Worst-case (100 companies, provider latency/errors and rate caps) 2,400-second wall-time proof, not inferred from published 100 RPM.
6. Existing first-party site proof and wrong-owner/foreign-entity/parent guard never weakened.

After rights and technical gates, query ONLY this already-consumed 20-company development cohort. Require at least **2 net-new independently exact-qualified sites / 20**, zero incorrect legal entities, zero lost baseline claims, zero contract/canonical/synthesis regressions, and 100% manual audit of proposed new claims. This is a **threshold, not a result**.

Even a passing consumed-20 would require a separately frozen zero-overlap consumed 100-company transfer gate before promotion, followed by fresh validation only if justified.

**Final M24 decision: OFFLINE READINESS COMPLETE / PROVIDER BLOCKED / qualified V8 + main unchanged.**
