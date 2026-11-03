"""
UnifiedAgent —— AI 智能体主控。

组装 RAG + Memory + DAG Runtime + Sandbox，对外暴露 chat() 流式接口。
"""

import asyncio
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Callable, Dict, List, Optional

from domain.graph import Node, NodeType
from domain.rag import HybridStore
from domain.memory import (GraphMemory, LongTermMemory, RecallFilter,
                           ShortTermMemory, PreferenceMemory)
from domain.sandbox import Sandbox, Validator
from application.dag_runtime import GraphConfig, GraphRuntime, run_dag_plan


@dataclass
class AgentConfig:
    llm_model: str = "gpt-4o"
    llm_api_url: str = ""
    llm_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"
    max_retries: int = 3
    retry_delay_ms: int = 1000
    step_timeout_ms: int = 30000
    max_iterations: int = 10
    top_k_rag: int = 10
    top_k_memory: int = 5


@dataclass
class StreamEvent:
    type: str
    data: Dict[str, Any]
    timestamp: float = 0.0


class UnifiedAgent:
    """AI 智能体主控 —— 接收用户消息，编排 RAG → Memory → Plan → DAG → Response。"""

    def __init__(self, config: AgentConfig = None):
        self.config = config or AgentConfig()

        # 记忆系统
        self.short_term = ShortTermMemory(max_turns=20)
        self.long_term = LongTermMemory()
        self.graph_mem = GraphMemory(self.long_term)
        self.preferences = PreferenceMemory()

        # RAG
        self.rag_store: Optional[HybridStore] = None

        # Sandbox
        self.sandbox: Optional[Sandbox] = None

        # 工具注册表
        self.tools: Dict[str, Any] = {}

        # LLM 客户端（注入）
        self.llm: Optional[Any] = None

    def set_rag(self, store: HybridStore) -> None:
        self.rag_store = store

    def set_sandbox(self, sandbox: Sandbox) -> None:
        self.sandbox = sandbox

    def set_llm(self, llm_client) -> None:
        self.llm = llm_client

    def register_tool(self, name: str, fn: Callable) -> None:
        self.tools[name] = fn

    # ── 核心方法：chat ──

    async def chat(self, user_id: str, message: str,
                   on_event: Callable[[StreamEvent], None] = None) -> str:
        """处理一条用户消息，返回最终回答。"""

        # 1. 装配上下文
        ctx = await self._assemble_context(user_id, message)
        if on_event:
            on_event(StreamEvent("context_ready", {"sources": len(ctx)}))

        # 2. 规划任务图
        plan_nodes = self._plan(message, ctx)
        if on_event:
            on_event(StreamEvent("plan_ready", {"nodes": len(plan_nodes)}))

        # 3. 执行 DAG
        result = await run_dag_plan(
            plan_nodes, self.tools,
            max_parallel=2, enable_racing=True,
            on_event=lambda t, d: on_event(StreamEvent(t, d)) if on_event else None,
        )

        # 4. 生成回答
        answer = await self._generate_answer(message, result.observations, ctx)
        if on_event:
            on_event(StreamEvent("answer_ready", {"length": len(answer)}))

        # 5. 更新记忆
        self._update_memory(user_id, message, answer)

        return answer

    async def chat_stream(self, user_id: str, message: str) -> AsyncIterator[StreamEvent]:
        """流式 chat —— 实时推送各阶段事件。"""
        events = []

        def _collect(event: StreamEvent):
            events.append(event)

        answer = await self.chat(user_id, message, on_event=_collect)
        for e in events:
            yield e
        yield StreamEvent("done", {"answer": answer})

    # ── 上下文装配 ──

    async def _assemble_context(self, user_id: str, message: str) -> str:
        parts = []

        # 短期记忆：最近对话
        recent = self.short_term.get_recent(10)
        if recent:
            lines = ["## 最近对话"]
            for m in recent:
                lines.append(f"{m['role']}: {m['content'][:200]}")
            parts.append("\n".join(lines))

        # 长期记忆：语义召回
        if self.rag_store and self.rag_store.embed_fn:
            query_emb = self.rag_store.embed_fn(message)
            memories = self.long_term.recall_by_filter(message, query_emb, RecallFilter(
                user_id=user_id, top_k=self.config.top_k_memory, min_score=0.4,
            ))
            if memories:
                lines = ["## 相关记忆"]
                for m in memories:
                    lines.append(f"- [{m.category}] {m.content} (importance: {m.importance:.2f})")
                parts.append("\n".join(lines))

        # RAG 检索
        if self.rag_store:
            rag_results = self.rag_store.search(message, self.config.top_k_rag)
            if rag_results:
                lines = ["## 检索到的文档"]
                for i, r in enumerate(rag_results):
                    content = r.parent or r.chunk.content
                    lines.append(f"### 来源{i+1} (score: {r.score:.3f})\n{content[:500]}")
                parts.append("\n".join(lines))

        return "\n\n".join(parts)

    # ── 任务规划 ──

    def _plan(self, message: str, context: str) -> List[Node]:
        """基于用户消息和可用工具生成任务图。"""
        nodes = []
        search_nodes = []
        counter = 0

        def _next_id():
            nonlocal counter
            counter += 1
            return f"n{counter}"

        # 搜索节点
        search_tools = [t for t in self.tools if "search" in t.lower()]
        if search_tools:
            for t in search_tools[:3]:  # 最多 3 个搜索源
                n = Node(
                    id=_next_id(), type=NodeType.TOOL, tool_name=t,
                    params={"query": message},
                    name=f"搜索: {t}",
                    race_group="search" if len(search_tools) > 1 else "",
                )
                search_nodes.append(n)
            nodes.extend(search_nodes)

        # 记忆检索节点
        n_mem = Node(
            id=_next_id(), type=NodeType.TOOL,
            tool_name="recall_memory",
            params={"query": message},
            name="检索相关记忆",
        )
        nodes.append(n_mem)

        # 聚合节点（依赖于所有搜索节点）
        deps = [n.id for n in search_nodes] + [n_mem.id]
        n_agg = Node(
            id=_next_id(), type=NodeType.AGGREGATE,
            name="汇总所有结果",
            depends_on=deps,
        )
        nodes.append(n_agg)

        return nodes

    # ── 生成回答 ──

    async def _generate_answer(self, message: str, observations: List[str],
                                context: str) -> str:
        """基于观察结果生成最终回答。"""
        if not self.llm:
            return f"[未配置 LLM] 检索到 {len(observations)} 条相关信息。"

        prompt = f"""## 上下文
{context[:2000]}

## 工具执行结果
{chr(10).join(observations[:5]) if observations else '无'}

## 用户问题
{message}

请用中文简洁回答。"""
        try:
            result = self.llm.chat(prompt, system="你是 dan，一个 AI 智能体助手。")
            return result if result else "\n\n".join(observations[:3])
        except Exception as e:
            return f"生成回答失败: {e}\n\n" + "\n\n".join(observations[:3])

    # ── 记忆更新 ──

    def _update_memory(self, user_id: str, message: str, answer: str) -> None:
        self.short_term.add("user", message)
        self.short_term.add("assistant", answer)
        # 异步写入长期记忆
        self.graph_mem.store(user_id, f"Q: {message[:100]} → A: {answer[:100]}",
                             importance=0.5)
