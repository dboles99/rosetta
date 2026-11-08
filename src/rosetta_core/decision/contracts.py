"""Versioned question contracts for typed semantic decisions.

A question's ID is a stable handle for code and metrics; its meaning lives in the
instructions and criteria, so any wording, option or order change produces a new
content hash. Provider-specific caps (questions per call, options per choice) are
adapter concerns and are checked by the caller, not here.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping

from ..hashing import sha256_text

CONTRACT_VERSION = "0.1"

_QID_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_VERSION_RE = re.compile(r"^\d+\.\d+(\.\d+)?$")
_OPTION_RE = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")
_MAX_SCORE_LEVELS = 10


class ContractError(ValueError):
    """Raised when a decision contract is malformed."""


class Primitive(str, Enum):
    NOUL = "noul"
    CHOICE = "choice"
    SCORE = "score"


def canonical_json(value) -> str:
    """Deterministic JSON: sorted keys, compact separators, UTF-8 text, no NaN/Infinity."""
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


@dataclass(frozen=True)
class QuestionDef:
    qid: str
    version: str
    primitive: Primitive
    instructions: str
    criteria: Mapping[str, str] | tuple[str, ...] | None = None
    required_state_paths: tuple[str, ...] = ()
    consumed_by: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.qid, str) or not _QID_RE.match(self.qid):
            raise ContractError(f"question id must be snake_case: {self.qid!r}")
        if not isinstance(self.version, str) or not _VERSION_RE.match(self.version):
            raise ContractError(f"{self.qid}: version must look like 1.0 or 1.0.0")
        if not isinstance(self.primitive, Primitive):
            raise ContractError(f"{self.qid}: unknown primitive {self.primitive!r}")
        if not isinstance(self.instructions, str) or not self.instructions.strip():
            raise ContractError(f"{self.qid}: instructions are required")
        if self.primitive is Primitive.CHOICE:
            self._check_choice()
        elif self.primitive is Primitive.SCORE:
            self._check_score()
        else:
            self._check_noul()

    def _check_choice(self) -> None:
        if not isinstance(self.criteria, Mapping) or len(self.criteria) < 2:
            raise ContractError(f"{self.qid}: choice needs at least two options")
        for option, description in self.criteria.items():
            if not isinstance(option, str) or not _OPTION_RE.match(option):
                raise ContractError(f"{self.qid}: invalid option name {option!r}")
            if not isinstance(description, str) or not description.strip():
                raise ContractError(f"{self.qid}: option {option!r} needs a description")

    def _check_score(self) -> None:
        levels = self.criteria
        if not isinstance(levels, tuple) or not 2 <= len(levels) <= _MAX_SCORE_LEVELS:
            raise ContractError(f"{self.qid}: score needs a tuple of 2-{_MAX_SCORE_LEVELS} levels, low to high")
        if any(not isinstance(level, str) or not level.strip() for level in levels):
            raise ContractError(f"{self.qid}: score levels must be non-blank strings")
        if len(set(levels)) != len(levels):
            raise ContractError(f"{self.qid}: score levels must be unique")

    def _check_noul(self) -> None:
        if self.criteria is None:
            return
        if not isinstance(self.criteria, Mapping) or not set(self.criteria) <= {"yes", "no"}:
            raise ContractError(f"{self.qid}: noul criteria may only clarify 'yes' and 'no'")

    @property
    def options(self) -> tuple[str, ...]:
        if self.primitive is not Primitive.CHOICE:
            raise ContractError(f"{self.qid}: only choice questions have options")
        return tuple(self.criteria)

    @property
    def levels(self) -> tuple[str, ...]:
        if self.primitive is not Primitive.SCORE:
            raise ContractError(f"{self.qid}: only score questions have levels")
        return tuple(self.criteria)

    def to_json(self) -> dict:
        if isinstance(self.criteria, Mapping):
            criteria = [[key, value] for key, value in self.criteria.items()]  # order is part of the contract
        elif isinstance(self.criteria, tuple):
            criteria = list(self.criteria)
        else:
            criteria = None
        return {
            "qid": self.qid,
            "version": self.version,
            "primitive": self.primitive.value,
            "instructions": self.instructions,
            "criteria": criteria,
            "required_state_paths": list(self.required_state_paths),
            "consumed_by": self.consumed_by,
        }

    def content_hash(self) -> str:
        return sha256_text(canonical_json(self.to_json()))


@dataclass(frozen=True)
class QuestionSet:
    set_id: str
    version: str
    questions: tuple[QuestionDef, ...]
    _index: dict = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not isinstance(self.set_id, str) or not _QID_RE.match(self.set_id):
            raise ContractError(f"question set id must be snake_case: {self.set_id!r}")
        if not isinstance(self.version, str) or not _VERSION_RE.match(self.version):
            raise ContractError(f"{self.set_id}: version must look like 1.0 or 1.0.0")
        if not self.questions:
            raise ContractError(f"{self.set_id}: a question set needs at least one question")
        index: dict[str, QuestionDef] = {}
        for question in self.questions:
            if question.qid in index:
                raise ContractError(f"{self.set_id}: duplicate question id {question.qid!r}")
            index[question.qid] = question
        object.__setattr__(self, "_index", index)

    @property
    def qids(self) -> tuple[str, ...]:
        return tuple(q.qid for q in self.questions)

    def get(self, qid: str) -> QuestionDef:
        return self._index[qid]

    def __contains__(self, qid: str) -> bool:
        return qid in self._index

    def to_json(self) -> dict:
        return {
            "set_id": self.set_id,
            "version": self.version,
            "questions": [q.to_json() for q in self.questions],
        }

    def content_hash(self) -> str:
        return sha256_text(canonical_json(self.to_json()))
