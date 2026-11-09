import unicodedata
from datetime import datetime, timedelta, timezone

import pytest

from rosetta_core.decision.answers import AnswerBatch, ChoiceAnswer, NoulAnswer, ScoreAnswer
from rosetta_core.decision.cache import (
    CACHE_KEY_VERSION,
    CacheScope,
    answers_from_entry,
    decision_cache_key,
    entry_usable,
    make_entry,
)
from rosetta_core.decision.contracts import Primitive, QuestionDef, QuestionSet
from rosetta_core.decision.state import Evidence, RouteRef, build_state

NOW = datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc)
ROUTES = (RouteRef("code_change", "Modify code", "a" * 64), RouteRef("clarify", "Ask for details", "b" * 64))
QSET = QuestionSet("intake", "1.1", (
    QuestionDef("route_fits", "1.1", Primitive.NOUL, "Does a listed workflow fit?"),
    QuestionDef("workflow_route", "1.1", Primitive.CHOICE, "Which workflow fits best?", {"code_change": "Modify code", "clarify": "Ask"}),
))
SCOPE = CacheScope(provider="jevmodel", served_model="jev-1.14.0", policy_id="intake", policy_version="0.1", ttl=timedelta(days=7))


def _state(text="Add a --verbose flag", constraints=None, retrieved=NOW, request_id="r1", proposed=None, source="request"):
    return build_state(
        request_id=request_id, objective="Route the request", constraints=constraints or {"data_class": "synthetic", "lang": "en"},
        evidence=(Evidence("request.text", text, source, retrieved.isoformat()),), eligible_routes=ROUTES,
        policy_ref="intake@0.1", required=("request.text",), max_age={"request.text": timedelta(days=1)},
        now=NOW, proposed_output=proposed,
    )


def _key(state, qset=QSET, scope=SCOPE):
    return decision_cache_key(state, qset, scope)


def test_same_meaning_in_different_formatting_shares_a_key():
    base = _key(_state())
    assert _key(_state(constraints={"lang": "en", "data_class": "synthetic"})) == base  # key order
    assert _key(_state(request_id="r2")) == base  # request id is not content
    assert _key(_state(retrieved=NOW - timedelta(minutes=5))) == base  # freshness is enforced by expiry, not the key


def test_line_endings_and_unicode_normal_form_are_normalised():
    composed = "Fix the café menu\nthen stop"
    decomposed = unicodedata.normalize("NFD", composed).replace("\n", "\r\n")
    assert _key(_state(text=decomposed)) == _key(_state(text=composed))


def test_any_change_of_content_changes_the_key():
    base = _key(_state())
    assert _key(_state(text="Add a --quiet flag")) != base
    assert _key(_state(text="Add a --verbose flag ")) != base  # internal and trailing whitespace can carry meaning
    assert _key(_state(proposed="def f():\n    return 1\n")) != _key(_state(proposed="def f():\n  return 1\n"))
    assert _key(_state(source="other-source")) != base  # the provider sees the source, so it is content


def test_near_miss_numbers_never_share_a_key():
    assert _key(_state(text="Budget 1,000; cost 1,000.")) != _key(_state(text="Budget 1,000; cost 1,001."))


def test_contract_provider_model_and_policy_are_part_of_the_key():
    base = _key(_state())
    reworded = QuestionSet("intake", "1.1", (QuestionDef("route_fits", "1.1", Primitive.NOUL, "Does any listed workflow fit?"),) + QSET.questions[1:])
    assert _key(_state(), qset=reworded) != base
    for change in ({"provider": "clef-ollama"}, {"served_model": "jev-1.15.0"}, {"policy_version": "0.2"}):
        scope = CacheScope(**{**SCOPE.__dict__, **change})
        assert _key(_state(), scope=scope) != base, change


def _batch(served="jev-1.14.0"):
    return AnswerBatch("jevmodel", "jev-latest", served, {
        "route_fits": NoulAnswer("route_fits", 0.93),
        "workflow_route": ChoiceAnswer("workflow_route", "code_change", {"code_change": 0.9, "clarify": 0.1}, 0.8),
    }, usage_input_tokens=850)


def test_entries_round_trip_answers_and_record_their_origin():
    state = _state()
    entry = make_entry(state, QSET, SCOPE, _batch(), now=NOW, evidence_expires_at=NOW + timedelta(days=1), source_receipt_id="rcpt-1")
    assert entry["key"] == _key(state) and entry["key_version"] == CACHE_KEY_VERSION
    assert entry["source_receipt_id"] == "rcpt-1"
    restored = answers_from_entry(entry)
    assert restored.served_model == "jev-1.14.0"
    assert restored.answers["workflow_route"].probabilities == {"code_change": 0.9, "clarify": 0.1}
    assert restored.usage_input_tokens == 0 and restored.extras["cache"] == "hit"


def test_score_answers_round_trip():
    qset = QuestionSet("lvl", "1.0", (QuestionDef("level", "1.0", Primitive.SCORE, "How much?", ("low", "mid", "high")),))
    batch = AnswerBatch("clef-ollama", "clef:cloud", "clef", {"level": ScoreAnswer("level", 1.4, (0.1, 0.6, 0.3), 0.4)})
    scope = CacheScope("clef-ollama", "clef", "lvl", "0.1", ttl=timedelta(hours=6))
    entry = make_entry(_state(), qset, scope, batch, now=NOW, evidence_expires_at=NOW + timedelta(days=1), source_receipt_id="r")
    assert answers_from_entry(entry).answers["level"] == ScoreAnswer("level", 1.4, (0.1, 0.6, 0.3), 0.4)


def test_entry_expires_at_the_earlier_of_ttl_and_evidence_freshness():
    entry = make_entry(_state(), QSET, SCOPE, _batch(), now=NOW, evidence_expires_at=NOW + timedelta(hours=2), source_receipt_id="r")
    key = entry["key"]
    assert entry_usable(entry, key, NOW + timedelta(hours=1), SCOPE) == (True, "HIT")
    assert entry_usable(entry, key, NOW + timedelta(hours=3), SCOPE) == (False, "EXPIRED")


def test_entry_is_refused_on_key_model_or_version_mismatch():
    entry = make_entry(_state(), QSET, SCOPE, _batch(), now=NOW, evidence_expires_at=NOW + timedelta(days=1), source_receipt_id="r")
    assert entry_usable(entry, "0" * 64, NOW, SCOPE) == (False, "KEY_MISMATCH")
    newer = CacheScope(**{**SCOPE.__dict__, "served_model": "jev-1.15.0"})
    assert entry_usable(entry, entry["key"], NOW, newer) == (False, "MODEL_CHANGED")
    old = dict(entry, key_version="0")
    assert entry_usable(old, entry["key"], NOW, SCOPE) == (False, "KEY_VERSION")


def test_only_answers_from_the_expected_served_model_are_cached():
    with pytest.raises(ValueError):
        make_entry(_state(), QSET, SCOPE, _batch(served="jev-1.15.0"), now=NOW, evidence_expires_at=NOW + timedelta(days=1), source_receipt_id="r")


def test_unversioned_models_need_a_short_ttl():
    with pytest.raises(ValueError):
        CacheScope("clef-ollama", "clef", "intake", "0.1", ttl=timedelta(days=7))
    CacheScope("clef-ollama", "clef", "intake", "0.1", ttl=timedelta(hours=6))
