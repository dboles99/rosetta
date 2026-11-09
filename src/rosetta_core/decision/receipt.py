"""Versioned decision receipt: JSON Schema plus rules JSON Schema cannot express.

A receipt binds the state digest, question set, policy, provider and served model,
recommendation, executed route, timings, nullable cost and verified outcome. A digest
alone is not replay data: `replay` says whether a retained redacted snapshot exists.
"""
from __future__ import annotations

import json
import re
import uuid
from typing import Iterable

import jsonschema

RECEIPT_VERSION = "1"

_HASH = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
_NULLABLE_STR = {"type": ["string", "null"]}
_NONNEG_NUM = {"type": "number", "minimum": 0}

RECEIPT_SCHEMA: dict = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "receipt_version", "receipt_id", "run_id", "trial_id", "case_id", "created_at", "repos",
        "contract_version", "state", "replay", "question_set", "policy", "provider", "answers_ref",
        "recommendation", "executed_route", "mode", "generator", "usage", "cost", "timings_ms",
        "retries", "output_digest", "outcome", "override",
    ],
    "properties": {
        "receipt_version": {"const": RECEIPT_VERSION},
        "receipt_id": {"type": "string", "minLength": 1},
        "run_id": {"type": "string", "minLength": 1},
        "trial_id": {"type": "string", "minLength": 1},
        "case_id": {"type": "string", "minLength": 1},
        "created_at": {"type": "string", "minLength": 1},
        "repos": {
            "type": "object",
            "required": ["core", "bench"],
            "properties": {"core": _NULLABLE_STR, "bench": _NULLABLE_STR},
        },
        "contract_version": {"type": "string"},
        "state": {
            "type": "object",
            "additionalProperties": False,
            "required": ["schema_version", "digest", "snapshot_ref"],
            "properties": {"schema_version": {"type": "string"}, "digest": _HASH, "snapshot_ref": _NULLABLE_STR},
        },
        "replay": {"enum": ["available", "unavailable"]},
        "question_set": {
            "type": ["object", "null"],
            "additionalProperties": False,
            "required": ["set_id", "version", "hash"],
            "properties": {"set_id": {"type": "string"}, "version": {"type": "string"}, "hash": _HASH},
        },
        "policy": {
            "type": ["object", "null"],
            "additionalProperties": False,
            "required": ["policy_id", "version", "calibrated"],
            "properties": {"policy_id": {"type": "string"}, "version": {"type": "string"}, "calibrated": {"type": "boolean"}},
        },
        "provider": {
            "type": ["object", "null"],
            "additionalProperties": False,
            "required": ["name", "requested_model", "served_model", "revision_known"],
            "properties": {
                "name": {"type": "string"},
                "requested_model": {"type": "string"},
                "served_model": _NULLABLE_STR,
                "revision_known": {"type": "boolean"},
            },
        },
        "answers_ref": _NULLABLE_STR,
        "recommendation": {
            "type": ["object", "null"],
            "additionalProperties": False,
            "required": ["outcome", "route", "reason_codes"],
            "properties": {
                "outcome": {"enum": ["DENY", "NEED_EVIDENCE", "FALLBACK", "NO_FIT", "ABSTAIN", "ACCEPT"]},
                "route": _NULLABLE_STR,
                "reason_codes": {"type": "array", "items": {"type": "string"}},
            },
        },
        "executed_route": _NULLABLE_STR,
        "mode": {"enum": ["disabled", "shadow", "enforced"]},
        "generator": {
            "type": ["object", "null"],
            "required": ["tool", "model", "settings"],
            "properties": {"tool": {"type": "string"}, "model": {"type": "string"}, "settings": {"type": "object"}},
        },
        "usage": {
            "type": "object",
            "additionalProperties": {"type": ["integer", "null"], "minimum": 0},
        },
        "cost": {
            "type": "object",
            "additionalProperties": False,
            "required": ["usd", "basis", "price_source", "price_as_of"],
            "properties": {
                "usd": {"type": ["number", "null"], "minimum": 0},
                "basis": {"enum": ["priced", "unknown", "free_local", "subscription", "legacy_unverified"]},
                "price_source": _NULLABLE_STR,
                "price_as_of": _NULLABLE_STR,
            },
        },
        "timings_ms": {"type": "object", "additionalProperties": _NONNEG_NUM},
        "retries": {
            "type": "object",
            "additionalProperties": False,
            "required": ["transport", "semantic"],
            "properties": {"transport": {"type": "integer", "minimum": 0}, "semantic": {"type": "integer", "minimum": 0}},
        },
        "output_digest": {"anyOf": [_HASH, {"type": "null"}]},
        "outcome": {
            "type": "object",
            "required": ["verified_success", "checks"],
            "properties": {
                "verified_success": {"type": ["boolean", "null"]},
                "checks": {"type": "object", "additionalProperties": {"type": ["boolean", "null"]}},
            },
        },
        "override": _NULLABLE_STR,
        # Optional, added for the canonical decision cache; receipts without it stay valid.
        "cache": {
            "type": "object",
            "additionalProperties": False,
            "required": ["status"],
            "properties": {
                "status": {"enum": ["off", "miss", "hit"]},
                "key": {"anyOf": [_HASH, {"type": "null"}]},
                "source_receipt_id": _NULLABLE_STR,
            },
        },
    },
}

_SECRET_PATTERNS = (
    re.compile(r"Bearer\s+\S{8,}", re.IGNORECASE),
    re.compile(r"\bsk-[A-Za-z0-9_\-]{16,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
)


class ReceiptInvalid(ValueError):
    pass


def _check_cost(cost: dict) -> None:
    usd, basis = cost["usd"], cost["basis"]
    if basis in ("unknown", "subscription") and usd is not None:
        raise ReceiptInvalid(f"cost basis {basis!r} requires usd to be null, not {usd!r}")
    if basis == "priced" and (usd is None or not cost["price_source"] or not cost["price_as_of"]):
        raise ReceiptInvalid("a priced cost needs usd, price_source and price_as_of")
    if basis == "free_local" and usd != 0:
        raise ReceiptInvalid("a free_local cost must be 0")


def _check_mode(receipt: dict) -> None:
    decision_parts = ("provider", "recommendation", "question_set", "policy")
    if receipt["mode"] == "disabled":
        present = [part for part in decision_parts if receipt[part] is not None]
        if present:
            raise ReceiptInvalid(f"a disabled-mode receipt must not carry {', '.join(present)}")
    else:
        absent = [part for part in decision_parts if receipt[part] is None]
        if absent:
            raise ReceiptInvalid(f"{receipt['mode']} mode needs {', '.join(absent)}")


def validate_receipt(receipt: dict) -> None:
    errors = sorted(jsonschema.Draft7Validator(RECEIPT_SCHEMA).iter_errors(receipt), key=lambda e: list(e.path))
    if errors:
        raise ReceiptInvalid(
            "; ".join(f"{'.'.join(str(p) for p in e.path) or '<root>'}: {e.message}" for e in errors)
        )
    _check_cost(receipt["cost"])
    _check_mode(receipt)


def assert_no_secrets(receipt: dict, forbidden: Iterable[str] = ()) -> None:
    """Fail if the serialized receipt contains a credential-like string or any of the
    supplied literals (for example the unmasked values a masker replaced)."""
    text = json.dumps(receipt, ensure_ascii=False)
    for pattern in _SECRET_PATTERNS:
        if pattern.search(text):
            raise ReceiptInvalid(f"receipt contains a credential-like value ({pattern.pattern})")
    for literal in forbidden:
        if literal and literal in text:
            raise ReceiptInvalid("receipt contains a forbidden literal")


def new_receipt_id() -> str:
    return f"rcpt-{uuid.uuid4().hex}"
