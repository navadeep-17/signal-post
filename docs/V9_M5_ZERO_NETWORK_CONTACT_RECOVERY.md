# V9 M5 — zero-network secondary contact recovery

Status: **NO-GO / do not integrate into production**

Production V8 remains untouched. This experiment is stacked on the M4 HOLD head and consumed no fresh qualification cohort.

## Hypothesis

The final evaluator can retain one bounded same-domain H1c secondary legal/contact page when a deterministic website candidate needs extra identity corroboration. That retained page carries its own URL, content hash and bounded text. H2c contact-email extraction reads the primary homepage identity excerpt, so M5 tested whether a same-domain email could be recovered from the already-retained secondary page with zero additional production requests.

## M5a offline gate

`src/norway_company_agent/zero_network_contact_recovery.py` requires all of:

1. the existing website is already exact and publishable;
2. `secondary_identity_page` exists;
3. the marker URL/hash exactly matches one retained page;
4. that page remains on the verified company's registered domain;
5. the email passes the existing H2c same-domain email rule;
6. the claim uses the secondary page's own URL/hash;
7. an email already published by H2c is not duplicated.

The recovery itself performs no network access and cannot create website identity.

Focused tests cover exact provenance, wrong-domain email rejection, cross-domain secondary-page rejection, hash mismatch, unpublishable websites, duplicate suppression, placeholder/noreply rejection and missing secondary markers.

## Forced reused-site development screen

Run: `37115532556`

Artifact: `11270713519` (`v9-m5-reused-site-contact-screen`)

Head: `018b48cb785025c861b021076c95588984e2e802`

The screen reused nine already-qualified websites and deliberately fetched the first bounded identity/contact page for each site to measure the theoretical value of secondary-page extraction.

Result:

- 9 reused sites;
- 9 had a candidate secondary identity/contact link;
- 3 companies had a primary-page H2c email;
- 1 company had incremental secondary-page email evidence;
- 2 incremental emails were found for organisation `930833959` (Friluftssykehuset):
  - `maren@friluftssykehuset.no`
  - `ole@friluftssykehuset.no`
- source page: `https://www.friluftssykehuset.no/stiftelsen-friluftssykehuset/kontakt-oss/`;
- page-specific content hash captured;
- recovery network requests added in production: 0;
- third-party API cost: $0.

This proved the extractor can recover real additional evidence, but this screen intentionally forced a secondary-page fetch for every reused site and therefore did **not** prove the actual production prerequisite occurs often enough.

## Production-prerequisite replay

The V7 100-company release qualification had only four websites selected through H1c deterministic-domain discovery. M5 therefore replayed the actual `discover_final_website()` path on those same four frozen company rows rather than forcing a secondary fetch.

Run: `37115777126`

Artifact: `11271615413` (`v9-m5-h1c-contact-replay`)

Replay head: `d58339adb5998b6c962e5c71feeb37cbccd2c037`

Full Baseline CI on that replay head: run `37115780324` — **success**.

Replay result:

- 4 reused H1c-selected profiles;
- 3 currently publishable through H1c directly from homepage evidence;
- 1 current H1c secondary corroboration attempt;
- 0 secondary corroborations verified;
- 0 retained verified secondary identity pages;
- 0 companies eligible for M5 recovery under the actual production prerequisite;
- 0 incremental secondary emails;
- 10 observed logical site requests / 16 ceiling;
- recovery production requests added: 0;
- third-party API cost: $0;
- no fresh cohort consumed.

## Decision

**NO-GO.**

The extraction logic is precise and can recover real same-domain emails when a suitable secondary page is available, but the current production H1c path almost never retains a verified secondary identity page. The measured production-eligible yield is therefore zero on the exact reused H1c-selected cohort.

Do not add this recovery to V8/V9 production solely because it is zero-network. Extra code and fact types still carry maintenance/evidence risk, and the current measured incremental company coverage is zero.

Revisit only if a future website-discovery milestone materially increases the number of exact websites whose publication genuinely depends on retained secondary identity pages.

Final experiment head before PR closure: `299a503045f7571718c3b6747593ce3f6581e8d3`.

Final Baseline CI: run `37115876569` — **success**.
