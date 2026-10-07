# Signalpost output contract

Emit one JSON object per input organisation number.

The original auditable envelope remains the source of truth:

```json
{
  "organisation_number": "123456789",
  "run": {
    "run_id": "2026-10-01-a",
    "started_at": "2026-10-01T06:00:00Z",
    "completed_at": "2026-10-01T06:00:08Z",
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
      "retrieved_at": "2026-10-01T06:00:04Z",
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

Allowed availability states are `available`, `not_available`, `blocked`, `not_applicable`, `ambiguous` and `failed`. A checked source with no qualifying value is different from a source that was not checked.

## Canonical projection and synthesis

`scripts/run_signalpost_v2.py` preserves every field above and additionally emits evaluator-facing fields:

- `canonical_facts[]` — flat, typed facts that reuse evidence IDs from the original source-backed claims;
- `canonical_profile` — the same facts grouped into company record, financials, people, locations, company website, jobs and public activity;
- `synthesis` — a deterministic evidence-linked brief assembled only from already-published canonical facts, validated refresh changes, qualified official registry-change facts and explicit unknown states.

The canonical schema name remains `signalpost-canonical-v2` for backward compatibility even though the current evaluator path includes the qualified V3–V5 layers.

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
    },
    {
      "type": "registry_change",
      "canonical_field": "company.registry_change",
      "source_field": "official_registry_change",
      "value": {
        "event_date": "2026-09-30",
        "path": "/antallAnsatte",
        "summary": "Brønnøysundregistrene recorded a registered employee-count update."
      },
      "availability": "available",
      "confidence": 1.0,
      "evidence_ids": ["ev-registry-change"]
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
      "text": "Brønnøysundregistrene recorded a qualified registry update for this organisation.",
      "change_count": 0,
      "changes": []
    },
    "unknowns": ["No strict job posting is published."],
    "evidence_ids": ["ev-revenue", "ev-registry-change"],
    "generation": {
      "mode": "deterministic_zero_network",
      "llm_used": false,
      "new_facts_created": false
    }
  }
}
```

## Evidence and identity invariants

Canonical projection and synthesis do not repair missing values, invent facts, relax company-identity gates or replace provenance. `claims[]` and `evidence[]` remain the authoritative source layer.

Every positive canonical fact must point to evidence already present in the same output object. Every positive synthesis statement must be grounded in already-published facts or validated refresh changes.

Current canonical namespaces are `company.*`, `financial.*`, `people.*`, `locations.*`, `website.*`, `hiring.*` and `public.*`.

Important semantic boundaries:

- a social-profile fact means only that an exact verified company-owned page declared the profile URL; the social platform itself was not fetched;
- a verified same-company-host careers page may be projected as `hiring.careers_page`, explicitly scoped to careers/hiring presence only; it never establishes an active vacancy or job posting;
- an official BRREG registry-change fact means BRREG recorded a dated exact-org update; it is not company-authored news, hiring or social activity;
- missing values, blocked sources and ambiguous identity evidence remain explicit rather than being converted into negative business claims.

## Change semantics

Signalpost has two distinct change channels:

1. `changes[]` contains validated refresh diffs when the system can establish old and new material values from comparable snapshots.
2. `official_registry_change` claims / `company.registry_change` canonical facts contain dated exact-org BRREG update events when BRREG provides a qualified current patch event. These facts do **not** invent an earlier value that the source did not provide.

The synthesis `what_changed` section may use either channel, but must preserve the distinction. If neither channel contains a qualified event, it says that no material change was **published for the run** rather than claiming that nothing changed in reality.
