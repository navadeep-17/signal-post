# V10 M21 — Norid organisation-to-domain rights screen

Reviewed: 2026-10-08  
Status: **TECHNICAL FIT / RIGHTS NO-GO / NO LOOKUPS EXECUTED**  
Scope: research only; does not amend any Signalpost production collector.

## Why this was investigated

The read-only 300-company audit found 259 without a qualified official website. Norway's `.no` registry, Norid, appears to have a much stronger identity anchor than name-derived hostname guesses: the registered subscriber organisation number. We evaluated the *documentation and published terms only*, not domain lookup responses.

## Official-source findings

1. The public domain registration directory service supports two kinds of queries: domain name, and organisation number → overview of domains registered to the organisation. It explicitly restricts request frequency. Source: https://www.norid.no/en/domeneoppslag/personvern/domeneoppslag/ (published May 2018, updated March 2025).
2. Norid's domain-directory terms state that **all commercial use** of lookup data is forbidden. They also prohibit copying/downloading/storing all or substantial parts of the data and constrain permitted purposes to domain technical issues, responsible-party contact, rights protection and prevention of illegal content. This is not a general-purpose company-intelligence enrichment licence. Source: https://www.norid.no/en/domeneoppslag/vilkar/ (updated April 2025; Norwegian master text prevails).
3. Norid's own FAQ explicitly says that it **does not permit bulk downloading** of data from the domain lookup database. Source: https://www.norid.no/en/oss/.
4. The technical RDAP service provides a REST API, but public/anonymous search is limited to nameserver search. Org-number-based domain searches such as `/domains?identity=<orgnr>` are an **authenticated registrar** feature whose results are scoped to that registrar's sponsored objects, not a public open enumeration API. Source: https://teknisk.norid.no/en/integrere-mot-norid/rdap-tjenesten/.
5. Norid's September 2025 registrar-access change reiterates that registrar access is for serving the registrar's own customers; it cannot be presumed to grant whole-registry company research rights. Source: https://teknisk.norid.no/en/registrar/nytt/begrenset-innsyn-i-kundedata/.

## Decision

**NO-GO for Signalpost's current source policy.** Do not scrape the public lookup UI, automate organisation-number lookups, use proxy rotation, assume registrar credentials solve rights, or republish lookup responses. No Norid sample queries or domain data were collected in this screen. Norid must not enter the evaluator path on the basis of technical availability alone.

A future reconsideration requires explicit written terms/permission covering programmatic organisation-number lookup and the intended company-intelligence use, reproducible access and cost, documented data handling, and the existing exact-company/publication and request-budget qualification gates. Even an explicitly permitted registration result would nominate a domain only: it does not prove that an active company website represents the exact target legal entity.

This is a policy/engineering screen based on the cited public documents, not a formal legal opinion. No production/fresh-cohort changes occurred.
