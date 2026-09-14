from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RunBudget:
    max_challenge_requests: int = 1800
    max_third_party_cost_usd: float = 0.0
    max_wall_runtime_seconds: int = 2400
    max_redirects_per_logical_request: int = 1

    @property
    def request_charge_multiplier(self) -> int:
        return 1 + self.max_redirects_per_logical_request

    def charge_requests(self, logical_requests: int) -> int:
        if logical_requests < 0:
            raise ValueError("logical_requests cannot be negative")
        return logical_requests * self.request_charge_multiplier

    def validate(self, *, logical_requests: int, third_party_cost_usd: float, wall_runtime_seconds: float) -> list[str]:
        errors: list[str] = []
        charged = self.charge_requests(logical_requests)
        if charged > self.max_challenge_requests:
            errors.append(
                f"conservative challenge request charge {charged} exceeds {self.max_challenge_requests}"
            )
        if third_party_cost_usd > self.max_third_party_cost_usd:
            errors.append(
                f"third-party cost ${third_party_cost_usd:.4f} exceeds ${self.max_third_party_cost_usd:.4f}"
            )
        if wall_runtime_seconds > self.max_wall_runtime_seconds:
            errors.append(
                f"wall runtime {wall_runtime_seconds:.3f}s exceeds {self.max_wall_runtime_seconds}s"
            )
        return errors
