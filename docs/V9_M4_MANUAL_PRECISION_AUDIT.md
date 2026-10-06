# V9 M4 Manual Precision Audit

Audited: 2026-10-06  
Branch: `experiment/v9-structured-contact-recovery`  
Exact tested head: `64eb9b66046f36a1c089b96e865f9bfdb3d9d425`  
Consumed replay: GitHub Actions `37463696625`  
Artifact: `11413326913`  
Artifact digest: `sha256:c6b240439a0144b0860c251da13a721e0c8fd658077782e0bddafd6c6a40ad6c`

## Audit method

All 26 net-new publications were reviewed against the **frozen retained exact-site snapshot** used by the replay, not against a later live page.

For each publication the review checked:

1. the retained website identity assessment is publishable;
2. the structured Organization/LocalBusiness node corresponds to the target legal entity by target legal-name identity or exact organisation-number identity;
3. the published email/phone value is explicitly present inside that target structured node;
4. no different structured organisation number is being used as target identity;
5. email values remain on the verified website registered domain;
6. phone values are conservative Norwegian `+47XXXXXXXX` normalization of an explicit `telephone` field.

## Reviewed publications

| Org.nr | Legal entity | Frozen exact site | Structured node identity | Explicit structured publications | Result |
|---|---|---|---|---|---|
| 835095002 | GB TRANSPORT AS | https://www.gbtransport.no/ | GB Transport AS | phone +4790808961 | PASS |
| 915338275 | LEAN TECH AS | https://www.leantech.no/ | Lean Tech / Lean Tech AS | email sissel@leantech.no; phone +4748123070 | PASS |
| 916161530 | GOD RYGG AS | https://www.god-rygg.no/ | God Rygg Kiropraktikk; target core legal-name tokens | phone +4748146864 | PASS |
| 922899355 | STENE TAKST AS | https://stenetakst.no/ | Stene Takst AS | phone +4792855155 | PASS |
| 927097532 | ENTALPY AS | https://entalpy.no/ | Entalpy AS | email frank@entalpy.no; phone +4790564983 | PASS |
| 927209284 | ALT-MULIG-MANN AS | https://www.alt-mulig-mann.no/ | Alt-Mulig-Mann AS | phone +4741225917 | PASS |
| 927336359 | GS BYGG AS | https://gsbyggskien.no/ | legalName Gs Bygg AS + exact VAT/org 927336359 | phone +4747740449 | PASS |
| 928832562 | TØLLEFSENHJØRNET AS | https://www.tollefsenhjornet.no/ | legalName Tøllefsenhjørnet; target core legal-name token | email post@tollefsenhjornet.no | PASS |
| 929668014 | TOTAL TJENESTE AS | https://www.totaltjeneste.no/ | TOTAL TJENESTE AS | phone +4795022244 | PASS |
| 930155500 | KINGS BAY AS | https://kingsbay.no/ | Kings Bay AS | email booking@kingsbay.no; phone +4779027200 | PASS |
| 931002279 | ENFY AS | https://www.enfy.no/ | legalName Enfy AS + exact identifier 931002279 | phone +4790607646 | PASS |
| 931759418 | FOLLO MALEREN AS | https://follomaleren.no/ | Follo Maleren AS + exact VAT/org 931759418 | phone +4746802535 | PASS |
| 936711219 | BRIM FJORDSAUNA AS | https://brimfjordsauna.no/ | BRIM FJORDSAUNA AS + exact VAT/org 936711219 | phone +4747845703 | PASS |
| 960132734 | VEKST REVISJON AS | https://vekst-revisjon.no/ | Vekst Revisjon AS | phone +4723383838 | PASS |
| 976160975 | SLITASJETEKNIKK AS | https://www.slitasjeteknikk.no/ | Slitasjeteknikk AS | email thomas@slitasjeteknikk.no; phone +4775167700 | PASS |
| 980152634 | TRUCKTECH AS | https://trucktech.no/ | Trucktech AS | email post@trucktech.no; phone +4769304850 | PASS |
| 985095841 | MARITIM DIESEL AS | https://maritimdiesel.no/ | Maritim Diesel AS | phone +4755302580 | PASS |
| 987530707 | EFFEKT REVISJON AS | https://effektrevisjon.no/ | Effekt Revisjon AS | phone +4770190100 | PASS |
| 987934239 | PROZO NORGE AS | https://www.prozo.no/ | Prozo Norge AS | email post@prozo.no; phone +4769153900 | PASS |
| 990794944 | REMTECH NORDIC AS | https://www.remtech.no/ | Remtech Nordic AS | phone +4792260520 | PASS |

## Result

- net-new claims reviewed: **26 / 26**
- companies represented: **20**
- wrong-company publications: **0**
- ambiguous structured-node publications: **0**
- existing contact publications lost: **0**
- non-contact claims changed: **0**
- network requests added: **0**
- contract/canonical/synthesis errors: **0**
- net-new contact-email companies: **5**
- net-new contact-phone companies: **19**
- net-new companies in the any-external-contact union: **7**

Decision: **PROMOTE M4 into the later integrated V9 candidate.**

This does **not** authorize merging this standalone experiment into V8/main. It authorizes the narrow M4 behavior for the integrated V9 branch after the other consumed-transfer milestones pass.
