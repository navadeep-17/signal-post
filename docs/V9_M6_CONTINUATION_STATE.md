# Signalpost V9 M6 Continuation State

Last updated: 2026-10-07

## Decision

**SHELVE** M6 structured dated first-party activity.

Qualified measured implementation head:
`b01eefd201c439f76fc25da4ddfd81a57dcc561b`.

M6 is not promoted into the next V9 lineage. Production `main`, V8 qualified/submission refs,
the promoted M2+M4 lineage, and promoted M5 behavior remain untouched.

## Exact-head qualification

- Baseline CI run `37512933250`: **PASS**
- consumed-transfer run `37512929936`: **PASS**
- consumed-transfer artifact: `11437162970`
- artifact digest:
  `sha256:2eef40b02a85079ba6ae55724754dea55b7a6653826e071d0c6766325f215215`
- fresh companies used: **0**
- search API requests: **0**
- third-party API cost: **$0**

The transfer compared the same consumed 100 exact-site companies against promoted M5
`dc5907b27fb8844b0f690a166937bf908f058a73`.

## Measured result

Consumed exact-site population available: **107**. The deterministic transfer target used **100**.

- dated first-party activity companies: **8 -> 8**
- net-new dated-activity companies: **0**
- lost dated-activity companies: **0**
- new activity publications: **0**
- lost activity publications: **0**
- non-activity family changes: **none**
- observed conservative request charge: **1892 -> 1892**
- theoretical conservative request ceiling: **2000 -> 2000**
- wall runtime: **653.211 s -> 665.917 s**
- contract/canonical/synthesis/evidence structural gates: **PASS**
- manual precision audit rows: **0**, because no new external publication was produced
- wrong-company new publications: **0**, because no new external publication was produced

Machine decision: `SHELVE_NO_NET_NEW_YIELD`.

## What was tested

M6 tested two budget-neutral/strict dated-activity improvements:

1. exact verified homepages may nominate explicit same-site RSS/Atom alternates, substituted into
   the already-existing bounded feed slot rather than adding requests;
2. page-local structured `NewsArticle`, `Article`, and `BlogPosting` `datePublished`
   metadata is retained for strict same-page activity evidence.

The experiment also hardened evidence bookkeeping so dated-activity evidence keeps page-local
retrieval provenance and the exact date-extraction method.

No sitemap/index timestamp is accepted as a publication date, future publication dates are
rejected, and one page hash may not support another page's fact.

## Why SHELVE

M6 is precise and budget-neutral on the measured consumed transfer, but it produced **zero**
net-new scored-family company coverage. Under the V9 promotion framework, clean implementation
alone is insufficient; positive measured family lift is required.

Therefore do not carry M6 production behavior forward unchanged.

## Next milestone

The exact next milestone is **M7 secondary deterministic candidate sources**, starting from the
promoted M5 base, not from M6.

M7 remains nomination-only. Any registered-subunit/NAV/Wikidata/legal-name-DNS candidate must be
independently fetched and pass the unchanged exact-company verifier before publication. Fresh
qualification remains locked.
