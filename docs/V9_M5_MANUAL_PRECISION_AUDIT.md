# V9 M5 Manual Precision Audit

Qualified head: `9165c2c9e02ab06010fb615fc1406fb0fac640b1`  
Replay run: `37506125575`  
Artifact: `11432295633`  
Artifact digest: `sha256:544af758c0d0a461981b9aa4bb5ef520e2eeaec78a4e0bbe7cc092e938b6da18`

Scope: **100% of new M5 hiring-intent publications**.

Result: **1/1 reviewed, 1/1 accepted, 0 wrong-company, 0 semantic overclaim.**

## ENTALPY AS — organisation 927097532

Published field: `external.hiring_intent`  
Source: `https://entalpy.no/`  
Content hash:
`93a79060f7be5743eee904890ea9accb37bd62aff587cd59f777788672232a12`

### Exact-company identity

Accepted.

The retained identity assessment is exact, score **1.0**, publishable, under
`deterministic_domain_page_identity_guard_v3`. The page explicitly exposes organisation number
`927097532`, and the legal-name token `entalpy` is matched.

### Recruitment-language evidence

Accepted.

The retained first-party homepage text contains explicit recruitment language:

`Vi søker etter talentfulle kuldeteknikere og mekanikere`

The same bounded span continues with administrative/logistics personnel and experience in
production planning or leadership. This satisfies the M5 people/role-context requirement for the
broad `vi søker` phrase.

### Semantic boundary

Accepted only as **company-authored hiring intent**.

The claim scope states that the evidence is not proof that any particular vacancy is currently
open. M5 does not synthesize a job title, application action, job-detail page, or
`external.job_posting` claim from this evidence.

### Evidence integrity

- page-local source URL: present
- retrieval timestamp: present
- 64-character content SHA-256: present
- exact-company identity proof: present
- bounded claim span: present
- extraction method: `explicit_company_authored_recruitment_language:no_vi_soker`
- incremental network requests: **0**

## Final result

Manual M5 precision gate: **PASS**.
