"""Bounded, provenance-aware decision state.

`build_state` fails closed: missing, blank, stale, future-dated or unserializable
evidence raises `StateRejected` instead of being passed to a provider. Evidence is
untrusted data by default; trusted instructions live in question definitions.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Mapping, Sequence

from ..hashing import sha256_text
from .contracts import canonical_json

STATE_SCHEMA_VERSION = "0.1"
_CLOCK_SKEW = timedelta(minutes=5)
_DEFAULT_MAX_BYTES = 200_000


@dataclass(frozen=True)
class Evidence:
    key: str
    value: object
    source: str
    retrieved_at: str
    verified: bool = False
    trusted: bool = False


@dataclass(frozen=True)
class RouteRef:
    route_id: str
    description: str
    contract_digest: str


@dataclass(frozen=True)
class DecisionState:
    schema_version: str
    request_id: str
    objective: str
    constraints: Mapping[str, object]
    evidence: tuple[Evidence, ...]
    eligible_routes: tuple[RouteRef, ...]
    policy_ref: str
    built_at: str
    proposed_output: str | None = None


class StateRejected(ValueError):
    def __init__(self, missing=(), stale=(), problems=()):
        self.missing = tuple(missing)
        self.stale = tuple(stale)
        self.problems = tuple(problems)
        parts = []
        if self.missing:
            parts.append(f"missing: {', '.join(self.missing)}")
        if self.stale:
            parts.append(f"stale: {', '.join(self.stale)}")
        if self.problems:
            parts.append(f"problems: {', '.join(self.problems)}")
        super().__init__("; ".join(parts) or "state rejected")


def _is_blank(value) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _parse_time(text: str) -> datetime | None:
    try:
        return datetime.fromisoformat(text)
    except (TypeError, ValueError):
        return None


def build_state(
    *,
    request_id: str,
    objective: str,
    constraints: Mapping[str, object],
    evidence: Sequence[Evidence],
    eligible_routes: Sequence[RouteRef],
    policy_ref: str,
    required: Sequence[str],
    max_age: Mapping[str, timedelta],
    now: datetime,
    proposed_output: str | None = None,
    max_bytes: int = _DEFAULT_MAX_BYTES,
) -> DecisionState:
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    missing: list[str] = []
    stale: list[str] = []
    problems: list[str] = []

    by_key: dict[str, Evidence] = {}
    for item in evidence:
        if item.key in by_key:
            problems.append(f"DUPLICATE_EVIDENCE:{item.key}")
            continue
        by_key[item.key] = item
        try:
            canonical_json(item.value)
        except (TypeError, ValueError):
            problems.append(f"NOT_JSON:{item.key}")
        retrieved = _parse_time(item.retrieved_at)
        if retrieved is None:
            problems.append(f"BAD_TIMESTAMP:{item.key}")
        elif retrieved.tzinfo is None:
            problems.append(f"NAIVE_TIMESTAMP:{item.key}")
        elif retrieved > now + _CLOCK_SKEW:
            problems.append(f"FUTURE_TIMESTAMP:{item.key}")
        elif item.key in max_age and now - retrieved > max_age[item.key]:
            stale.append(item.key)

    for key in required:
        if key not in by_key or _is_blank(by_key[key].value):
            missing.append(key)

    if not eligible_routes:
        problems.append("NO_ELIGIBLE_ROUTES")
    seen_routes: set[str] = set()
    for route in eligible_routes:
        if route.route_id in seen_routes:
            problems.append(f"DUPLICATE_ROUTE:{route.route_id}")
        seen_routes.add(route.route_id)

    state = DecisionState(
        schema_version=STATE_SCHEMA_VERSION,
        request_id=request_id,
        objective=objective,
        constraints=dict(constraints),
        evidence=tuple(evidence),
        eligible_routes=tuple(eligible_routes),
        policy_ref=policy_ref,
        built_at=now.isoformat(),
        proposed_output=proposed_output,
    )
    if not problems:
        try:
            size = len(canonical_json(wire_state(state)).encode("utf-8"))
        except (TypeError, ValueError):
            problems.append("NOT_JSON:constraints")
        else:
            if size > max_bytes:
                problems.append("STATE_TOO_LARGE")

    if missing or stale or problems:
        raise StateRejected(missing=missing, stale=stale, problems=problems)
    return state


def wire_state(state: DecisionState) -> dict:
    """The exact structure a decision provider receives as `state`."""
    wire = {
        "objective": state.objective,
        "constraints": dict(state.constraints),
        "routes": {route.route_id: route.description for route in state.eligible_routes},
        "evidence": {
            item.key: {
                "value": item.value,
                "source": item.source,
                "retrieved_at": item.retrieved_at,
                "verified": item.verified,
                "trusted": item.trusted,
            }
            for item in state.evidence
        },
    }
    if state.proposed_output is not None:
        wire["proposed_output"] = state.proposed_output
    return wire


def state_digest(state: DecisionState) -> str:
    """Digest of what is judged. Excludes request ID and build time, so an unchanged
    question over unchanged evidence produces the same digest."""
    return sha256_text(
        canonical_json(
            {
                "schema_version": state.schema_version,
                "policy_ref": state.policy_ref,
                "route_contracts": [r.contract_digest for r in state.eligible_routes],
                "wire": wire_state(state),
            }
        )
    )
