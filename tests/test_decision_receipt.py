import copy

import pytest

from rosetta_core.decision.receipt import (
    RECEIPT_VERSION,
    ReceiptInvalid,
    assert_no_secrets,
    new_receipt_id,
    validate_receipt,
)

H = "0" * 64


def _receipt(**overrides) -> dict:
    receipt = {
        "receipt_version": RECEIPT_VERSION,
        "receipt_id": "r-1",
        "run_id": "run-1",
        "trial_id": "t-1",
        "case_id": "case-1",
        "created_at": "2026-11-09T12:00:00Z",
        "repos": {"core": "a" * 40, "bench": "b" * 40},
        "contract_version": "0.1",
        "state": {"schema_version": "0.1", "digest": H, "snapshot_ref": None},
        "replay": "unavailable",
        "question_set": {"set_id": "intake", "version": "1.0", "hash": H},
        "policy": {"policy_id": "intake", "version": "0.1", "calibrated": False},
        "provider": {"name": "fake", "requested_model": "jev-latest", "served_model": "jev-latest", "revision_known": False},
        "answers_ref": None,
        "recommendation": {"outcome": "ACCEPT", "route": "docs_edit", "reason_codes": []},
        "executed_route": "default",
        "mode": "shadow",
        "generator": {"tool": "FAKE", "model": "fake-1", "settings": {}},
        "usage": {"decision_input_tokens": 120, "generator_tokens_in": 300, "generator_tokens_out": 80},
        "cost": {"usd": None, "basis": "unknown", "price_source": None, "price_as_of": None},
        "timings_ms": {"decision": 210.5, "generation": 900.0},
        "retries": {"transport": 0, "semantic": 0},
        "output_digest": H,
        "outcome": {"verified_success": True, "checks": {"acceptance_tests": True}},
        "override": None,
    }
    receipt.update(overrides)
    return receipt


def test_valid_receipt_passes():
    validate_receipt(_receipt())


def test_missing_required_field_is_rejected():
    receipt = _receipt()
    del receipt["state"]
    with pytest.raises(ReceiptInvalid):
        validate_receipt(receipt)


def test_unknown_cost_is_null_not_zero():
    with pytest.raises(ReceiptInvalid):
        validate_receipt(_receipt(cost={"usd": 0.0, "basis": "unknown", "price_source": None, "price_as_of": None}))


def test_priced_cost_needs_a_number_and_a_source():
    with pytest.raises(ReceiptInvalid):
        validate_receipt(_receipt(cost={"usd": None, "basis": "priced", "price_source": "pack", "price_as_of": "2026-11-09"}))
    with pytest.raises(ReceiptInvalid):
        validate_receipt(_receipt(cost={"usd": 0.01, "basis": "priced", "price_source": None, "price_as_of": None}))
    validate_receipt(_receipt(cost={"usd": 0.01, "basis": "priced", "price_source": "jevmodel pack", "price_as_of": "2026-11-09"}))


def test_subscription_cost_is_null():
    validate_receipt(_receipt(cost={"usd": None, "basis": "subscription", "price_source": "ollama cloud", "price_as_of": None}))
    with pytest.raises(ReceiptInvalid):
        validate_receipt(_receipt(cost={"usd": 0.0, "basis": "subscription", "price_source": None, "price_as_of": None}))


def test_mode_must_be_known():
    with pytest.raises(ReceiptInvalid):
        validate_receipt(_receipt(mode="auto"))


def test_negative_timing_is_rejected():
    with pytest.raises(ReceiptInvalid):
        validate_receipt(_receipt(timings_ms={"decision": -1.0}))


def test_hashes_must_be_sha256_hex():
    receipt = _receipt()
    receipt["question_set"] = dict(receipt["question_set"], hash="not-a-hash")
    with pytest.raises(ReceiptInvalid):
        validate_receipt(receipt)


def test_disabled_mode_has_no_provider_or_recommendation():
    validate_receipt(_receipt(mode="disabled", provider=None, recommendation=None, question_set=None, policy=None))
    with pytest.raises(ReceiptInvalid):
        validate_receipt(_receipt(mode="shadow", provider=None))


def test_assert_no_secrets_finds_bearer_tokens():
    fake_token = "sk-" + "x" * 24  # built at runtime so no token-shaped literal is committed
    receipt = _receipt(override=f"Authorization: Bearer {fake_token}")
    with pytest.raises(ReceiptInvalid):
        assert_no_secrets(receipt)


def test_assert_no_secrets_finds_forbidden_literals():
    receipt = copy.deepcopy(_receipt())
    receipt["recommendation"]["reason_codes"] = ["contact alice@example.com"]
    with pytest.raises(ReceiptInvalid):
        assert_no_secrets(receipt, forbidden=("alice@example.com",))


def test_assert_no_secrets_passes_a_clean_receipt():
    assert_no_secrets(_receipt(), forbidden=("alice@example.com",))


def test_new_receipt_ids_are_unique():
    assert len({new_receipt_id() for _ in range(100)}) == 100
