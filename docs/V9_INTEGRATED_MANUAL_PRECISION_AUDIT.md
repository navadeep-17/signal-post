# V9 Integrated Manual Precision Audit

Run: `37496552710`  
Exact challenger head: `ce0efaf7a2abba82b66726111ed488bf5185fa3a`  
Artifact: `11429661159`  
Artifact digest: `sha256:a39d110a13edc21935c3c1e19613f5407cc1c012e4c40f209b0dba868e882977`

Scope: **100% of new evaluator-family publications** in the exact-head integrated consumed gate.

Result: **8/8 reviewed, 8/8 accepted, 0 wrong-company publications, 0 material page-scope ambiguities.**

## 1–2. VOLF AS — organisation 979943377

Source: `https://volf.no/`  
Retained content hash:
`083de1273a66bcf99be8faec8c028caebd6f789f2922e4af7ce628ce9dcb7ef4`

Website identity is exact at 0.95 under `deterministic_name_org_evidence_v4`.

### external.contact_email = post@volf.no

Accepted.

- source is the already-retained exact company homepage;
- email is explicitly present in schema.org Organization;
- email registered domain is exactly `volf.no`;
- the individual structured Organization node contains exact organisation number `979943377`;
- evidence has source URL, retrieval timestamp and content hash;
- no network request was added by the M4 projection.

### external.contact_phone = +4770275662

Accepted.

- source is the same exact company homepage;
- telephone is explicitly present in schema.org Organization;
- the structured node contains exact organisation number `979943377`;
- value passes the conservative Norwegian phone normalization;
- evidence is page-local, hashed and timestamped;
- zero additional network requests.

## 3–8. DEN GLADE GRIS AS — organisation 999096298

Source: `https://www.dengladegris.no/`  
Retained content hash:
`a9d8388c0b1eee0547f2800964a98fbc3835deaea584c18eabd1998bdda12889`

Website identity is exact at 0.98 under `final_h1c_secondary_identity_guard_v1`.
All normalized legal-name tokens — `den`, `glade`, `gris` — are present together and the
site has same-domain secondary identity corroboration.

### official_website = https://www.dengladegris.no/

Accepted. Exact-company identity gate is publishable at 0.98 with full legal-name token match and
secondary identity corroboration.

### external.careers_page = /ledige-stillinger

Accepted strictly as a **careers surface**.

The exact company homepage explicitly links to the same-host `Ledige stillinger` page. This
publication does **not** assert company-authored hiring intent and does **not** assert a specific
active vacancy.

### external.profile_handle = Facebook

Accepted.

The exact company homepage explicitly declares
`https://facebook.com/dengladegrisen`; the social-platform page itself was not fetched. The
handle passes the deterministic legal-name token identity gate.

### external.profile_handle = Instagram

Accepted under the same bounded homepage-declaration rule for
`https://instagram.com/dengladegris`.

### external.contact_email = booking@dengladegris.no

Accepted.

The email is explicitly present in bounded company-page contact/footer evidence and its domain is
exactly the verified website registered domain `dengladegris.no`.

### external.contact_phone = +4722111710

Accepted.

The telephone is explicitly present in the retained schema.org Organization node. The individual
structured node independently matches the legal name `Den Glade Gris`; evidence is page-local,
hashed and timestamped.

## Final audit decision

- new external publications: **8**
- accepted: **8**
- rejected: **0**
- wrong-company: **0**
- ambiguous structured-node: **0**
- material page-scope ambiguity: **0**
- lost external publications: **0**
- lost verified websites: **0**
- lost contact publications: **0**

Manual precision gate: **PASS**.
