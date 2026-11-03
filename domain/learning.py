"""程序员学习闭环的领域模型。

这一层只描述学习目标、任务、笔记和掌握度，不依赖 LLM 或数据库。
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Dict, List


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class LearningTask:
    id: str
    day: int
    topic: str
    objective: str
    practice: str
    acceptance: str
    completed: bool = False
    score: int = 0
    reflection: str = ""
    completed_at: str = ""


@dataclass
class KnowledgeNote:
    id: str
    topic: str
    content: str
    source: str = "manual"
    created_at: str = field(default_factory=utc_now)


@dataclass
class TopicMastery:
    topic: str
    attempts: int = 0
    best_score: int = 0
    mastery: float = 0.0
    last_reviewed_at: str = ""

    def record(self, score: int) -> None:
        score = max(0, min(100, int(score)))
        self.attempts += 1
        self.best_score = max(self.best_score, score)
        # 首次以本次成绩为主；后续使用加权移动平均，避免一次低分清空进步。
        current = score / 100
        self.mastery = current if self.attempts == 1 else self.mastery * 0.7 + current * 0.3
        self.last_reviewed_at = utc_now()


@dataclass
class LearningPlan:
    user_id: str
    goal: str
    level: str
    daily_minutes: int
    days: int
    tasks: List[LearningTask] = field(default_factory=list)
    notes: List[KnowledgeNote] = field(default_factory=list)
    mastery: Dict[str, TopicMastery] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)

    @property
    def completed_count(self) -> int:
        return sum(task.completed for task in self.tasks)

    @property
    def progress(self) -> float:
        return self.completed_count / len(self.tasks) if self.tasks else 0.0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "LearningPlan":
        payload = dict(data)
        payload["tasks"] = [LearningTask(**item) for item in data.get("tasks", [])]
        payload["notes"] = [KnowledgeNote(**item) for item in data.get("notes", [])]
        payload["mastery"] = {
            topic: TopicMastery(**item) for topic, item in data.get("mastery", {}).items()
        }
        return cls(**payload)
