from application.learning_coach import LearningCoach


def test_learning_loop_updates_progress_mastery_and_notes(tmp_path):
    state_path = tmp_path / "learning.json"
    coach = LearningCoach(state_path)
    plan = coach.create_plan("u1", "学习 Python AI Agent", days=3, daily_minutes=90)

    assert len(plan.tasks) == 3
    assert plan.tasks[0].acceptance

    coach.complete_task("u1", "day-1", 80, "函数应该只做一件事")
    dashboard = coach.dashboard("u1")

    assert dashboard["completed"] == 1
    assert dashboard["progress_percent"] == 33.3
    assert dashboard["average_mastery_percent"] == 80.0
    assert dashboard["notes"] == 1
    assert dashboard["next_actions"]

    restored = LearningCoach(state_path)
    assert restored.get_plan("u1").tasks[0].completed is True


def test_learning_plan_validates_required_fields():
    coach = LearningCoach()
    try:
        coach.create_plan("", "AI Agent")
    except ValueError as exc:
        assert "不能为空" in str(exc)
    else:
        raise AssertionError("expected ValueError")
