# V6e First Fresh Qualification Audit

## Decision context

V6e is a zero-network recovery path for social-profile URLs that are already retained in the exact verified company homepage evidence. It does not fetch social platforms, does not expand website discovery, and does not relax the existing website identity gate.

Qualification run: `36983572529`

Artifact: `v6e-homepage-social-recovery-qualification` (`11217001007`)

Fresh cohort:

- companies: 100
- historical exclusions: 7,720
- overlap: 0
- seed: `20261013`
- cohort SHA-256: `56fe56f9417ede32da1f0df53796ae629b38a88d7a9a4c07522a203a100e8543`

## Aggregate result

- incumbent V5 social-profile companies: 4
- V6e net-new social-profile companies: 1
- combined social-profile companies: 5
- V6e net-new observations: 1
- added logical requests: 0
- added conservative request charge: 0
- third-party API cost: $0
- V6e runtime: 0.017 seconds
- qualification workflow: success

This is a +1 percentage-point absolute social-company coverage gain on the 100-company fresh cohort and a 25% relative increase versus the incumbent social-company count (4 -> 5), at zero added request charge.

## Manual audit of the single candidate

### Entity

- organisation number: `932097567`
- legal name: `SØRØ TAKSERING AS`
- municipality: `BAMBLE`
- BRREG activity: `Takstoppdrag for fast eiendom og malertjenester.`

### Exact website evidence

- source URL: `https://sorotaksering.no/`
- website evidence status: `available`
- website identity status: `exact`
- website identity score: `0.95`
- website identity publishable: `true`
- matched normalized legal-name tokens: `soro`, `taksering`
- identity method: `deterministic_domain_page_identity_guard_v3`
- primary retained page title: `Takstmann Porsgrunn | Sørø Taksering | Verdivurdering Skien`
- primary retained page SHA-256: `de0959358b2b26fe67e1814eb9975ac0c279b2dbd73575bb973ca24fea4d755d`
- canonical website evidence SHA-256: `de0959358b2b26fe67e1814eb9975ac0c279b2dbd73575bb973ca24fea4d755d`

The retained primary homepage identity excerpt explicitly includes `Sørø Taksering As` and a same-domain contact email.

### Retained declaration

The homepage-retained Organization JSON-LD contains:

```json
{
  "@type": "Organization",
  "name": "Sørø Taksering As",
  "url": "https://sorotaksering.no/",
  "sameAs": [
    "https://www.facebook.com/sorotaksering"
  ]
}
```

V6e canonicalizes this to:

`https://facebook.com/sorotaksering`

The existing deterministic social-handle identity gate scored the candidate `0.98`, matched both `soro` and `taksering`, and marked it publishable.

### Incumbent overlap check

The saved V5 profile had no incumbent `profile_handle` observation for this company. Therefore the candidate is genuinely net-new relative to the exact incumbent run on the same cohort.

### Evidence-boundary check

The candidate source URL and SHA-256 exactly match the retained primary company homepage. V6e added no website request and no social-platform request. The claim is limited to the company-declared social-profile URL; it makes no claim about social activity, engagement, sentiment, recency, or account contents.

## Manual audit result

**PASS for candidate correctness and provenance.**

The candidate is strongly supported by exact-company homepage evidence and deterministic name/handle agreement, with no added network acquisition and no widening of the company identity boundary.

## Promotion gate

Do not promote from this single fresh candidate alone. Run V6e unchanged on one additional untouched transfer cohort that excludes this 100-company qualification cohort. If the transfer run preserves the zero-request/$0 boundary and every net-new candidate passes manual audit, promote the minimal recovery module into the production runner. Otherwise keep V6e experimental.
