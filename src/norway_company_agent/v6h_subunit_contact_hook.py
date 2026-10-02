from __future__ import annotations

from typing import Any, Callable


def install_subunit_contact_hint_hook() -> Callable[[Any], dict[str, Any]]:
    """Retain website/email fields already present in the fetched BRREG subunit payload.

    This experiment hook adds no network requests and does not publish any website. The
    retained values are nomination hints only; publication still requires an independently
    fetched page to pass the exact-parent-company identity gate.
    """
    from . import official

    original = official.normalize_locations
    if getattr(original, "_signalpost_v6h_hook", False):
        return original

    def wrapped(body: Any) -> dict[str, Any]:
        normalized = original(body)
        raw_rows = (((body or {}).get("_embedded") or {}).get("underenheter") or []) if isinstance(body, dict) else []
        by_org = {
            str(item.get("organisasjonsnummer") or ""): item
            for item in raw_rows
            if isinstance(item, dict) and item.get("organisasjonsnummer")
        }
        for row in normalized.get("locations") or []:
            if not isinstance(row, dict):
                continue
            raw = by_org.get(str(row.get("organisation_number") or "")) or {}
            website = str(raw.get("hjemmeside") or "").strip()
            email = str(raw.get("epostadresse") or "").strip()
            if website:
                row["website_hint"] = website
            if email:
                row["email_hint"] = email
        return normalized

    wrapped._signalpost_v6h_hook = True  # type: ignore[attr-defined]
    official.normalize_locations = wrapped
    return original
