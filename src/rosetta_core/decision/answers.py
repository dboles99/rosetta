"""Provider-neutral normalized answers and their validation.

Adapters map each provider's raw reply into these types, preserving the raw reply
elsewhere. Validation treats every value as untrusted. A provider failure is a
`ProviderError`, never a fabricated answer.

Score answers use `position`: a 0-based place on the declared levels (0 = lowest),
possibly fractional. Adapters must convert provider-specific score scales.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping, Union

from .contracts import Primitive, QuestionSet

DEFAULT_SUM_TOLERANCE = 0.02
# A selected option may trail the top probability by rounding noise without the answer
# being inconsistent; beyond this gap the provider contradicted its own distribution.
ARGMAX_TOLERANCE = 1e-3


@dataclass(frozen=True)
class NoulAnswer:
    qid: str
    p_yes: float


@dataclass(frozen=True)
class ChoiceAnswer:
    qid: str
    selected: str
    probabilities: Mapping[str, float] | None
    confidence: float | None


@dataclass(frozen=True)
class ScoreAnswer:
    qid: str
    position: float
    probabilities: tuple[float, ...] | None
    confidence: float | None


Answer = Union[NoulAnswer, ChoiceAnswer, ScoreAnswer]


class ErrorKind(str, Enum):
    TIMEOUT = "TIMEOUT"
    RATE_LIMITED = "RATE_LIMITED"
    UNAVAILABLE = "UNAVAILABLE"
    AUTH = "AUTH"
    QUOTA_EXHAUSTED = "QUOTA_EXHAUSTED"
    INVALID_REQUEST = "INVALID_REQUEST"
    MALFORMED = "MALFORMED"
    CONTRACT_MISMATCH = "CONTRACT_MISMATCH"

    @property
    def retryable(self) -> bool:
        return self in (ErrorKind.TIMEOUT, ErrorKind.RATE_LIMITED, ErrorKind.UNAVAILABLE)


@dataclass(frozen=True)
class ProviderError:
    kind: ErrorKind
    detail: str
    attempts: int = 1
    http_status: int | None = None

    @property
    def retryable(self) -> bool:
        return self.kind.retryable


@dataclass
class AnswerBatch:
    provider: str
    requested_model: str
    served_model: str
    answers: dict[str, Answer]
    raw_ref: str | None = None
    usage_input_tokens: int | None = None
    extras: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Violation:
    qid: str
    code: str
    detail: str = ""


def _is_unit_interval(value) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and 0.0 <= value <= 1.0
    )


def _check_confidence(answer, out: list[Violation]) -> None:
    if answer.confidence is not None and not _is_unit_interval(answer.confidence):
        out.append(Violation(answer.qid, "BAD_CONFIDENCE", repr(answer.confidence)))


def _check_distribution(qid: str, values, out: list[Violation], tolerance: float) -> bool:
    if any(not _is_unit_interval(v) for v in values):
        out.append(Violation(qid, "BAD_DISTRIBUTION", "probability outside [0, 1] or not finite"))
        return False
    if abs(sum(values) - 1.0) > tolerance:
        out.append(Violation(qid, "BAD_DISTRIBUTION", f"sums to {sum(values):.4f}"))
        return False
    return True


def _validate_choice(answer: ChoiceAnswer, options: tuple[str, ...], out: list[Violation], tolerance: float) -> None:
    if answer.selected not in options:
        out.append(Violation(answer.qid, "UNKNOWN_OPTION", repr(answer.selected)))
    probs = answer.probabilities
    if probs is not None:
        unknown = set(probs) - set(options)
        if unknown:
            out.append(Violation(answer.qid, "UNKNOWN_OPTION", ", ".join(sorted(unknown))))
        elif set(probs) != set(options):
            out.append(Violation(answer.qid, "INCOMPLETE_DISTRIBUTION", "not every option has a probability"))
        elif _check_distribution(answer.qid, list(probs.values()), out, tolerance):
            if answer.selected in probs and probs[answer.selected] < max(probs.values()) - ARGMAX_TOLERANCE:
                out.append(Violation(answer.qid, "SELECTED_NOT_ARGMAX", answer.selected))
    _check_confidence(answer, out)


def _validate_score(answer: ScoreAnswer, levels: tuple[str, ...], out: list[Violation], tolerance: float) -> None:
    position = answer.position
    if (
        not isinstance(position, (int, float))
        or isinstance(position, bool)
        or not math.isfinite(position)
        or not 0.0 <= position <= len(levels) - 1
    ):
        out.append(Violation(answer.qid, "BAD_SCORE", repr(position)))
    if answer.probabilities is not None:
        if len(answer.probabilities) != len(levels):
            out.append(Violation(answer.qid, "BAD_DISTRIBUTION", "length differs from number of levels"))
        else:
            _check_distribution(answer.qid, list(answer.probabilities), out, tolerance)
    _check_confidence(answer, out)


def validate_batch(batch: AnswerBatch, qset: QuestionSet, *, sum_tolerance: float = DEFAULT_SUM_TOLERANCE) -> list[Violation]:
    violations: list[Violation] = []
    for qid in batch.answers:
        if qid not in qset:
            violations.append(Violation(qid, "UNEXPECTED_QUESTION"))
    for question in qset.questions:
        answer = batch.answers.get(question.qid)
        if answer is None:
            violations.append(Violation(question.qid, "MISSING"))
            continue
        if question.primitive is Primitive.NOUL and isinstance(answer, NoulAnswer):
            if not _is_unit_interval(answer.p_yes):
                violations.append(Violation(question.qid, "BAD_PROBABILITY", repr(answer.p_yes)))
        elif question.primitive is Primitive.CHOICE and isinstance(answer, ChoiceAnswer):
            _validate_choice(answer, question.options, violations, sum_tolerance)
        elif question.primitive is Primitive.SCORE and isinstance(answer, ScoreAnswer):
            _validate_score(answer, question.levels, violations, sum_tolerance)
        else:
            violations.append(Violation(question.qid, "WRONG_PRIMITIVE", type(answer).__name__))
    return violations
