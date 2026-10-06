# V9 OpenAI Web Search Provider V2

Updated: 2026-10-06

Status: **OFFLINE CONTRACT READY; LIVE GATE CLOSED**

This is an isolated V9 provider experiment. It does not change V8, `main`, or the current Builderr submission.

## Why V2 exists

The older `experiment/v9-openai-websearch-provider` branch let the model return candidate URLs in structured output. That is unnecessarily permissive for Signalpost's precision-first identity model.

V2 changes the trust boundary:

```text
OpenAI Responses API
        |
        | one required web_search tool call
        v
web_search_call.results / action.sources
        |
        | deterministic transient scoring only
        v
<= 3 untrusted URL nominations
        |
        | fresh independent HTTP fetch
        v
existing exact-company verifier
        |
        +--> exact -> eligible for later publication path
        |
        +--> ambiguous/wrong -> discard
```

Assistant prose, reasoning, citations and model-generated URL strings are ignored by the nomination parser.

## Current provider API assumptions

The adapter is pinned to `gpt-6-luna` and the Responses API.

Official OpenAI references reviewed on 2026-10-06:

- model: https://developers.openai.com/api/docs/models/gpt-6-luna
- web search guide: https://developers.openai.com/api/docs/guides/tools-web-search
- Responses include fields: https://developers.openai.com/api/reference/python/resources/responses
- pricing: https://developers.openai.com/api/docs/pricing

Current standard-price assumptions encoded for experiment telemetry:

- GPT-6 Luna input: **$0.10 / 1M tokens**
- GPT-6 Luna output: **$0.50 / 1M tokens**
- web search: **$10 / 1,000 calls = $0.01 / call**

Pricing is an operational estimate, not an invoice or a Builderr budget declaration.

## Request contract

Each company request is bounded to:

- model `gpt-6-luna`;
- `reasoning.effort = none`;
- `store = false`;
- one `web_search` tool with `search_context_size = low`;
- `tool_choice = required`;
- `max_tool_calls = 1`;
- `parallel_tool_calls = false`;
- `include = ["web_search_call.results", "web_search_call.action.sources"]`.

The prompt emphasizes exact Norwegian organisation number and legal name, but prompt/model output never authorizes identity.

## Data-retention boundary

Transient provider fields may help decide which URL to fetch:

- result URL;
- result title;
- result snippet/description when present;
- provider rank;
- provider query text in memory.

Returned/persistable nomination output contains URL decisions, hashed query identifiers and cost telemetry only. It does not retain provider result title/snippet, assistant prose, citations, or reasoning as company evidence.

## Fail-closed behavior

The adapter abstains when:

- no evaluator/API key is available;
- more than one web-search call appears;
- the tool action is not a search;
- the API request fails;
- no source/result URL survives the existing V9 candidate hygiene and scoring gate.

A source URL with no title/snippet receives no synthetic identity evidence.

## Provider gate remains closed

The implementation deliberately does **not** self-declare:

- evaluator reproducibility;
- evaluator key availability;
- challenge/provider rights approval;
- non-zero project third-party spend.

`provider_readiness(...)` therefore remains blocked under the default V9 state.

A live Gate-A provider run may happen only after the challenge/provider handoff explicitly confirms:

1. the evaluator-supported model/provider path;
2. how the model credential is injected during scoring;
3. the permitted rights/use state for this path;
4. the external API dollar ceiling and whether web-search charges count inside it;
5. a non-zero project experiment budget consistent with that ceiling.

Do not use a personal third-party credential as evidence of evaluator reproducibility.

## Promotion rule

Even a provider-gate PASS would authorize only the same frozen consumed Gate-A experiment.

The provider must still reach at least **5 / 20 new exact-company websites** on the frozen Gate-A cohort, with:

- 0 wrong-company publications;
- 0 evidence defects;
- unchanged exact-company verification;
- bounded request/runtime/cost;
- no fresh cohort consumed for tuning.

Until then this branch remains experiment-only.
