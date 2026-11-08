import math

from rosetta_core.decision.answers import (
    AnswerBatch,
    ChoiceAnswer,
    ErrorKind,
    NoulAnswer,
    ProviderError,
    ScoreAnswer,
    validate_batch,
)
from rosetta_core.decision.contracts import Primitive, QuestionDef, QuestionSet

QSET = QuestionSet(
    set_id="intake",
    version="1.0",
    questions=(
        QuestionDef("route_fits", "1.0", Primitive.NOUL, "Does an eligible workflow fit?"),
        QuestionDef(
            "workflow_route",
            "1.0",
            Primitive.CHOICE,
            "Which workflow fits best?",
            {"code_change": "Modify code", "clarify": "Ask for information"},
        ),
        QuestionDef("effort", "1.0", Primitive.SCORE, "How much effort?", ("low", "medium", "high")),
    ),
)

GOOD = {
    "route_fits": NoulAnswer("route_fits", 0.9),
    "workflow_route": ChoiceAnswer("workflow_route", "code_change", {"code_change": 0.8, "clarify": 0.2}, 0.6),
    "effort": ScoreAnswer("effort", 1.0, (0.1, 0.8, 0.1), 0.7),
}


def _batch(**replace) -> AnswerBatch:
    answers = dict(GOOD)
    for qid, answer in replace.items():
        if answer is None:
            answers.pop(qid)
        else:
            answers[qid] = answer
    return AnswerBatch(provider="fake", requested_model="jev-latest", served_model="jev-latest", answers=answers)


def _codes(batch) -> set[str]:
    return {v.code for v in validate_batch(batch, QSET)}


def test_valid_batch_has_no_violations():
    assert validate_batch(_batch(), QSET) == []


def test_nan_probability_is_rejected():
    assert _codes(_batch(route_fits=NoulAnswer("route_fits", math.nan))) == {"BAD_PROBABILITY"}


def test_out_of_range_probability_is_rejected():
    assert _codes(_batch(route_fits=NoulAnswer("route_fits", 1.2))) == {"BAD_PROBABILITY"}


def test_boolean_is_not_a_probability():
    assert _codes(_batch(route_fits=NoulAnswer("route_fits", True))) == {"BAD_PROBABILITY"}


def test_unknown_selected_option_is_rejected():
    bad = ChoiceAnswer("workflow_route", "deploy", {"code_change": 0.8, "clarify": 0.2}, 0.6)
    assert "UNKNOWN_OPTION" in _codes(_batch(workflow_route=bad))


def test_unknown_option_in_distribution_is_rejected():
    bad = ChoiceAnswer("workflow_route", "code_change", {"code_change": 0.7, "clarify": 0.2, "deploy": 0.1}, 0.6)
    assert "UNKNOWN_OPTION" in _codes(_batch(workflow_route=bad))


def test_distribution_must_sum_to_one():
    bad = ChoiceAnswer("workflow_route", "code_change", {"code_change": 0.5, "clarify": 0.2}, 0.6)
    assert _codes(_batch(workflow_route=bad)) == {"BAD_DISTRIBUTION"}


def test_incomplete_distribution_is_flagged():
    bad = ChoiceAnswer("workflow_route", "code_change", {"code_change": 1.0}, 1.0)
    assert _codes(_batch(workflow_route=bad)) == {"INCOMPLETE_DISTRIBUTION"}


def test_selected_option_must_have_the_highest_probability():
    bad = ChoiceAnswer("workflow_route", "clarify", {"code_change": 0.8, "clarify": 0.2}, 0.6)
    assert _codes(_batch(workflow_route=bad)) == {"SELECTED_NOT_ARGMAX"}


def test_choice_without_distribution_is_allowed():
    sparse = ChoiceAnswer("workflow_route", "clarify", None, None)
    assert validate_batch(_batch(workflow_route=sparse), QSET) == []


def test_missing_question_is_reported():
    assert _codes(_batch(effort=None)) == {"MISSING"}


def test_unexpected_question_is_reported():
    batch = _batch()
    batch.answers["urgency"] = NoulAnswer("urgency", 0.5)
    assert _codes(batch) == {"UNEXPECTED_QUESTION"}


def test_wrong_primitive_is_reported():
    assert _codes(_batch(workflow_route=NoulAnswer("workflow_route", 0.5))) == {"WRONG_PRIMITIVE"}


def test_score_position_must_lie_on_the_scale():
    assert _codes(_batch(effort=ScoreAnswer("effort", 2.5, None, None))) == {"BAD_SCORE"}


def test_score_distribution_length_must_match_levels():
    assert _codes(_batch(effort=ScoreAnswer("effort", 1.0, (0.5, 0.5), 0.2))) == {"BAD_DISTRIBUTION"}


def test_confidence_out_of_range_is_rejected():
    bad = ChoiceAnswer("workflow_route", "code_change", {"code_change": 0.8, "clarify": 0.2}, -0.1)
    assert _codes(_batch(workflow_route=bad)) == {"BAD_CONFIDENCE"}


def test_provider_errors_carry_a_retry_classification():
    assert ErrorKind.TIMEOUT.retryable and ErrorKind.RATE_LIMITED.retryable and ErrorKind.UNAVAILABLE.retryable
    assert not ErrorKind.AUTH.retryable
    assert not ErrorKind.QUOTA_EXHAUSTED.retryable
    assert not ErrorKind.MALFORMED.retryable
    error = ProviderError(ErrorKind.TIMEOUT, "read timed out after 15s", attempts=3)
    assert error.retryable is True
    assert not hasattr(error, "answers")
