# Q3 — Search-assisted exact-company website discovery

Last updated: 2026-10-05

Status: **EXPERIMENT VALIDATED / PRODUCTION HOLD / FRESH QUALIFICATION NOT CONSUMED**

## Decision

Keep the Q3 search-assisted discovery implementation as a reusable experiment, but **do not integrate it into the production evaluator yet**.

The downstream exact-company verifier behaved conservatively on consumed data, but the deterministic consumed-only proxy produced only **1 verified site / 20 unresolved companies (5%)**. That is below the project’s threshold for spending scarce production request slots or consuming a new fresh qualification cohort.

No fresh Phase-11 company was consumed by this decision.

## Why Q3 was reopened

The earlier project policy treated `$0 third-party API cost` and `0 search API requests` as release constraints. Builderr's current challenge page now explicitly states that LLMs are allowed, each official run has a small external API budget, and Builderr can supply a model key for scoring. It also makes recall/coverage the largest scoring component at 50/100 and uses lower third-party cost only after wrong-company publications and recall in the tiebreak order.

Therefore `$0` remains a useful optimization target but is no longer treated as a challenge requirement.

Current official challenge reference checked 2026-10-05:

- https://builderr.ai/challenges/signalpost

## Current OpenAI provider facts

The Q3 experiment uses the OpenAI Responses API only as a transient URL nominator.

Public OpenAI documentation checked 2026-10-05 supports:

- Responses API built-in `web_search`;
- `tool_choice = required`;
- `max_tool_calls` to bound built-in tool usage;
- `search_context_size = low|medium|high`;
- `gpt-6-luna` as a current low-cost model;
- web search price: $10 / 1,000 calls plus search-content tokens at model rates;
- Standard short-context `gpt-6-luna`: $0.10 / 1M input tokens and $0.50 / 1M output tokens.

References:

- https://platform.openai.com/docs/api-reference/responses
- https://platform.openai.com/pricing

The runner does not assume Builderr's exact dollar ceiling. A live run requires an explicit `--max-external-api-cost-usd` value confirmed for that run.

## Q3 experiment architecture

```text
exact organisation number + legal name
 -> one bounded OpenAI web-search call
 -> transient cited/source URLs
 -> reject directory/social hosts
 -> dedupe by registered domain
 -> at most two independently crawled candidates
 -> current bounded homepage fetch
 -> current website identity gate
 -> current search-discovered page corroboration
 -> multi-entity / conflicting organisation-number veto
 -> publish only if exact-company proof survives
```

The model/search provider may nominate URLs. It may **never** establish legal identity.

## Precision hardening added during Q3

A consumed screen exposed a dangerous pattern: a group/company-overview page can contain the target organisation number alongside several other legal entities. Exact target-ID presence alone is therefore insufficient for a search-discovered candidate page.

Q3 adds a search-specific multi-entity veto: when independently fetched candidate identity evidence explicitly contains the target organisation number **and** another organisation number, the candidate is quarantined rather than published. This supplements the existing wrong-org and explicit site-owner guards; it does not weaken any existing identity rule.

## Consumed-only replay evidence

### A. Adversarial four-company replay

Frozen nominations:

1. `LØRENSKOG RENHOLD & SERVICE AS` — `940762642` — dedicated first-party candidate;
2. `XL-BYGG MATHISEN & CO AS` — `997645359` — shared chain/store domain;
3. `BRAVO MATSENTER AS` — `939067442` — shared SPAR store domain;
4. `LADE NÆRINGSBYGG DA` — `981889967` — group overview containing multiple legal entities.

Result:

- accepted: **1/4**;
- quarantined: **3/4**;
- accepted company: Lørenskog Renhold & Service AS;
- logical verification requests: **8**;
- wrong-company publications: **0**.

This established that the downstream verifier rejects the shared-chain/group adversarial cases while retaining a dedicated exact-company positive.

### B. Deterministic 20-company public-search proxy

To avoid judging Q3 from handpicked positives, a deterministic 20-company subset was frozen from the 94 unresolved companies in the already-consumed Phase-11 cohort.

Selection rule:

```text
sort unresolved companies by sha256("q3-consumed-v1|" + organisation_number)
take first 20
```

Frozen organisation-list SHA-256:

`5c378da42b78ce4c4dfe4b71d0b074f912bde6ea704ebaf5f5b6abddf4d20269`

Public search surfaced four plausible first-party nominations:

- PREG BARNEHAGER ÅLESUND AS -> `pregalesund.barnehage.no`;
- NORSK NAVIGASJON AS -> `norsknavigasjon.no`;
- NORGES FLYMEDISINSKE SENTER AS -> `nfms.no`;
- RELOAD YOUR STYLE AS -> `thelounge.no`.

The other 16 companies had no plausible first-party nomination and remained explicit misses.

Replay result through the **actual independent bounded fetch + exact-company gate**:

- companies: **20**;
- accepted: **1 (5%)**;
- quarantined candidate pages: **3**;
- no candidate: **16**;
- logical verification requests: **8**;
- accepted company: **PREG BARNEHAGER ÅLESUND AS** (`930465143`);
- accepted URL: `https://pregalesund.barnehage.no/`;
- wrong-company publications: **0**.

The three other nominations were correctly not published:

- `nfms.no`: fetched but insufficient exact legal-entity proof;
- `norsknavigasjon.no`: source error in replay;
- `thelounge.no`: operating-brand site but insufficient exact legal-entity proof.

### Replay provenance

- workflow: `37328342354` — PASS;
- artifact: `11352149982`;
- artifact digest: `sha256:5611c946e0349c0bf2ababf2b33816f81525fd7b2ff212f6e1f25c98045256e7`;
- exact-head Baseline CI: `37328353539` — PASS;
- measured replay head: `e25e5370830dcbd0f91a1d15d6acf0f8349e6ab3`.

These are consumed-only measurements, not fresh qualification evidence.

## Persistence boundary

Never persist as company evidence:

- model answer text;
- search query text;
- provider raw response;
- provider citation titles;
- search rank as identity evidence;
- quarantined/ambiguous candidate pages.

Persist only:

- an operational discovery summary; and
- an independently fetched candidate page when it passes the current exact-company gate.

## Cost and request guards

Default provider bounds:

- <=1 hosted web-search tool call per queried company;
- `search_context_size=low`;
- <=180 provider output tokens per company;
- declared audit ceiling of 50,000 provider/search-content input tokens per company;
- <=2 independently fetched candidate domains per company.

At public Standard pricing checked for this experiment, the declared 100-company provider ceiling is approximately **$1.509**:

- search calls: 100 x $0.01 = $1.00;
- input/search-content ceiling: 5,000,000 tokens x $0.10/M = $0.50;
- output ceiling: 18,000 tokens x $0.50/M = $0.009.

This is an experiment-side ceiling, not a claim about Builderr's exact official-run allowance.

The production request theorem is unchanged because Q3 is not wired into V8 production. Any future production integration must explicitly reallocate request capacity before merge.

## Promotion decision

### Q3a — code safety

**PASS.**

- exact-head Baseline CI green;
- provider output nomination-only;
- one web-search call hard ceiling;
- explicit provider dollar budget required at launch;
- independent current identity gate unchanged;
- quarantined pages not persisted;
- multi-entity candidate guard added.

### Q3b — consumed/dev transfer

**HOLD.**

The deterministic proxy produced only 1/20 verified sites. This proves the mechanism can recover real sites, but it does not yet demonstrate enough transfer to justify production integration or a fresh cohort. The earlier provisional website-discovery target was at least 5/20; the measured 1/20 result is materially below it.

### Q3c — fresh transfer

**BLOCKED / NOT CONSUMED.**

Do not consume a fresh cohort for Q3 unless at least one of the following materially changes:

1. evaluator-reproducible search/provider credentials and exact budget are confirmed and a provider-specific consumed/dev run demonstrates meaningfully better nomination yield than the public-search proxy; or
2. a new nomination strategy materially improves consumed/dev verified-site yield without weakening the exact-company verifier.

## Final Q3 boundary

Q3 is a useful retained experiment, not a production feature. The correct next action is to move to the next qualification-sprint scoring lever using measured field-level coverage from the consumed output rather than repeatedly tuning website search against the same data.
