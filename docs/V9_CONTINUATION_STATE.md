# Signalpost V9 Continuation State

Last updated: 2026-10-07

Live GitHub is authoritative if any recorded SHA advances.

## Frozen production boundary

- production `main`: `72f1bf2892ec1c1e35674aa383433c9a37afdaca`
- V8 qualified SHA: `200f056a5a60cad23610a3958b6bec62dfb624a5`
- V8 qualified ref: `release/v8-qualified-2026-10-06`
- V8 submission ref: `release/v8-submission-2026-10-06`
- research archive: `research/bulk-exact-org-recall`
- no research branch may be merged wholesale
- fresh qualification remains locked

Production `main` is still frozen. V9 remains isolated.

## Promoted V9 lineage

### M2 — BRREG registry-email-domain substitution

**PROMOTE** after retune.

Promoted head: `5fda04cd81f1cbba77ee741361e3b5bd064a0d86`.

The final M2 policy preserves `exact`, `acronym`, `multi`, and `partial` email-domain
candidates and substitutes only clearly unrelated `none` candidates. Candidate morphology is
nomination only; the existing exact-company verifier remains authoritative.

Targeted consumed transfer covered all 54 behaviorally affected companies:

- verified websites: **8 -> 9**, net-new **+1**, lost **0**
- scored family-company edges: **+4**, lost **0**
- observed conservative request charge: **1602 -> 1418**
- theoretical ceiling: **2000 -> 2000**
- all new publications manually audited
- wrong-company publications: **0**
- search API requests: **0**
- third-party cost: **$0**

### M4 — zero-request structured contact recovery

**PROMOTE**.

Canonical isolated PR: **#143**. The overlapping stacked PR #144 is superseded and must not be
revived.

Standalone measured head: `e931519d58f82c79fc96b8e7fd54cb5143819b71`.

Frozen-consumed-1000 replay:

- external contact-email companies: **53 -> 58**
- external contact-phone companies: **0 -> 19**
- any external-contact companies: **53 -> 60**
- new contact claims: **26**
- existing contact losses: **0**
- non-contact changes: **0**
- network requests added: **0**
- manual audit: **26/26 accepted, 0 wrong-company**

### Integrated M2 + M4

**PROMOTE** as the V9 base.

Qualified integrated head: `ce0efaf7a2abba82b66726111ed488bf5185fa3a`.

Consumed exact-head gate `37496552710`:

- verified websites: **8 -> 9**
- social: **5 -> 6**
- external contact: **4 -> 6**
- careers: **2 -> 3**
- hiring intent: **0 -> 0**
- active jobs: **0 -> 0**
- dated first-party activity: **2 -> 2**
- total net-new scored family-company edges: **+5**
- total lost edges: **0**
- new external publications: **8**
- manual audit: **8/8 accepted, 0 wrong-company**
- observed conservative request charge: **1602 -> 1418**
- theoretical ceiling: **2000**
- cost/search: **$0 / 0**

### M5 — hiring semantics

**PROMOTE**.

Promoted/cleaned lineage base:
`dc5907b27fb8844b0f690a166937bf908f058a73`.

M5 preserves three separate meanings:

- careers surface
- company-authored hiring intent
- specific active job posting

Consumed-1000 replay added **1** exact first-party company-authored hiring-intent company at
zero added requests, with no careers/job/non-intent losses and no contract/canonical/synthesis
errors. Manual precision audit accepted **1/1** publication with zero wrong-company or
specific-vacancy overclaim.

This is the current promoted V9 code base.

## Shelved milestone

### M6 — structured dated first-party activity

**SHELVE**.

Measured implementation head:
`b01eefd201c439f76fc25da4ddfd81a57dcc561b`.

Exact-head evidence:

- Baseline CI `37512933250`: PASS
- consumed transfer `37512929936`: PASS
- artifact `11437162970`
- digest `sha256:2eef40b02a85079ba6ae55724754dea55b7a6653826e071d0c6766325f215215`
- dated activity companies: **8 -> 8**
- net-new/lost dated activity companies: **0 / 0**
- new/lost activity publications: **0 / 0**
- non-activity family changes: **none**
- conservative request charge: **1892 -> 1892**
- theoretical ceiling: **2000 -> 2000**
- search requests / third-party cost: **0 / $0**
- fresh companies used: **0**

Reason: the implementation is strict and budget-neutral but produces zero measured scored-family
lift. M6 is therefore not carried into the promoted lineage.

## M7 decision

**SHELVE / NO NEW PRODUCTION IMPLEMENTATION**.

M7 revalidated secondary deterministic candidate sources and found no genuinely new primitive that
clears the novelty, exact-identity, rights, request-economics, and expected-family-lift bar.

- exact-parent BRREG subunit homepage: prior **0/3** exact target sites;
- exact-parent BRREG subunit email-domain: prior **0/10** exact target sites;
- broad NAV feed scan: prior **0/20** exact active-job matches after **54** logical requests;
- Wikidata exact P2333 -> P856 already exists in the promoted base;
- deterministic legal-name H1c/H1g already exist;
- historical-name DNS/Norid paths remain stopped.

Docs-only M7 head: `e696819a4a8e6bc7dcdeb5225aa57367a59df4cc`.
Baseline CI `37517206468`: **PASS**.

No production code, request class, external dependency, paid/search API, or fresh cohort was added.

## M8 decision

**SHELVE NAV extension / retain existing strict first-party JobPosting behavior.**

The promoted base already satisfies the first-party specific-job contract. The prior NAV broad-feed
screen remains below the promotion bar: 20 targets, 30,000 feed items, 54 logical requests, and
zero exact main/subunit organisation-number matches.

Docs-only M8 head: `39e4bb31f08206ae9e8f49cb9fce57d00ede441a`.
Baseline CI `37517809343`: **PASS**.

No production code, request class, paid/search API, or fresh cohort was added.

## Active milestone

**M9 — optional organisation-number-first search.**

Active branch:
`experiment/v9-m9-optional-search`

Code behavior remains promoted M5.

M9 is conditional. Search output is nomination only and may never serve as evidence or exact
identity proof. Search can be activated only if Builderr explicitly supplies a reproducible
provider/key and confirms the environment variable and budget before revision freeze.

Current Builderr clarification means the official path must remain credential-free: no general
model provider or web-search tool is injected by default and participant-owned API keys are not
used.

PR #137 remains parked as a draft optional future fallback and must not be merged or enabled now.

## Builderr / budget rules

Official per-100-company limits:

- wall clock: **45 minutes**
- outbound requests: **2,000**
- external API spend: **$10**

No general paid model/search provider is injected by default. Participant-owned API keys are not
part of the official path. Production V9 remains credential-free.

PR #137 stays parked as optional M9-only search fallback. Paid/model search may be reconsidered
only if Builderr explicitly supplies a reproducible provider/key. Internal planning ceiling would
be **$8**, retaining about **$2 reserve**.

## Hard locks

Do not:

- modify or move V8 release refs;
- modify `main`;
- merge research branches wholesale;
- weaken the exact-company verifier;
- use candidate/search output as evidence;
- add requests without re-proving the worst-case theorem;
- consume a fresh cohort before M10/M11 pass;
- revive stopped source paths unchanged;
- stack shelved M6 behavior onto later milestones.

## Exact next action

Resolve M9 as **SHELVE/PARK** under the current Builderr credential-free constraint. Do not activate
PR #137, paid/model search, or any participant-owned key. After M9 is recorded, proceed serially to
M10 consumed transfer gates on the promoted integrated V9 code line.
