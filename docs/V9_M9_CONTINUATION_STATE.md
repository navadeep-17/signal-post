# Signalpost V9 M9 Continuation State

Last updated: 2026-10-07

## Decision

**SHELVE / PARK M9 optional search under the current Builderr environment.**

M9 is not activated.

The official V9 production path remains deterministic and credential-free.

## Builderr constraint

Current official clarification:

- no general model provider is injected by default;
- no web-search tool/provider is injected by default;
- participant-owned API keys are not used;
- if Builderr explicitly arranges a provider/key later, it must confirm the provider,
  environment variable, and budget before revision freeze;
- per 100-company shard limits remain 45 minutes, 2,000 outbound requests, and $10 total
  external API cost;
- paid model tokens and paid search/tool calls share that same $10 cap.

Internal planning, if a paid search path ever becomes officially available, should target no more
than $8 planned spend with roughly $2 reserve.

## Search semantics

Even if M9 reopens later:

1. query organisation number first;
2. only then consider legal name + municipality;
3. search result output is nomination only;
4. search output is never publication evidence;
5. search output is never legal-entity identity proof;
6. every candidate must be independently fetched and pass the unchanged exact-company verifier;
7. access/provider/key/cost must be evaluator-reproducible;
8. search outputs should remain transient rather than becoming unsupported evidence snapshots;
9. request and cost theorems must be re-proved before promotion.

## Parked implementation

PR #137 remains a draft optional future adapter. It must not be merged, enabled, or used for the
official V9 path under the present environment.

No participant-owned key is introduced.

No fresh cohort is consumed.

No production code changes are made by M9.

## Final result

**SHELVE/PARK**.

The absence of an official reproducible provider/key means M9 cannot be part of the release
candidate now.

## Exact next milestone

Proceed serially to **M10 — consumed transfer gates** on the promoted integrated V9 code line
(M2 + M4 + M5), excluding shelved M6 behavior and with M7/M8/M9 adding no production behavior.

M10 must compare baseline and challenger on identical already-consumed companies, preserve zero
wrong-company publication, require manual audit of every new external publication, and prove no
contract/canonical/synthesis regression before any fresh cohort is touched.
