from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


MAX_REDIRECTS_PER_ATTEMPT = 1


class LimitedRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Allow at most one redirect for each logical HTTP attempt.

    The evaluator counts redirects as outbound requests. Bounding redirect depth lets the
    final orchestrator conservatively charge two outbound requests for every recorded
    logical attempt: the original request plus at most one redirect.
    """

    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> Any:
        redirect_count = int(getattr(req, "_signalpost_redirect_count", 0))
        if redirect_count >= MAX_REDIRECTS_PER_ATTEMPT:
            raise urllib.error.HTTPError(newurl, code, "Signalpost redirect limit exceeded", headers, fp)
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected is not None:
            setattr(redirected, "_signalpost_redirect_count", redirect_count + 1)
        return redirected


HTTP_OPENER = urllib.request.build_opener(LimitedRedirectHandler())


@dataclass
class FetchResult:
    url: str
    status: int
    elapsed_ms: int
    bytes_received: int
    body: Any = None
    error: str | None = None
    content_sha256: str | None = None
    retrieved_at: str | None = None
    effective_at: str | None = None
    request_count: int = 1


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def fetch_json(url: str, *, timeout: float = 20.0, attempts: int = 3) -> FetchResult:
    if attempts < 1:
        raise ValueError("attempts must be positive")
    last_error = "request failed"
    for attempt in range(attempts):
        started = time.monotonic()
        request = urllib.request.Request(
            url,
            headers={"Accept": "application/json", "User-Agent": "builderr-signalpost-poc/0.1 (+https://builderr.ai)"},
        )
        try:
            with HTTP_OPENER.open(request, timeout=timeout) as response:
                raw = response.read()
                elapsed = int((time.monotonic() - started) * 1000)
                return FetchResult(
                    url,
                    response.status,
                    elapsed,
                    len(raw),
                    json.loads(raw),
                    content_sha256=hashlib.sha256(raw).hexdigest(),
                    retrieved_at=_utc_now(),
                    request_count=attempt + 1,
                )
        except urllib.error.HTTPError as exc:
            elapsed = int((time.monotonic() - started) * 1000)
            raw = exc.read()
            if exc.code in {404, 410}:
                return FetchResult(
                    url,
                    exc.code,
                    elapsed,
                    len(raw),
                    error=f"HTTP {exc.code}",
                    content_sha256=hashlib.sha256(raw).hexdigest(),
                    retrieved_at=_utc_now(),
                    request_count=attempt + 1,
                )
            last_error = f"HTTP {exc.code}"
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = type(exc).__name__
        if attempt + 1 < attempts:
            time.sleep(0.4 * (2**attempt))
    return FetchResult(
        url,
        0,
        0,
        0,
        error=last_error,
        retrieved_at=_utc_now(),
        request_count=attempts,
    )
