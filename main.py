#!/usr/bin/env python3
"""
dan —— Python AI 智能体助手。

启动：
  python main.py demo    # 演示 DAG + Race 竞速
  python main.py learning-demo  # 演示程序员学习闭环
  python main.py          # 交互式对话（需要 LLM）
  python main.py chat     # 单轮对话快速测试
"""

import asyncio
import os
import signal
import sys

from config import AppConfig
from domain.graph import Node, NodeStatus, NodeType
from domain.memory import ConsolidationConfig, LongTermMemory
from domain.rag import HybridStore
from application.agent import AgentConfig, UnifiedAgent
from application.dag_runtime import GraphConfig, run_dag_plan
from application.learning_coach import LearningCoach
from infrastructure.llm_client import MockLLM, create_llm


# ── 工具 ──

def search_web(params: dict) -> str:
    query = params.get("query", "")
    return f"[搜索] 关于 '{query}' 的结果: Python 协程通过 async/await 实现异步编程，asyncio 是标准库事件循环..."

def recall_memory(params: dict) -> str:
    return "[记忆] 你偏好 Python、函数式风格、常用 asyncio 处理并发"


# ── Demo ──

async def demo():
    print("=" * 50)
    print("dan Demo: DAG + Race Strategy")
    print("=" * 50)

    nodes = [
        Node(id="n1", type=NodeType.TOOL, tool_name="search_web",
             params={"query": "Python asyncio best practice"},
             name="搜索 asyncio 最佳实践", race_group="search"),
        Node(id="n2", type=NodeType.TOOL, tool_name="search_web",
             params={"query": "Python asyncio tutorial"},
             name="搜索 asyncio 教程（竞速）", race_group="search"),
        Node(id="n3", type=NodeType.TOOL, tool_name="recall_memory",
             params={"query": "Python async"}, name="检索记忆"),
        Node(id="n4", type=NodeType.AGGREGATE, name="汇总结果",
             depends_on=["n1", "n2", "n3"]),
    ]

    tools = {"search_web": search_web, "recall_memory": recall_memory}

    print("\n[TaskGraph]")
    print(f"  Nodes: {len(nodes)}, RaceGroup: n1 vs n2")
    for n in nodes:
        deps = f" (deps: {n.depends_on})" if n.depends_on else ""
        race = f" [race: {n.race_group}]" if n.race_group else ""
        print(f"  {n.id}: {n.name}{deps}{race}")

    print("\n[Executing DAG...]")
    result = await run_dag_plan(nodes, tools, max_parallel=3, enable_racing=True)

    print(f"\n[Result] {len(result.observations)} observations, interrupted={result.interrupted}")
    for nid, nr in result.node_results.items():
        icon = "[OK]" if nr.status == NodeStatus.DONE else "[SKIP]" if nr.status == NodeStatus.SKIPPED else "[FAIL]"
        detail = (nr.result or nr.error)[:70]
        print(f"  {icon} {nid} ({nr.status.value}): {detail}")

    from domain.graph import TaskGraph
    print(f"\n[Graph]\n{TaskGraph.from_nodes(nodes).summary()}")


def learning_demo():
    """离线演示：计划 → 练习 → 笔记 → 评估 → 下一步。"""
    coach = LearningCoach()
    plan = coach.create_plan(
        "demo-user", "10 天入门 Python AI Agent", days=10,
        level="beginner", daily_minutes=120,
    )
    print("=" * 56)
    print("dan Learning Coach Demo: 学习与成长闭环")
    print("=" * 56)
    print("\n[1. 制定计划]")
    for task in plan.tasks[:3]:
        print(f"  Day {task.day} {task.topic}: {task.objective}")
    print("  ...")

    print("\n[2. 完成练习 + 3. 沉淀笔记]")
    task = coach.complete_task(
        "demo-user", "day-1", 80,
        "函数要有明确输入、返回值，并用小例子验证边界条件。",
    )
    print(f"  [OK] {task.id} {task.topic}, score={task.score}")

    print("\n[4. 掌握度评估 + 5. 推荐下一步]")
    dashboard = coach.dashboard("demo-user")
    print(f"  进度: {dashboard['completed']}/{dashboard['total']} ({dashboard['progress_percent']}%)")
    print(f"  已沉淀笔记: {dashboard['notes']} 条")
    print(f"  平均掌握度: {dashboard['average_mastery_percent']}%")
    for action in dashboard["next_actions"]:
        print(f"  - {action}")


# ── 交互模式 ──

def build_agent():
    """构建 Agent，自动检测 LLM 配置。"""
    cfg = AppConfig.from_env()

    # 创建 LLM（有 Key 用真实，没有用 Mock）
    llm = create_llm(api_key=cfg.llm.api_key, model=cfg.llm.model, api_url=cfg.llm.api_url)

    agent = UnifiedAgent(AgentConfig(
        llm_model=llm.model,
        top_k_rag=cfg.rag.top_k,
        top_k_memory=cfg.memory.long_term_top_k,
    ))
    agent.set_llm(llm)
    agent.register_tool("search_web", search_web)
    agent.register_tool("recall_memory", recall_memory)
    return agent, llm


async def interactive():
    agent, llm = build_agent()

    print("=" * 50)
    print(f"dan 交互模式  [{llm.model}]")
    print("=" * 50)
    print("试试问:")
    print("  - Python asyncio 怎么用？")
    print("  - 什么是 DAG？")
    print("  - 什么是 RAG 检索增强生成？")
    print("  - 记忆系统怎么设计？")
    print("输入 'quit' 退出\n")

    while True:
        try:
            msg = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if msg.lower() in ("quit", "exit", "q"):
            break
        if not msg:
            continue

        print()
        async for event in agent.chat_stream("user-1", msg):
            if event.type == "context_ready":
                print(f"  [context: {event.data['sources']} sources]")
            elif event.type == "plan_ready":
                print(f"  [plan: {event.data['nodes']} nodes]")
            elif event.type == "done":
                print(f"  {event.data['answer']}")
                print()


async def chat_once():
    """单轮对话：python main.py chat"""
    agent, llm = build_agent()

    questions = [
        "Python asyncio 和 threading 的区别是什么？",
        "什么是 DAG 有向无环图？",
        "RAG 检索增强生成是怎么工作的？",
    ]
    print(f"dan 单轮测试 [{llm.model}]\n")
    for q in questions:
        print(f"Q: {q}")
        async for event in agent.chat_stream("user-1", q):
            if event.type == "done":
                print(f"A: {event.data['answer'][:300]}...")
                print()


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""

    if cmd == "demo":
        asyncio.run(demo())
    elif cmd == "learning-demo":
        learning_demo()
    elif cmd == "chat":
        asyncio.run(chat_once())
    else:
        asyncio.run(interactive())


if __name__ == "__main__":
    def _shutdown(sig, frame):
        print("\nShutting down...")
        sys.exit(0)
    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)
    main()
