import math

import pytest

from rosetta_core.decision.answers import AnswerBatch, ChoiceAnswer, ErrorKind, NoulAnswer, ProviderError
from rosetta_core.decision.contracts import ContractError, Primitive, QuestionDef, QuestionSet
from rosetta_core.decision.policy import (
    GateResult,
    IntakeThresholds,
    Outcome,
    Policy,
    may_reask,
    reduce,
)

ROUTES = ("code_change", "docs_edit", "clarify")
QSET = QuestionSet(
    set_id="intake",
    version="1.0",
    questions=(
        QuestionDef("route_fits", "1.0", Primitive.NOUL, "Does an eligible workflow fit the request?"),
        QuestionDef(
            "workflow_route",
            "1.0",
            Primitive.CHOICE,
            "Which eligible workflow fits the request best?",
            {"code_change": "Modify code", "docs_edit": "Edit docs", "clarify": "Ask for information"},
        ),
        QuestionDef("requirements_sufficient", "1.0", Primitive.NOUL, "Is the listed required information present?"),
    ),
)
POLICY = Policy(
    policy_id="intake",
    version="0.1",
    provider="fake",
    served_model="jev-latest",
    qset_id="intake",
    qset_hash=QSET.content_hash(),
    thresholds=IntakeThresholds(
        fit_yes=0.7,
        fit_no=0.3,
        requirements_yes=0.7,
        requirements_no=0.3,
        route_min_p={"*": 0.6, "code_change": 0.8},
    ),
    calibrated=False,
    frozen_at="2026-11-09T00:00:00Z",
)
GATES = GateResult(eligible_routes=ROUTES)


def _batch(fit=0.9, req=0.9, selected="docs_edit", probs=None, confidence=0.5, served="jev-latest", drop=()):
    if probs is None:
        probs = {"code_change": 0.05, "docs_edit": 0.9, "clarify": 0.05}
    answers = {
        "route_fits": NoulAnswer("route_fits", fit),
        "workflow_route": ChoiceAnswer("workflow_route", selected, probs, confidence),
        "requirements_sufficient": NoulAnswer("requirements_sufficient", req),
    }
    for qid in drop:
        answers.pop(qid)
    return AnswerBatch(provider="fake", requested_model="jev-latest", served_model=served, answers=answers)


def test_accepts_confident_eligible_route():
    rec = reduce(GATES, _batch(), POLICY, QSET)
    assert rec.outcome is Outcome.ACCEPT
    assert rec.route == "docs_edit"


def test_route_specific_threshold_applies():
    probs = {"code_change": 0.75, "docs_edit": 0.15, "clarify": 0.1}
    rec = reduce(GATES, _batch(selected="code_change", probs=probs), POLICY, QSET)
    assert rec.outcome is Outcome.ABSTAIN
    assert "LOW_ROUTE_PROBABILITY" in rec.reason_codes


def test_hard_deny_wins_over_confident_answers():
    gates = GateResult(eligible_routes=ROUTES, deny_reasons=("DATA_CLASS_FORBIDDEN",))
    rec = reduce(gates, _batch(), POLICY, QSET)
    assert rec.outcome is Outcome.DENY
    assert rec.route is None
    assert rec.reason_codes == ("DATA_CLASS_FORBIDDEN",)


def test_missing_evidence_is_requested_before_any_answer_is_read():
    gates = GateResult(eligible_routes=ROUTES, missing_evidence=("request.text",))
    rec = reduce(gates, _batch(), POLICY, QSET)
    assert rec.outcome is Outcome.NEED_EVIDENCE
    assert rec.reason_codes == ("MISSING_EVIDENCE:request.text",)


def test_provider_error_falls_back_and_never_accepts():
    rec = reduce(GATES, ProviderError(ErrorKind.TIMEOUT, "read timed out"), POLICY, QSET)
    assert rec.outcome is Outcome.FALLBACK
    assert rec.reason_codes == ("PROVIDER_TIMEOUT",)


def test_absent_decision_falls_back():
    rec = reduce(GATES, None, POLICY, QSET)
    assert rec.outcome is Outcome.FALLBACK
    assert rec.reason_codes == ("NO_DECISION",)


def test_low_route_fit_is_no_fit():
    rec = reduce(GATES, _batch(fit=0.1), POLICY, QSET)
    assert rec.outcome is Outcome.NO_FIT


def test_uncertain_route_fit_abstains():
    rec = reduce(GATES, _batch(fit=0.5), POLICY, QSET)
    assert rec.outcome is Outcome.ABSTAIN
    assert "ROUTE_FIT_UNCERTAIN" in rec.reason_codes


def test_no_fit_holds_even_when_route_choice_is_confident():
    probs = {"code_change": 0.0, "docs_edit": 1.0, "clarify": 0.0}
    rec = reduce(GATES, _batch(fit=0.05, probs=probs), POLICY, QSET)
    assert rec.outcome is Outcome.NO_FIT
    assert rec.route is None


def test_semantically_missing_requirements_request_evidence():
    rec = reduce(GATES, _batch(req=0.1), POLICY, QSET)
    assert rec.outcome is Outcome.NEED_EVIDENCE
    assert "REQUIREMENTS_NOT_SUPPLIED" in rec.reason_codes


def test_ineligible_route_abstains():
    gates = GateResult(eligible_routes=("code_change", "clarify"))
    rec = reduce(gates, _batch(), POLICY, QSET)
    assert rec.outcome is Outcome.ABSTAIN
    assert "ROUTE_NOT_ELIGIBLE" in rec.reason_codes


def test_invalid_answer_falls_back():
    rec = reduce(GATES, _batch(fit=math.nan), POLICY, QSET)
    assert rec.outcome is Outcome.FALLBACK
    assert rec.reason_codes == ("INVALID_ANSWER:route_fits:BAD_PROBABILITY",)


def test_missing_answer_falls_back():
    rec = reduce(GATES, _batch(drop=("workflow_route",)), POLICY, QSET)
    assert rec.outcome is Outcome.FALLBACK
    assert rec.reason_codes == ("INVALID_ANSWER:workflow_route:MISSING",)


def test_model_change_invalidates_calibration():
    rec = reduce(GATES, _batch(served="jev-1.15.0"), POLICY, QSET)
    assert rec.outcome is Outcome.FALLBACK
    assert rec.reason_codes == ("CALIBRATION_STALE",)


def test_question_set_change_falls_back():
    changed = QuestionSet(
        set_id="intake",
        version="1.0",
        questions=QSET.questions[:2]
        + (QuestionDef("requirements_sufficient", "1.0", Primitive.NOUL, "Reworded requirement question?"),),
    )
    rec = reduce(GATES, _batch(), POLICY, changed)
    assert rec.outcome is Outcome.FALLBACK
    assert rec.reason_codes == ("POLICY_QSET_MISMATCH",)


def test_choice_without_distribution_abstains():
    sparse = _batch()
    sparse.answers["workflow_route"] = ChoiceAnswer("workflow_route", "docs_edit", None, 0.99)
    rec = reduce(GATES, sparse, POLICY, QSET)
    assert rec.outcome is Outcome.ABSTAIN
    assert "NO_DISTRIBUTION" in rec.reason_codes


def test_confidence_is_not_used_for_gating():
    probs = {"code_change": 0.2, "docs_edit": 0.65, "clarify": 0.15}
    rec = reduce(GATES, _batch(probs=probs, confidence=0.0), POLICY, QSET)
    assert rec.outcome is Outcome.ACCEPT


def test_recommendation_records_the_values_it_used():
    rec = reduce(GATES, _batch(), POLICY, QSET)
    assert rec.signals == {
        "route_fits.p_yes": 0.9,
        "requirements_sufficient.p_yes": 0.9,
        "workflow_route.selected": "docs_edit",
        "workflow_route.p_selected": 0.9,
    }


def test_policy_rejects_an_inverted_band():
    with pytest.raises(ContractError):
        IntakeThresholds(fit_yes=0.3, fit_no=0.7, requirements_yes=0.7, requirements_no=0.3, route_min_p={"*": 0.6})


def test_policy_requires_a_default_route_threshold():
    with pytest.raises(ContractError):
        IntakeThresholds(fit_yes=0.7, fit_no=0.3, requirements_yes=0.7, requirements_no=0.3, route_min_p={"code_change": 0.8})


def test_may_reask_only_when_state_or_questions_change():
    assert may_reask("s1", "q1", "s1", "q1") is False
    assert may_reask("s1", "q1", "s2", "q1") is True
    assert may_reask("s1", "q1", "s1", "q2") is True
