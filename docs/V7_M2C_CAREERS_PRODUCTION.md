# V7 M2C — verified homepage careers signals

## Purpose

Builderr's official diagnostic explicitly cited company-owned careers pages as missed hiring signals. M2C publishes a narrow hiring-presence fact from an exact-verified company homepage without claiming that a specific vacancy is open.

## Production boundary

- The company website must already pass the existing exact-company publication gate.
- Careers discovery happens while the already-budgeted homepage HTML is in memory.
- Only explicit same-registered-domain careers/hiring links are retained.
- External ATS/job-board URLs are not represented as company-owned careers pages.
- No careers URL is fetched by M2C.
- The claim type is `external.careers_page`; it is never `external.job_posting`.
- Canonical fact: `hiring.careers_page`.
- Synthesis says hiring presence is known while explicitly stating when no specific active job is independently verified.
- Incremental network requests: 0.
- Third-party API cost: $0.

## Evidence

The evidence is the exact verified homepage that declared the careers link, including its retrieval timestamp, content hash and bounded link text. Website discovery provenance may be registry-linked, deterministic-domain discovery, or another already-qualified production route; the M2C invariant is that the evidence homepage and the careers URL resolve to the same registered domain after the website itself has already passed the exact-company publication gate.

## Qualification

The discovery rule first transferred on a genuinely unseen 100-company cohort after excluding 7,920 previously touched organisations:

- frozen transfer manifest SHA-256: `1d50c3eddb91004c6413ffd263e25b166b9ec822cceae9c9bb8c0908edd997b3`;
- exact verified websites eligible: 10;
- companies with careers signals: 2;
- careers links: 2;
- wrong-company publications: 0;
- third-party API cost: $0.

The experiment had to re-fetch ten homepages and therefore added 20 logical requests / 40 conservative charge. Production removes that re-fetch and extracts the same links while the already-budgeted homepage HTML is in memory.

The integrated production implementation was then replayed on the exact frozen transfer 100. The production run completed successfully and reproduced both expected signals:

- `982897327` — Lucerna → `https://www.lucerna.no/karriere`;
- `936618200` — BK Ventilasjon → `https://bkventilasjon.no/karriere/`;
- 2 `external.careers_page` claims and 2 `hiring.careers_page` canonical facts;
- 0 careers claims represented as `external.job_posting`;
- deterministic synthesis explicitly states that a careers surface is known while no specific active job is independently verified;
- observed conservative production charge: 1,392 / 2,000;
- third-party API cost: $0;
- contract/canonical/synthesis production run: passed.

Integrated production artifact:

- workflow run: `37096473516`;
- artifact: `v7-m2c-production-qualification`;
- artifact digest: `sha256:8cdd9ed59fea48c9a9d5821edcbe87dd06760755f7f39eb6ec33d9fff4f05a67`.

A follow-up artifact verifier corrected an overly narrow test assumption about website `source_class`. The invariant is same exact-verified registered domain, not a specific discovery-source label. Corrected verification workflow `37097186345` passed.

## Decision

**GO for production promotion.** M2C adds a Builderr-requested hiring-presence fact with no new production request class, keeps concrete vacancies semantically separate, preserves the existing exact-company gate, and reproduced the same two unseen-transfer signals in the integrated production output.
