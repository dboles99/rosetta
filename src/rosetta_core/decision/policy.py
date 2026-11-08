"""Pure reduction of deterministic gates plus typed answers into a recommendation.

Order of precedence (first match wins):
  1. hard deny from deterministic gates       -> DENY
  2. missing required evidence                -> NEED_EVIDENCE
  3. no decision / provider error             -> FALLBACK
  4. question set differs from calibration    -> FALLBACK (POLICY_QSET_MISMATCH)
  5. served model differs from calibration    -> FALLBACK (CALIBRATION_STALE)
  6. invalid or missing required answer       -> FALLBACK (INVALID_ANSWER:...)
  7. requirements question: low -> NEED_EVIDENCE, band -> ABSTAIN
  8. route_fits: low -> NO_FIT, band -> ABSTAIN
  9. selected route not eligible              -> ABSTAIN
 10. no distribution for the route choice     -> ABSTAIN
 11. p(selected) >= route threshold           -> ACCEPT, else ABSTAIN

Confidence is recorded by adapters but never used here: for Choice, the selected
option's probability is the gating value. Answers are not multiplied together.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping

from .answers import AnswerBatch, ProviderError, validate_batch
from .contracts import ContractError, QuestionSet


class Outcome(str, Enum):
    DENY = "DENY"
    NEED_EVIDENCE = "NEED_EVIDENCE"
    FALLBACK = "FALLBACK"
    NO_FIT = "NO_FIT"
    ABSTAIN = "ABSTAIN"
    ACCEPT = "ACCEPT"


@dataclass(frozen=True)
class GateResult:
    eligible_routes: tuple[str, ...]
    deny_reasons: tuple[str, ...] = ()
    missing_evidence: tuple[str, ...] = ()


def _check_band(name: str, yes: float, no: float) -> None:
    for label, value in ((f"{name}_yes", yes), (f"{name}_no", no)):
        if not isinstance(value, (int, float)) or not 0.0 <= value <= 1.0:
            raise ContractError(f"{label} must be within [0, 1]")
    if not no < yes:
        raise ContractError(f"{name}_no must be below {name}_yes")


@dataclass(frozen=True)
class IntakeThresholds:
    fit_yes: float
    fit_no: float
    requirements_yes: float
    requirements_no: float
    route_min_p: Mapping[str, float]

    def __post_init__(self) -> None:
        _check_band("fit", self.fit_yes, self.fit_no)
        _check_band("requirements", self.requirements_yes, self.requirements_no)
        if "*" not in self.route_min_p:
            raise ContractError("route_min_p needs a default '*' threshold")
        for route, value in self.route_min_p.items():
            if not isinstance(value, (int, float)) or not 0.0 <= value <= 1.0:
                raise ContractError(f"route threshold for {route!r} must be within [0, 1]")

    def route_threshold(self, route: str) -> float:
        return self.route_min_p.get(route, self.route_min_p["*"])


@dataclass(frozen=True)
class IntakeQuestions:
    fit: str = "route_fits"
    route: str = "workflow_route"
    requirements: str | None = "requirements_sufficient"


@dataclass(frozen=True)
class Policy:
    policy_id: str
    version: str
    provider: str
    served_model: str
    qset_id: str
    qset_hash: str
    thresholds: IntakeThresholds
    calibrated: bool
    frozen_at: str
    split_hash: str | None = None
    questions: IntakeQuestions = field(default_factory=IntakeQuestions)


@dataclass(frozen=True)
class Recommendation:
    outcome: Outcome
    route: str | None
    reason_codes: tuple[str, ...]
    signals: Mapping[str, object] = field(default_factory=dict)


def _rec(outcome: Outcome, *reasons: str, route: str | None = None, signals=None) -> Recommendation:
    return Recommendation(outcome=outcome, route=route, reason_codes=tuple(reasons), signals=dict(signals or {}))


def reduce(
    gates: GateResult,
    result: AnswerBatch | ProviderError | None,
    policy: Policy,
    qset: QuestionSet,
) -> Recommendation:
    if gates.deny_reasons:
        return _rec(Outcome.DENY, *gates.deny_reasons)
    if gates.missing_evidence:
        return _rec(Outcome.NEED_EVIDENCE, *(f"MISSING_EVIDENCE:{key}" for key in gates.missing_evidence))
    if result is None:
        return _rec(Outcome.FALLBACK, "NO_DECISION")
    if isinstance(result, ProviderError):
        return _rec(Outcome.FALLBACK, f"PROVIDER_{result.kind.value}")
    if qset.set_id != policy.qset_id or qset.content_hash() != policy.qset_hash:
        return _rec(Outcome.FALLBACK, "POLICY_QSET_MISMATCH")
    if result.served_model != policy.served_model:
        return _rec(Outcome.FALLBACK, "CALIBRATION_STALE")

    q = policy.questions
    needed = [q.fit, q.route] + ([q.requirements] if q.requirements else [])
    violations = [v for v in validate_batch(result, qset) if v.qid in needed]
    if violations:
        first = violations[0]
        return _rec(Outcome.FALLBACK, f"INVALID_ANSWER:{first.qid}:{first.code}")

    t = policy.thresholds
    signals: dict[str, object] = {f"{q.fit}.p_yes": result.answers[q.fit].p_yes}

    if q.requirements:
        p_req = result.answers[q.requirements].p_yes
        signals[f"{q.requirements}.p_yes"] = p_req
        if p_req <= t.requirements_no:
            return _rec(Outcome.NEED_EVIDENCE, "REQUIREMENTS_NOT_SUPPLIED", signals=signals)
        if p_req < t.requirements_yes:
            return _rec(Outcome.ABSTAIN, "REQUIREMENTS_UNCERTAIN", signals=signals)

    p_fit = result.answers[q.fit].p_yes
    if p_fit <= t.fit_no:
        return _rec(Outcome.NO_FIT, "NO_ROUTE_FITS", signals=signals)
    if p_fit < t.fit_yes:
        return _rec(Outcome.ABSTAIN, "ROUTE_FIT_UNCERTAIN", signals=signals)

    choice = result.answers[q.route]
    signals[f"{q.route}.selected"] = choice.selected
    if choice.selected not in gates.eligible_routes:
        return _rec(Outcome.ABSTAIN, "ROUTE_NOT_ELIGIBLE", signals=signals)
    if not choice.probabilities:
        return _rec(Outcome.ABSTAIN, "NO_DISTRIBUTION", signals=signals)
    p_selected = choice.probabilities[choice.selected]
    signals[f"{q.route}.p_selected"] = p_selected
    if p_selected >= t.route_threshold(choice.selected):
        return _rec(Outcome.ACCEPT, "ROUTE_ACCEPTED", route=choice.selected, signals=signals)
    return _rec(Outcome.ABSTAIN, "LOW_ROUTE_PROBABILITY", signals=signals)


def may_reask(prev_state_digest: str, prev_qset_hash: str, state_digest: str, qset_hash: str) -> bool:
    """A semantic re-ask is allowed only when the evidence or the question contract changed."""
    return prev_state_digest != state_digest or prev_qset_hash != qset_hash
