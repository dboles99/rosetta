"""Rosetta canonical decision cache: pure key, entry and validity rules (no storage, no I/O).

"Same meaning in different formatting" shares a key; any change of content does not.
The key covers exactly what a provider is shown, after Rosetta canonicalisation: sorted
JSON keys, LF line endings and Unicode NFC. It deliberately does NOT normalise internal
or trailing whitespace (it can carry meaning, e.g. in code) and never uses text
similarity: near-identical items with opposite answers are common (a near-miss budget,
a corrupted Rosetta artifact). Evidence timestamps are excluded from the key; freshness
is enforced by the entry's expiry instead. Question wording, provider, served model and
policy version are part of the key, so a change to any of them is a miss.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta

from ..hashing import sha256_text
from .answers import AnswerBatch, ChoiceAnswer, NoulAnswer, ScoreAnswer, validate_batch
from .contracts import CONTRACT_VERSION, QuestionSet, canonical_json
from .state import DecisionState, wire_state

CACHE_KEY_VERSION = "1"
MAX_UNVERSIONED_TTL = timedelta(hours=24)
_VERSIONED = re.compile(r"\d+\.\d+\.\d+")


@dataclass(frozen=True)
class CacheScope:
    provider: str
    served_model: str
    policy_id: str
    policy_version: str
    ttl: timedelta

    def __post_init__(self) -> None:
        if self.ttl <= timedelta(0):
            raise ValueError("ttl must be positive")
        if not _VERSIONED.search(self.served_model) and self.ttl > MAX_UNVERSIONED_TTL:
            raise ValueError(f"served model {self.served_model!r} reports no version, so drift is undetectable; "
                             f"ttl may not exceed {MAX_UNVERSIONED_TTL}")


def _normalise(value):
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value.replace("\r\n", "\n").replace("\r", "\n"))
    if isinstance(value, dict):
        return {key: _normalise(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalise(item) for item in value]
    return value


def _content(state: DecisionState) -> dict:
    wire = wire_state(state)
    for item in wire["evidence"].values():
        item.pop("retrieved_at", None)
    return {
        "schema_version": state.schema_version,
        "route_contracts": [route.contract_digest for route in state.eligible_routes],
        "wire": _normalise(wire),
    }


def decision_cache_key(state: DecisionState, qset: QuestionSet, scope: CacheScope) -> str:
    return sha256_text(canonical_json({
        "key_version": CACHE_KEY_VERSION,
        "contract_version": CONTRACT_VERSION,
        "content": _content(state),
        "question_set": qset.content_hash(),
        "provider": scope.provider,
        "served_model": scope.served_model,
        "policy": [scope.policy_id, scope.policy_version],
    }))


def _answer_json(answer) -> dict:
    kind = {NoulAnswer: "noul", ChoiceAnswer: "choice", ScoreAnswer: "score"}[type(answer)]
    data = asdict(answer)
    if kind == "score" and data["probabilities"] is not None:
        data["probabilities"] = list(data["probabilities"])
    return {"type": kind, **data}


def _answer_from(data: dict):
    data = dict(data)
    kind = data.pop("type")
    if kind == "noul":
        return NoulAnswer(**data)
    if kind == "choice":
        return ChoiceAnswer(**data)
    if data.get("probabilities") is not None:
        data["probabilities"] = tuple(data["probabilities"])
    return ScoreAnswer(**data)


def make_entry(state: DecisionState, qset: QuestionSet, scope: CacheScope, batch: AnswerBatch, *,
               now: datetime, evidence_expires_at: datetime, source_receipt_id: str) -> dict:
    """Only validated answers from the expected served model are cacheable."""
    if batch.served_model != scope.served_model:
        raise ValueError(f"answers came from {batch.served_model!r}, cache scope expects {scope.served_model!r}")
    violations = validate_batch(batch, qset)
    if violations:
        raise ValueError(f"refusing to cache invalid answers: {[v.code for v in violations]}")
    expires_at = min(now + scope.ttl, evidence_expires_at)
    return {
        "key_version": CACHE_KEY_VERSION,
        "key": decision_cache_key(state, qset, scope),
        "created_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
        "provider": scope.provider,
        "requested_model": batch.requested_model,
        "served_model": batch.served_model,
        "question_set": {"set_id": qset.set_id, "version": qset.version, "hash": qset.content_hash()},
        "policy": {"policy_id": scope.policy_id, "version": scope.policy_version},
        "answers": {qid: _answer_json(answer) for qid, answer in batch.answers.items()},
        "original_input_tokens": batch.usage_input_tokens,
        "source_receipt_id": source_receipt_id,
    }


def entry_usable(entry: dict, key: str, now: datetime, scope: CacheScope) -> tuple[bool, str]:
    if entry.get("key_version") != CACHE_KEY_VERSION:
        return False, "KEY_VERSION"
    if entry.get("key") != key:
        return False, "KEY_MISMATCH"
    if entry.get("served_model") != scope.served_model:
        return False, "MODEL_CHANGED"
    if now >= datetime.fromisoformat(entry["expires_at"]):
        return False, "EXPIRED"
    return True, "HIT"


def answers_from_entry(entry: dict) -> AnswerBatch:
    return AnswerBatch(
        provider=entry["provider"],
        requested_model=entry["requested_model"],
        served_model=entry["served_model"],
        answers={qid: _answer_from(data) for qid, data in entry["answers"].items()},
        usage_input_tokens=0,
        extras={"cache": "hit", "cache_key": entry["key"], "source_receipt_id": entry["source_receipt_id"]},
    )
