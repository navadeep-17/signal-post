# V10 M26 — strict consumed-20 local pilot runbook

Decision: **PREVIEW-READY ONLY / LIVE NOT EXECUTED / DRAFT / DO NOT MERGE**.
Date: 2026-10-09. Branch based on M25, itself based on the immutable V8 qualified release.

## Tavily account evidence

User-provided dashboard screenshots show Researcher, 40 of 1,000 monthly credits used, 960 remaining **at screenshot time**, pay-as-you-go **off**, and a masked development API key already created. This is not proof that the key is usable in Builderr's execution environment; live quota may change. Tavily Support's 2026-10-08 written reply generally permitted competition use and third-party server-side evaluator credentials. Aggregate Signalpost coverage may be disclosed without naming or comparing search providers.

## Implementation

scripts/run_v10_m26_consumed_pilot.py imports M24's immutable 20-company cohort manifest and verifies all three archived ZIP SHA256s, embedded frozen cohort manifests, 300 disjoint consumed organisation numbers, published V8 baseline records, and the exact original M24 7/7/6 ID order SHA256. Uses no sealed M20 Gate B, no fresh company IDs.

**Default operation is an offline preview, with zero external provider/website calls even if a key exists in the environment.** The only network-enabled path needs all of these explicit flags:
- --execute-live
- --confirm-pay-as-you-go-off
- --confirm-credits-at-least-20
- --confirm-server-side-use

In that mode the private runner separately requires the TAVILY_API_KEY environment variable. No key value is recorded in Git, output or logs, and this CI deliberately never passes the flag or key.

For one exact company, the path reserves 1 logical request for one Basic Search, no retry and no redirects; nominates at most one candidate URL; reserves up to 2 logical requests for the first-party robots + homepage fetch; then applies M23's existing independent webpage proof, wrong legal-entity and registry-risk vetoes, **plus the target exact nine-digit organisation number must appear on the fetched company page**. Cross-domain redirects and non-verified pages are rejected. Every candidate remains a *manual review item*, not a published website claim.

20-company upper bound: 60 logical HTTP requests reserved; 120 conservatively charged. M26 limits its local pilot to 600 seconds. These bounds DO NOT prove full 100-company V8 budget compliance or full evaluator runtime; this is an independent development-only runner, not a production integration.

M26 private JSON reports can only be written under gitignored out/ and contain source company IDs, statuses, and independently fetched company website URL + SHA256 for manual candidates. No provider query, title, snippet, ranking, answer, raw response or key is published or persisted.

## Reproduce the no-network preview

Download exactly the previously used GitHub Actions artifact ZIPs:

1. M19 A, artifact 11505218381: save as m19-a.zip.
2. M19 B, artifact 11525046472: save as m19-b.zip.
3. M20 A, artifact 11525304908: save as m20-a.zip.

Then run (no key or additional flags):

    uv sync --locked
    uv run python scripts/run_v10_m26_consumed_pilot.py --m19-a m19-a.zip --m19-b m19-b.zip --m20-a m20-a.zip

The CI securely retrieves the same three existing artifacts and runs this preview. It must yield exactly 20 dry-run rows, no API calls, no first-party website requests, zero charges, zero published claims. A test additionally tries --execute-live with a FAKE_TEST_ONLY key but without the positive confirmation flags and demands that it fail BEFORE requests.

## Private live pilot — planned, NOT done

When you are ready for a real run, confirm the latest available account credits, confirm pay-as-you-go is still disabled and use a *private machine's secure environment variable* for the Tavily key, never GitHub source, chat messages, public logs or committed .env files. Add all four explicit live flags above to the same command. This uses up to 20 Basic Search credits if each request costs one credit. No key/credit is yet available to this agent, and no real calls have been made in M26.

Never upload full provider results or a private, provider-specific performance report to a public issue, PR or workflow artifact. Public summaries must be provider-neutral as Tavily Support instructed.

## Promotion conditions

- Independently review every proposed new domain, including exact legal number, registry entity, final hostname, redirects, legal-name/ownership collision and original first-party evidence.
- At least 2 net additional exact-company websites in the *already-consumed* development 20, zero wrong entities, zero lost baseline claims, no contract/canonical/synthesis regressions.
- After a material development gain, prove an actual **replacement** path in the V8→V7→V2→V1 runner, never append three requests. 100-company theoretical conservative charge must remain <=2,000, end-to-end runtime <=2,400 seconds and third-party provider cost $0.
- Verify Builderr can securely supply the evaluator key without key disclosure; otherwise keep Tavily optional and maintain qualified zero-secret V8.
- Then run a separately frozen, disjoint *consumed* 100-company transfer before any fresh qualification or production merge.

M26 is an experiment, not an automatic V8 enhancement or verified recall improvement.
