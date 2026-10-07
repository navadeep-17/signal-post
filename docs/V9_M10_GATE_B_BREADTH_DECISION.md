# V9 M10 Gate B — consumed transfer and scoped precision decision

**Decision (2026-10-07): technical Gate B PASS; evidence-based breadth HOLD. Do not promote V9 or run fresh qualification on this basis.**

## Frozen evaluation identity

- Gate A 20 run: `37565180008`; artifact `11458838045` SHA256 `928e9ff4f11eb2ad078b0455c66e574c6c6bb7ec6e2ef2a8ccce123a73808e9f`; fully scoped 11/11 approval in `docs/V9_M10_GATE_A_MANUAL_REVIEW.json`.
- Governing Gate B 100 run: `37567829642`, [actions page](https://github.com/navadeep-17/signal-post/actions/runs/37567829642); archived machine, cohort and publication evidence artifact `11459639663` SHA256 `f33211ff123dd58c59b56d74d4d5910f7dbb7e87629e785ade54878c93955119`.
- Evaluators (pinned): V8 `72f1bf2892ec1c1e35674aa383433c9a37afdaca`, V9 M2+M4+M5 `2848ed505103b3cbb0a3bf8d6313ee1ba7a25ecf`.
- One shared registry snapshot for V8 and V9, same 100 organisations drawn from frozen consumed 1000. No fresh cohort, no paid API or search calls.

## Machine results (consumed Gate B 100)

| Screen | V8 baseline | V9 candidate | Interpretation |
|---|---:|---:|---|
| Terminal profiles | 100/100 | 100/100 | Complete |
| Verified websites | 9 | 10 | +1, no losses |
| Social family | 5 | 6 | +1, no losses |
| External contact family | 4 | 7 | +3, no losses |
| Careers surface | 3 | 4 | +1, no losses |
| First-party hiring intent | 0 | 1 | +1, not active job |
| Specific active job | 0 | 0 | No lift |
| Dated first-party activity | 2 | 2 | No lift |
| Observed conservative request charge | 1610 | 1426 | 184 fewer charged requests |
| Theoretical charge ceiling | 2000 | 2000 | Exactly the permitted maximum |
| Wall runtime seconds | 814.584 | 759.930 | <45 minutes |
| Paid external API / search | $0 / 0 | $0 / 0 | Unchanged |
| Source-level reported errors | 147 | 152 | Five *additional* nonfatal source errors; track, not 0 |

New company-family edges: **7**, lost **0**; new external publications **11**, lost **0**; automated evidence defects **0**, machine screen **MANUAL_AUDIT_REQUIRED** with `errors=[]`. Source-level errors are distinct from schema/evidence/contract validation failures.

## Eleven distinct publications — assistant claim review

All **11** Gate B tuples (`organisation_number`, exact `field`, JSON-`value`) match previously approved Gate A tuples. Every repeated entry also matches the previously inspected `source_url`, retained content SHA-256, extraction method and quoted claim span. Each Gate B evidence check is true. These are *repeated observations*, not eleven newly-discovered companies and not an independent review by a named human.

1. ENTALPY AS `927097532` (3): `frank@entalpy.no`, `+4790564983`, explicit `Vi søker` company-authored recruitment **intent**. No current vacancy proven. First-party `https://entalpy.no/`, hash prefix `93a79060`.
2. VOLF AS `979943377` (2): `post@volf.no`, `+4770275662`, exact organisation-number identity in structured same-company node. First-party `https://volf.no/`, hash prefix `083de127`.
3. DEN GLADE GRIS AS `999096298` (6): official verified restaurant site `dengladegris.no`, careers **surface**, homepage-declared Facebook and Instagram **URLs** (no platform fetch, current activity or account control asserted), same-domain `booking@dengladegris.no`, structured restaurant phone `+4722111710`. Domain independently corroborated to legal company/operator despite 2026 BRREG business-address correction; no dependence on obsolete location equivalence. First-party `https://www.dengladegris.no/`, hash prefix `a9d8388c`.

**Scoped precision verdict:** the 11/11 previously reviewed publications remain approved at the same narrow scope. Zero observed wrong-company publications or semantic overclaims for these eleven. This assistant-led audit is **not represented as an independent human reviewer certification**; Builderr's hidden precision metric remains unknown. See [PR #156 manual decision comment](https://github.com/navadeep-17/signal-post/pull/156).

## Most important transfer finding

Gate A's 20 companies are a subset of Gate B's 100. **All** eleven Gate B new-publication tuples are the **same** eleven Gate A tuples from the **three forced positive canaries**. There are **zero new publication tuples contributed by the additional 80 companies**; all seven company-family gains are also already counted in Gate A.

Thus a 20→100 expanded denominator is *not* evidence of broader incremental generalization. Do not add Gate A's seven gained edges to Gate B's seven, portray Gate B as seven additional gains, or treat our within-consumed transfer as Builderr's hidden >=60% recall proof. The study is conditioned on previously observed positive canaries. The request performance is favorable, but the externally useful coverage improvement demonstrated outside those canaries is **zero**.

## Next safe decision

- Keep PR #154 (Gate A), #156 (Gate B) and #157 (M11 static request theorem) as draft and unmerged.
- The read-only reproducibility check `scripts/audit_v9_m10_gate_b_breadth.py` and companion artifact-only workflow should return `HOLD_BREADTH_CANARY_ONLY` on the frozen real evidence. It does not rerun the evaluator or spend website requests.
- Prioritize a *pre-registered* next consumed-only candidate-discovery and allocation analysis that could improve company-family coverage beyond known positive canaries while preserving exact-identity/source-rights screens, the worst-case 2,000-request charge bound, $0 cost and 45-minute runtime.
- Treat the older overlapping PR #155/run as a duplicate cross-check rather than another cohort. Do not silently authorize fresh qualification, main/release edits or production promotion.

**Final status:** *safety/contract/budget Gate B green; broad transfer not yet demonstrated — HOLD production V9*.
