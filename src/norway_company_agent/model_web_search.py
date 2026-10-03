from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.request
from typing import Any

OPENAI_RESPONSES_ENDPOINT = "https://api.openai.com/v1/responses"
DEFAULT_WEB_SEARCH_MODEL = "gpt-6-luna"
USER_AGENT = "builderr-signalpost-v9-experiment/0.1 (+https://builderr.ai)"


def _company_prompt(profile: dict[str, Any]) -> str:
    name = " ".join(str(profile.get("name") or "").split())
    org = "".join(character for character in str(profile.get("organisation_number") or "") if character.isdigit())
    municipality = " ".join(str(profile.get("municipality") or "").split())
    if not name or len(org) != 9:
        raise ValueError("Model website discovery requires a legal name and 9-digit organisation number")
    location = f" Municipality: {municipality}." if municipality else ""
    return (
        "Find the likely official company-owned website for this exact Norwegian legal entity. "
        f"Legal name: {name}. Organisation number: {org}.{location} "
        "Use web search. Prefer the legal entity's own homepage/contact/about pages. "
        "Do not treat business directories, social networks, parent-company pages or namesakes as the answer. "
        "Give at most three likely official website URLs and keep the response brief."
    )


def _citation_urls(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    """Extract only URL citations plus transient assistant text from a Responses payload.

    The returned text exists only so an experimental caller can inspect provider behavior.
    Production evidence must never persist it or use it to prove company identity.
    """
    results: list[dict[str, Any]] = []
    texts: list[str] = []
    rank = 0
    seen_urls: set[str] = set()
    for item in payload.get("output") or []:
        if not isinstance(item, dict) or item.get("type") != "message":
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
                url = str(annotation.get("url") or "").strip()
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                rank += 1
                results.append(
                    {
                        "url": url,
                        "title": str(annotation.get("title") or ""),
                        "rank": rank,
                        "provider": "openai_responses_web_search",
                    }
                )
    return results, "\n".join(texts)


def openai_web_search_candidates(
    profile: dict[str, Any],
    api_key: str,
    *,
    model: str = DEFAULT_WEB_SEARCH_MODEL,
    timeout: float = 15.0,
    max_candidates: int = 5,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Use model web search only to nominate URLs for later independent verification."""
    if not api_key.strip():
        raise ValueError("OpenAI web-search provider requires an API key")
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    if max_candidates < 1:
        raise ValueError("max_candidates must be positive")

    prompt = _company_prompt(profile)
    body = json.dumps(
        {
            "model": model,
            "tools": [{"type": "web_search"}],
            "input": prompt,
            "max_output_tokens": 220,
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
            if isinstance(item, dict) and item.get("type") in {"web_search_call", "web_search"}
        )
        usage = payload.get("usage") or {}
        return results[:max_candidates], {
            "status": status,
            "latency_ms": elapsed_ms,
            "bytes": len(raw),
            "prompt_sha256": prompt_sha256,
            "provider": "openai_responses_web_search",
            "model": model,
            "web_search_tool_calls": tool_calls,
            "input_tokens": int(usage.get("input_tokens") or 0),
            "output_tokens": int(usage.get("output_tokens") or 0),
            "transient_response_text_present": bool(transient_text),
            "raw_response_persisted": False,
        }
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
        return [], {
            "status": int(getattr(exc, "code", 0) or 0),
            "latency_ms": int((time.monotonic() - started) * 1000),
            "bytes": 0,
            "prompt_sha256": prompt_sha256,
            "provider": "openai_responses_web_search",
            "model": model,
            "web_search_tool_calls": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "transient_response_text_present": False,
            "raw_response_persisted": False,
            "error": type(exc).__name__,
        }
