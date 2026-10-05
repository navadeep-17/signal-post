# Q8 fresh qualification attempt #2 — consumed failure record

Fresh seed `20261105` was consumed by workflow `37347385696` on qualification head `36973bf862b6b48863ce647c3ff1237612dd363a`.

Pre-result lineage gates passed before production results were observed:

- previous touched companies: 8,523 unique;
- fresh cohort: 100 unique, zero overlap;
- seed: `20261105`;
- fresh cohort SHA-256: `68aad9c136df21bd3f197399b75def21aed6871f1efe0de81b63d6e00648bac1`;
- no production-code delta on the qualification branch.

The actual V8 production step completed successfully. The post-run evidence verifier failed on exactly one evaluator-visible provenance row:

- organisation: `885588522` (`HEMSEDAL MØBLER AS`);
- field: `external.company_update`;
- source: `https://www.hemsedalmobler.no/garderobe/`;
- core evidence URL/date/span/hash: present and complete;
- missing evaluator-visible fields: `identity_proof`, `extraction_method`.

Aggregate verifier state before failure:

- available claims: 4,658;
- core-evidence-complete: 4,658 / 4,658;
- reopenable sources: 4,658 / 4,658;
- identity-sensitive claims: 165;
- identity proof visible: 164 / 165;
- extraction method visible: 164 / 165.

Artifact `11362056592`, digest `sha256:8db304a4a91669d42a8cea8c219e43ea7e3d4e549a486b777a7cb248d83ca7fa` preserves the consumed output.

Decision: **NO-GO / consumed**. Do not rerun seed `20261105` as fresh. Repair the first-party detail-page provenance boundary, validate on this consumed cohort, merge + post-merge CI, then construct the next untouched cohort with this 100-company set added to the exclusion.
