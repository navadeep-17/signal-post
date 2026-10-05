from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from .discovery import BLOCKED_DISCOVERY_HOSTS
from .website import _registered_domain, normalize_homepage

OPENAI_RESPONSES_ENDPOINT = "https://api.openai.com/v1/responses"
DEFAULT_WEB_SEARCH_MODEL = "gpt-6-luna"
DEFAULT_SEARCH_CONTEXT_SIZE = "low"
MAX_WEB_SEARCH_TOOL_CALLS = 1
USER_AGENT = "builderr-signalpost-q3-experiment/0.1 (+https://builderr.ai)"


def _company_prompt(profile: dict[str, Any]) -> str:
    name = " ".join(str(profile.get("name") or "").split())
    org = "".join(character for character in str(profile.get("organisation_number") or "") if character.isdigit())
    municipality = " ".join(str(profile.get("municipality") or "").split())
    if not name or len(org) != 9:
        raise ValueError("Model website discovery requires a legal name and 9-digit organisation number")
    location = f" Municipality: {municipality}." if municipality else ""
    return (
        "Find likely first-party website URLs for this exact Norwegian legal entity. "
        f"Legal name: {name}. Organisation number: {org}.{location} "
        "Use web search. Prefer the legal entity's own homepage, contact, or about page. "
        "A branded store/dealer/profile page may be nominated, but never assume a parent, chain, franchise, "
        "directory, social profile, or namesake belongs to this legal entity. "
        "Return no more than three likely first-party URLs. These URLs are nominations only and will be "
        "independently fetched and verified before publication."
    )


def _citation_urls(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    """Extract transient URL nominations from a Responses payload.

    Model text, titles, search actions, and citation ordering are not identity evidence.
    The caller may inspect the returned transient text for debugging, but must never
    persist it as company evidence.
    """

    results: list[dict[str, Any]] = []
    texts: list[str] = []
    seen_urls: set[str] = set()
    rank = 0

    def add_url(url: Any, title: Any = "") -> None:
        nonlocal rank
        value = str(url or "").strip()
        if not value or value in seen_urls:
            return
        seen_urls.add(value)
        rank += 1
        results.append(
            {
                "url": value,
                "title": str(title or ""),
                "rank": rank,
                "provider": "openai_responses_web_search",
            }
        )

    for item in payload.get("output") or []:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "web_search_call":
            action = item.get("action") or {}
            for source in action.get("sources") or []:
                if isinstance(source, dict) and source.get("type") == "url":
                    add_url(source.get("url"))
            continue
        if item.get("type") != "message":
            continue
        for content in item.get("content") or []:
            if not isinstance(content, dict) or content.get("type") != "output_text":
                continue
            text = str(content.get("text") or "")
            if text:
                texts.append(text)
            for annotation in content.get("annotations") or []:
                if not isinstance(annotation, dict) or annotation.get("type") != "url_citation":
                    continue
                add_url(annotation.get("url"), annotation.get("title"))

    return results, "\n".join(texts)


def choose_model_url_candidates(results: list[dict[str, Any]], *, limit: int = 2) -> list[dict[str, Any]]:
    """Filter model citations into untrusted, domain-deduplicated crawl nominations."""

    if limit < 1:
        raise ValueError("limit must be positive")

    selected: list[dict[str, Any]] = []
    seen_domains: set[str] = set()
    for item in sorted(results, key=lambda value: (int(value.get("rank") or 10_000), str(value.get("url") or ""))):
        normalized = normalize_homepage(item.get("url"))
        if not normalized:
            continue
        host = (urllib.parse.urlparse(normalized).hostname or "").casefold().removeprefix("www.")
        if any(host == blocked or host.endswith("." + blocked) for blocked in BLOCKED_DISCOVERY_HOSTS):
            continue
        domain = (_registered_domain(normalized) or host).casefold()
        if not domain or domain in seen_domains:
            continue
        seen_domains.add(domain)
        selected.append(
            {
                "url": normalized,
                "host": host,
                "rank": item.get("rank"),
                "provider": item.get("provider") or "model_web_search",
                "method": "untrusted_model_url_nomination_v2",
            }
        )
        if len(selected) >= limit:
            break
    return selected


def openai_web_search_candidates(
    profile: dict[str, Any],
    api_key: str,
    *,
    model: str = DEFAULT_WEB_SEARCH_MODEL,
    timeout: float = 15.0,
    max_candidates: int = 5,
    search_context_size: str = DEFAULT_SEARCH_CONTEXT_SIZE,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Use one OpenAI hosted web-search call only to nominate URLs for later verification."""

    if not api_key.strip():
        raise ValueError("OpenAI web-search provider requires an API key")
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    if max_candidates < 1:
        raise ValueError("max_candidates must be positive")
    if search_context_size not in {"low", "medium", "high"}:
        raise ValueError("search_context_size must be low, medium, or high")

    prompt = _company_prompt(profile)
    body = json.dumps(
        {
            "model": model,
            "tools": [{"type": "web_search", "search_context_size": search_context_size}],
            "tool_choice": "required",
            "max_tool_calls": MAX_WEB_SEARCH_TOOL_CALLS,
            "input": prompt,
            "max_output_tokens": 180,
            "store": False,
        },
        separators=(",", ":"),
    ).encode("utf-8")
    request = urllib.request.Request(
        OPENAI_RESPONSES_ENDPOINT,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    started = time.monotonic()
    prompt_sha256 = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            status = int(response.status)
        elapsed_ms = int((time.monotonic() - started) * 1000)
        payload = json.loads(raw)
        results, transient_text = _citation_urls(payload)
        tool_calls = sum(
            1
            for item in payload.get("output") or []
            if isinstance(item, dict) and item.get("type") == "web_search_call"
        )
        if tool_calls > MAX_WEB_SEARCH_TOOL_CALLS:
            raise RuntimeError(
                f"OpenAI response exceeded web-search call ceiling: {tool_calls}>{MAX_WEB_SEARCH_TOOL_CALLS}"
            )
        usage = payload.get("usage") or {}
        return results[:max_candidates], {
            "status": status,
            "latency_ms": elapsed_ms,
            "bytes": len(raw),
            "prompt_sha256": prompt_sha256,
            "provider": "openai_responses_web_search",
            "model": model,
            "search_context_size": search_context_size,
            "web_search_tool_calls": tool_calls,
            "max_web_search_tool_calls": MAX_WEB_SEARCH_TOOL_CALLS,
            "web_search_required": True,
            "input_tokens": int(usage.get("input_tokens") or 0),
            "output_tokens": int(usage.get("output_tokens") or 0),
            "transient_response_text_present": bool(transient_text),
            "raw_response_persisted": False,
        }
    except RuntimeError:
        raise
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
        return [], {
            "status": int(getattr(exc, "code", 0) or 0),
            "latency_ms": int((time.monotonic() - started) * 1000),
            "bytes": 0,
            "prompt_sha256": prompt_sha256,
            "provider": "openai_responses_web_search",
            "model": model,
            "search_context_size": search_context_size,
            "web_search_tool_calls": 0,
            "max_web_search_tool_calls": MAX_WEB_SEARCH_TOOL_CALLS,
            "web_search_required": True,
            "input_tokens": 0,
            "output_tokens": 0,
            "transient_response_text_present": False,
            "raw_response_persisted": False,
            "error": type(exc).__name__,
        }
