from dataclasses import dataclass
from typing import Any

from app.core.enums import SignalSeverity, SubScoreCode


@dataclass(frozen=True)
class Signal:
    code: str
    severity: SignalSeverity
    title: str
    detail: str
    evidence_url: str | None = None

    def to_dict(self, sub_score_code: SubScoreCode) -> dict[str, Any]:
        return {
            "sub_score_code": sub_score_code.value,
            "code": self.code,
            "severity": self.severity.value,
            "title": self.title,
            "detail": self.detail,
            "evidence_url": self.evidence_url,
        }


@dataclass(frozen=True)
class SubScoreResult:
    code: SubScoreCode
    score: int | None  # None means "not enough data" (cold start for this sub-score)
    signals: list[Signal]
