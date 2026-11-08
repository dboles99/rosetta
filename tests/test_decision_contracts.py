import pytest

from rosetta_core.decision.contracts import (
    CONTRACT_VERSION,
    ContractError,
    Primitive,
    QuestionDef,
    QuestionSet,
    canonical_json,
)


def _choice(**overrides) -> QuestionDef:
    fields = dict(
        qid="workflow_route",
        version="1.0",
        primitive=Primitive.CHOICE,
        instructions="Which eligible workflow fits `request.text` best?",
        criteria={"code_change": "Modify repository code", "docs_edit": "Edit documentation only"},
    )
    fields.update(overrides)
    return QuestionDef(**fields)


def _noul(**overrides) -> QuestionDef:
    fields = dict(
        qid="route_fits",
        version="1.0",
        primitive=Primitive.NOUL,
        instructions="Does at least one eligible workflow fit `request.text`?",
    )
    fields.update(overrides)
    return QuestionDef(**fields)


def test_contract_version_is_declared():
    assert CONTRACT_VERSION == "0.1"


def test_choice_question_exposes_options_in_declared_order():
    assert _choice().options == ("code_change", "docs_edit")


def test_choice_needs_at_least_two_options():
    with pytest.raises(ContractError):
        _choice(criteria={"only": "the one option"})


def test_choice_option_descriptions_must_not_be_blank():
    with pytest.raises(ContractError):
        _choice(criteria={"code_change": "Modify code", "docs_edit": " "})


def test_score_levels_are_ordered_low_to_high():
    question = QuestionDef(
        qid="intervention_level",
        version="1.0",
        primitive=Primitive.SCORE,
        instructions="How much editorial intervention does the passage need?",
        criteria=("light", "moderate", "heavy"),
    )
    assert question.levels == ("light", "moderate", "heavy")


def test_score_rejects_more_than_ten_levels():
    with pytest.raises(ContractError):
        QuestionDef(
            qid="effort",
            version="1.0",
            primitive=Primitive.SCORE,
            instructions="How much effort?",
            criteria=tuple(f"level{i}" for i in range(11)),
        )


def test_score_rejects_duplicate_levels():
    with pytest.raises(ContractError):
        QuestionDef(
            qid="effort",
            version="1.0",
            primitive=Primitive.SCORE,
            instructions="How much effort?",
            criteria=("low", "low"),
        )


def test_noul_criteria_may_only_clarify_yes_and_no():
    _noul(criteria={"yes": "A listed workflow covers the request", "no": "None does"})
    with pytest.raises(ContractError):
        _noul(criteria={"maybe": "unclear"})


def test_instructions_are_required():
    with pytest.raises(ContractError):
        _noul(instructions="   ")


def test_question_id_must_be_snake_case():
    with pytest.raises(ContractError):
        _noul(qid="Route Fits")


def test_version_must_be_numeric():
    with pytest.raises(ContractError):
        _noul(version="latest")


def test_content_hash_changes_when_wording_changes():
    assert _choice().content_hash() != _choice(instructions="Pick the closest workflow.").content_hash()


def test_content_hash_changes_when_option_order_changes():
    reordered = _choice(criteria={"docs_edit": "Edit documentation only", "code_change": "Modify repository code"})
    assert _choice().content_hash() != reordered.content_hash()


def test_question_set_rejects_duplicate_ids():
    with pytest.raises(ContractError):
        QuestionSet(set_id="intake", version="1.0", questions=(_noul(), _noul()))


def test_question_set_hash_covers_every_question():
    first = QuestionSet(set_id="intake", version="1.0", questions=(_noul(), _choice()))
    second = QuestionSet(
        set_id="intake",
        version="1.0",
        questions=(_noul(), _choice(criteria={"code_change": "Modify code", "docs_edit": "Docs"})),
    )
    assert first.content_hash() != second.content_hash()
    assert len(first.content_hash()) == 64


def test_question_set_lookup_by_id():
    qset = QuestionSet(set_id="intake", version="1.0", questions=(_noul(), _choice()))
    assert qset.get("workflow_route").primitive is Primitive.CHOICE
    assert qset.qids == ("route_fits", "workflow_route")


def test_canonical_json_is_sorted_and_compact():
    assert canonical_json({"b": 1, "a": "é"}) == '{"a":"é","b":1}'


def test_canonical_json_rejects_nan():
    with pytest.raises(ValueError):
        canonical_json({"x": float("nan")})
