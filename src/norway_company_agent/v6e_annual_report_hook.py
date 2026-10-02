from __future__ import annotations

from typing import Any, Callable

from .annual_report_domain_discovery import extract_annual_report_domain_candidates


def install_annual_report_candidate_hook() -> Callable[..., Any]:
    """Attach website candidate hints while V5 already processes annual-report text.

    This is an experiment-only hook. It does not fetch anything, does not create evidence,
    and leaves the production annual-report description/workforce return value unchanged.
    """
    from . import annual_report_workforce as workforce

    original = workforce.build_annual_report_description_observation
    if getattr(original, "_signalpost_v6e_hook", False):
        return original

    def wrapped(profile: dict[str, Any], *, text: str, **kwargs: Any):
        candidates = extract_annual_report_domain_candidates(profile, text, max_candidates=3)
        if candidates:
            profile["annual_report_website_candidates"] = candidates
            profile["annual_report_website_candidate_source"] = {
                "source_url": kwargs.get("source_url"),
                "content_sha256": kwargs.get("content_sha256"),
                "effective_at": kwargs.get("effective_at"),
                "candidate_count": len(candidates),
                "publication_authority": False,
            }
        return original(profile, text=text, **kwargs)

    wrapped._signalpost_v6e_hook = True  # type: ignore[attr-defined]
    workforce.build_annual_report_description_observation = wrapped
    return original
