# V4 keyed official-source access gate

Date: 2026-10-01

This document records the credential boundary for the remaining Milestone 2 source screens. It intentionally separates **officially verified access facts** from unverified endpoint assumptions.

## Patentstyret (Norwegian Industrial Property Office)

Official developer material reviewed on 2026-10-01 states:

- the patent/trademark/design Open Data dataset is available in JSON;
- usage is free, with source attribution/copyright guidance;
- the dataset follows NLOD 2.0;
- many Norwegian businesses can be uniquely linked to rights by national organisation number;
- `/register/v1/IprCasesByCompany` is the recommended company-portfolio endpoint before retrieving domain-specific case details;
- API endpoints require a valid subscription key;
- creating an account and subscribing to a product is self-service.

Official references:

- `https://developer.patentstyret.no/`
- `https://developer.patentstyret.no/docs-open-data`
- `https://developer.patentstyret.no/docs-get-access`

### Signalpost status

**High-value candidate, access-gated.**

The repository now contains a credential-gated exact-org screen, but we deliberately do not guess the query-parameter shape from the endpoint name. After subscription, use the exact GET operation URL documented by Patentstyret and replace the organisation-number value with `{organisation_number}` when dispatching the workflow.

Required repository secret:

`PATENTSTYRET_API_KEY`

No production connector is allowed until the screen shows useful reach and matched responses are schema-audited for the exact company role (owner/applicant/right holder as appropriate).

## Doffin

Official Doffin material reviewed on 2026-10-01 states:

- Doffin is the Norwegian public procurement notice database;
- Doffin's publication/distribution flow includes an API and Doffindata;
- the DFØ developer portal exposes a `Public API` described as an API for searching for and downloading published notices;
- access to the API platform requires sign-up and a subscription/token.

Official references:

- `https://doffin.anskaffelser.no/`
- `https://doffin.anskaffelser.no/info`
- `https://dof-notices-dev-api.developer.azure-api.net/`
- `https://dof-notices-dev-api.developer.azure-api.net/apis`

### Signalpost status

**Potentially valuable, access-gated and role-sensitive.**

A target organisation number occurring in a procurement response is not enough to publish a supplier/award fact: it could identify a buyer, supplier, participant or another organisation. The first keyed screen therefore measures only exact-org response reach. If reach is useful, the next step is a source-specific parser that validates the organisation's role inside result/award notices.

Required repository secret:

`DOFFIN_API_KEY`

The exact public search/download operation URL and query shape must be copied from the authenticated official portal before dispatching the screen. Do not promote an endpoint inferred only from third-party client code.

## Reproducible screen tooling

Manual workflow:

`.github/workflows/v4-keyed-source-screen.yml`

Pure screen implementation:

`scripts/screen_keyed_exact_org_source.py`

Safety properties:

1. endpoint must be HTTPS;
2. endpoint template must contain `{organisation_number}`;
3. API key is read from an environment variable and sent only in the configured request header;
4. API key is never written to reports/artifacts;
5. exact nine-digit identifier matching uses numeric boundaries and accepts compact or 3-3-3 formatting;
6. raw official responses are archived by hash for audit;
7. the screen never emits production claims;
8. a source still needs schema/role validation before promotion.

The fixed comparison cohort is the same 20-company V4 source-screen set (seed `20261006`, zero overlap after 7,200 prior companies). Reusing the same cohort for source triage makes source reach directly comparable; it is not treated as a future untouched qualification holdout.

## Dispatch checklist

For each source:

1. create the official API account/subscription;
2. add the key to GitHub Actions using the secret name above;
3. confirm the exact GET operation URL in the official portal;
4. replace the concrete organisation-number value with `{organisation_number}`;
5. manually dispatch `V4 Keyed Official Source Screen`;
6. audit every matched response for source schema and company role;
7. only then decide BUILD / HARDEN / DROP.

Until those credentials exist, engineering should continue on milestones that do not depend on external account setup rather than weakening the source screen or scraping authenticated interfaces.
