# Signalpost output contract

Emit one JSON object per input organisation number.

The original auditable envelope remains the source of truth:

```json
{
  "organisation_number": "123456789",
  "run": {
    "run_id": "2026-08-24-a",
    "started_at": "2026-08-24T06:00:00Z",
    "completed_at": "2026-08-24T06:00:08Z",
    "terminal_status": "completed"
  },
  "claims": [
    {
      "field": "official_website",
      "value": "https://example.no/",
      "availability": "available",
      "confidence": 0.99,
      "evidence_ids": ["ev-1"]
    }
  ],
  "evidence": [
    {
      "id": "ev-1",
      "source_url": "https://example.no/",
      "source_class": "company_owned",
      "retrieved_at": "2026-08-24T06:00:04Z",
      "content_sha256": "...",
      "claim_span": "Example AS, organisation number 123 456 789"
    }
  ],
  "changes": [],
  "errors": [],
  "operations": {
    "requests": 4,
    "runtime_ms": 8120,
    "third_party_cost_usd": 0
  }
}
```

Allowed availability states are `available`, `not_available`, `blocked`, `not_applicable`, `ambiguous` and `failed`. A checked source that has zero jobs or zero locations is different from a source that was not checked.

## V2 canonical projection

`scripts/run_signalpost_v2.py` preserves every field above and additionally emits evaluator-facing fields:

- `canonical_facts[]` — flat, typed facts that reuse the evidence IDs of the original source-backed claim;
- `canonical_profile` — the same facts grouped into Builderr-facing data areas: company record, financials, people, locations, company website, jobs and public activity;
- `synthesis` — a deterministic zero-network brief assembled only from already-published canonical facts, refresh `changes[]`, and explicit unknown states.

Example:

```json
{
  "canonical_facts": [
    {
      "type": "person_role",
      "canonical_field": "people.role",
      "source_field": "roles",
      "value": {
        "name": "Example Person",
        "role_code": "DAGL",
        "role": "Daglig leder",
        "inactive": false
      },
      "availability": "available",
      "confidence": 1.0,
      "evidence_ids": ["ev-role"]
    },
    {
      "type": "financial_revenue",
      "canonical_field": "financial.revenue",
      "source_field": "financial.revenue",
      "value": 12500000,
      "currency": "NOK",
      "reporting_period": {
        "fraDato": "2025-01-01",
        "tilDato": "2025-12-31"
      },
      "availability": "available",
      "confidence": 1.0,
      "evidence_ids": ["ev-revenue"]
    }
  ],
  "canonical_profile": {
    "schema_version": "signalpost-canonical-v2",
    "organisation_number": "123456789",
    "company_record": [],
    "financials": [],
    "people": [],
    "locations": [],
    "company_website": [],
    "jobs": [],
    "public_activity": [],
    "data_areas": {
      "company_record": true,
      "financials": true,
      "people_and_locations": true,
      "company_website": false,
      "hiring_and_public_activity": false
    }
  },
  "synthesis": {
    "schema_version": "signalpost-synthesis-v1",
    "organisation_number": "123456789",
    "sections": [
      {
        "key": "financials",
        "title": "Financial snapshot",
        "text": "Latest published revenue: 12,500,000 NOK for period ending 2025-12-31.",
        "evidence_ids": ["ev-revenue"],
        "source_fields": ["financial.revenue"]
      }
    ],
    "what_changed": {
      "text": "No material change is published for this run; this does not imply that nothing changed outside checked sources.",
      "change_count": 0,
      "changes": []
    },
    "unknowns": ["No strict job posting is published."],
    "evidence_ids": ["ev-revenue"],
    "generation": {
      "mode": "deterministic_zero_network",
      "llm_used": false,
      "new_facts_created": false
    }
  }
}
```

The V2 projection and synthesis are deliberately **zero-network and evidence-bounded**. They do not repair missing values, invent facts, relax company-identity gates or replace provenance. `claims[]` and `evidence[]` remain the authoritative source layer. Every canonical fact must point to evidence already present in the same output object, and every positive synthesis statement is built from those canonical facts.

Current canonical namespaces are `company.*`, `financial.*`, `people.*`, `locations.*`, `website.*`, `hiring.*` and `public.*`. A social-profile fact means only that a verified company-owned page declared the profile URL; the social platform itself was not fetched. A generic careers page is never projected as a hiring fact.

The synthesis layer makes three boundaries explicit:

- **what the company does / current snapshot** — only from qualified canonical facts;
- **what changed** — only from validated `changes[]`; an empty list is described as “no material change published for this run,” never “nothing changed”;
- **what remains unknown** — derived from unavailable canonical areas and strict activity abstentions, never converted into negative business facts.
