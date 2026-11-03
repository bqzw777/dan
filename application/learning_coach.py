"""程序员 AI 学习助手：计划、练习、笔记、评估、推荐的闭环服务。"""

import json
from pathlib import Path
from typing import Dict, List, Optional

from domain.learning import KnowledgeNote, LearningPlan, LearningTask, TopicMastery, utc_now


AI_AGENT_PATH = [
    ("Python 基础", "读懂函数、参数、返回值与模块", "写 3 个函数并解释输入输出", "不看答案独立运行，能逐行解释"),
    ("面向对象与类型", "理解类、对象、dataclass 和类型标注", "用 dataclass 建模一个 AgentTask", "能说明类与字典的取舍"),
    ("异常与测试", "会定位异常并用测试保护行为", "为 AgentTask 写正常和异常测试", "测试可运行且包含断言"),
    ("异步编程", "理解协程、事件循环和并发", "用 asyncio.gather 并发执行 3 个任务", "能解释并发为何比串行快"),
    ("LLM 与 Prompt", "理解消息、上下文和结构化输出", "设计一个输出 JSON 学习计划的 Prompt", "能处理模型输出格式错误"),
    ("RAG", "理解切片、召回、融合和生成", "给 5 段文本实现关键词 Top-K 检索", "能解释 RAG 与微调的区别"),
    ("Agent 工具调用", "理解规划、工具、观察和回答", "新增一个可被 Agent 调用的工具", "参数错误时能安全失败"),
    ("DAG 调度", "理解依赖、拓扑排序、竞速和聚合", "修改 dan Demo 增加一个依赖节点", "能画出执行层级并解释结果"),
    ("记忆系统", "区分短期、长期和偏好记忆", "保存并召回一条学习偏好", "不同 user_id 的数据不会串联"),
    ("项目交付", "完成演示、测试、README 和复盘", "录制一次 5 分钟项目讲解", "能回答设计取舍、边界和改进点"),
]


class LearningCoach:
    """围绕可验收任务维护用户学习状态；默认可保存到 JSON。"""

    def __init__(self, state_path: Optional[Path] = None):
        self.state_path = Path(state_path) if state_path else None
        self.plans: Dict[str, LearningPlan] = {}
        self._load()

    def create_plan(self, user_id: str, goal: str, days: int = 10,
                    level: str = "beginner", daily_minutes: int = 120) -> LearningPlan:
        if not user_id.strip() or not goal.strip():
            raise ValueError("user_id 和 goal 不能为空")
        days = max(1, min(30, int(days)))
        daily_minutes = max(20, min(480, int(daily_minutes)))
        topics = self._select_topics(goal)
        tasks: List[LearningTask] = []
        for index in range(days):
            topic, objective, practice, acceptance = topics[index % len(topics)]
            tasks.append(LearningTask(
                id=f"day-{index + 1}", day=index + 1, topic=topic,
                objective=objective, practice=practice, acceptance=acceptance,
            ))
        plan = LearningPlan(
            user_id=user_id, goal=goal, level=level,
            daily_minutes=daily_minutes, days=days, tasks=tasks,
            mastery={topic[0]: TopicMastery(topic=topic[0]) for topic in topics},
        )
        self.plans[user_id] = plan
        self._save()
        return plan

    def complete_task(self, user_id: str, task_id: str, score: int,
                      reflection: str = "") -> LearningTask:
        plan = self.get_plan(user_id)
        task = next((item for item in plan.tasks if item.id == task_id), None)
        if not task:
            raise KeyError(f"任务不存在: {task_id}")
        score = max(0, min(100, int(score)))
        task.completed = True
        task.score = score
        task.reflection = reflection.strip()
        task.completed_at = utc_now()
        plan.mastery.setdefault(task.topic, TopicMastery(task.topic)).record(score)
        if reflection.strip():
            self.add_note(user_id, task.topic, reflection, source=task_id, save=False)
        self._save()
        return task

    def add_note(self, user_id: str, topic: str, content: str,
                 source: str = "manual", save: bool = True) -> KnowledgeNote:
        if not topic.strip() or not content.strip():
            raise ValueError("topic 和 content 不能为空")
        plan = self.get_plan(user_id)
        note = KnowledgeNote(
            id=f"note-{len(plan.notes) + 1}", topic=topic.strip(),
            content=content.strip(), source=source,
        )
        plan.notes.append(note)
        if save:
            self._save()
        return note

    def get_plan(self, user_id: str) -> LearningPlan:
        if user_id not in self.plans:
            raise KeyError("尚未创建学习计划")
        return self.plans[user_id]

    def recommend_next(self, user_id: str) -> List[str]:
        plan = self.get_plan(user_id)
        pending = [task for task in plan.tasks if not task.completed]
        weak = sorted(
            (item for item in plan.mastery.values() if item.attempts),
            key=lambda item: item.mastery,
        )
        actions = []
        if weak and weak[0].mastery < 0.7:
            actions.append(f"复习薄弱项「{weak[0].topic}」，再做一道不看答案的练习")
        if pending:
            actions.append(f"完成 Day {pending[0].day}：{pending[0].practice}")
        if plan.completed_count and len(plan.notes) < plan.completed_count:
            actions.append("把今天的错误原因和正确思路各写一句，沉淀为知识笔记")
        return actions or ["计划已完成：做一次综合项目演示并整理面试复盘"]

    def dashboard(self, user_id: str) -> dict:
        plan = self.get_plan(user_id)
        attempted = [item for item in plan.mastery.values() if item.attempts]
        average = sum(item.mastery for item in attempted) / len(attempted) if attempted else 0.0
        return {
            "goal": plan.goal,
            "completed": plan.completed_count,
            "total": len(plan.tasks),
            "progress_percent": round(plan.progress * 100, 1),
            "average_mastery_percent": round(average * 100, 1),
            "notes": len(plan.notes),
            "next_actions": self.recommend_next(user_id),
        }

    @staticmethod
    def format_plan(plan: LearningPlan) -> str:
        lines = [f"学习目标：{plan.goal}", f"周期：{plan.days} 天，每天 {plan.daily_minutes} 分钟"]
        for task in plan.tasks:
            lines.append(
                f"Day {task.day}｜{task.topic}\n"
                f"  学习：{task.objective}\n  练习：{task.practice}\n  验收：{task.acceptance}"
            )
        return "\n".join(lines)

    @staticmethod
    def _select_topics(goal: str):
        # 当前版本聚焦 AI Agent；后续可由 LLM 根据仓库和岗位 JD 动态生成。
        return AI_AGENT_PATH

    def _load(self) -> None:
        if not self.state_path or not self.state_path.exists():
            return
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            self.plans = {uid: LearningPlan.from_dict(plan) for uid, plan in data.items()}
        except (OSError, ValueError, TypeError):
            self.plans = {}

    def _save(self) -> None:
        if not self.state_path:
            return
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {uid: plan.to_dict() for uid, plan in self.plans.items()}
        temp_path = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
        temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        temp_path.replace(self.state_path)
