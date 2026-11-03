"""
DAG ReAct Runtime —— 拓扑排序按层并行调度 + Race Strategy 竞速引擎。

核心调度策略：
  - 迭代取 ReadyNodes（入度=0 的 PENDING 节点）作为一层
  - 同 RaceGroup 的节点竞速执行（First-success-wins）
  - 信号量控制最大并行度
  - Plan-and-ReAct 层间重规划
  - 支持 context 取消 + 中断恢复（快照持久化）
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional, Set

from domain.graph import Node, NodeStatus, NodeType, TaskGraph


@dataclass
class GraphConfig:
    max_parallel: int = 2
    race_timeout_ms: int = 30000
    enable_racing: bool = True
    replan_enabled: bool = False
    max_replan: int = 2
    replan_on_failed: bool = False


@dataclass
class NodeResult:
    status: NodeStatus
    result: str = ""
    error: str = ""


@dataclass
class GraphResult:
    observations: List[str] = field(default_factory=list)
    node_results: Dict[str, NodeResult] = field(default_factory=dict)
    interrupted: bool = False
    interrupted_msg: str = ""


@dataclass
class RaceGroup:
    race_group: str
    node_ids: List[str]


class GraphRuntime:
    """
    任务图并行调度执行器。

    使用示例：
        graph = TaskGraph.from_nodes(nodes)
        runtime = GraphRuntime(graph, tools, max_parallel=3)
        result = await runtime.execute()
    """

    def __init__(
        self,
        task_graph: TaskGraph,
        tools: Dict[str, Any] = None,
        cfg: GraphConfig = None,
        on_event: Callable[[str, dict], None] = None,
    ):
        self.graph = task_graph
        self.tools = tools or {}
        self.cfg = cfg or GraphConfig()
        self.on_event = on_event

        # 并发控制
        self._sem = asyncio.Semaphore(self.cfg.max_parallel)

        # 结果收集
        self.results: Dict[str, str] = {}
        self.errors: Dict[str, str] = {}
        self._lock = asyncio.Lock()

    # ── 主入口 ──

    async def execute(self, cancel_event: asyncio.Event = None) -> GraphResult:
        """迭代执行整个任务图。"""
        err = self.graph.validate()
        if err:
            return GraphResult(interrupted=True, interrupted_msg=f"图校验失败: {err}")

        if self.on_event:
            levels, _ = self.graph.topological_levels()
            self.on_event("graph_ready", {"levels": levels})

        layer_idx = 0
        while True:
            if cancel_event and cancel_event.is_set():
                return self._build_interrupted(f"第 {layer_idx} 层执行前被中断")

            # 取当前所有 PENDING 且入度为 0 的节点
            level = self.graph.ready_nodes()
            if not level:
                break

            level.sort()  # 稳定顺序

            # 按 race_group 分组：同组竞速，其余独立并行
            groups = self._group_by_race(level)
            tasks = []
            for g in groups:
                if g.race_group and self.cfg.enable_racing:
                    tasks.append(self._race_group(g))
                else:
                    for nid in g.node_ids:
                        tasks.append(self._execute_node(nid))

            await asyncio.gather(*tasks, return_exceptions=True)

            # 更新下游入度
            for nid in level:
                node = self.graph.nodes.get(nid)
                if node and node.status in (
                    NodeStatus.DONE, NodeStatus.SKIPPED,
                    NodeStatus.FAILED, NodeStatus.CANCELLED,
                ):
                    self.graph.mark_done(nid)

            if cancel_event and cancel_event.is_set():
                return self._build_interrupted(f"第 {layer_idx} 层执行后被中断")

            layer_idx += 1

        return self._build_result()

    # ── 竞速执行 ──

    async def _race_group(self, group: RaceGroup) -> None:
        """同 RaceGroup 的节点竞速执行：首个成功 → 取消其余。"""
        # 创建竞速专用的 cancel event
        race_done = asyncio.Event()
        winner_found = False
        winner_lock = asyncio.Lock()

        async def _run_one(nid: str) -> None:
            nonlocal winner_found
            async with self._sem:
                # 如果已有胜者，跳过
                if race_done.is_set():
                    self.graph.set_node_status(nid, NodeStatus.SKIPPED)
                    return

                try:
                    result = await self._execute_single(nid, race_done)
                except Exception as e:
                    result = (False, str(e))

                success, output = result
                async with winner_lock:
                    if success and not winner_found:
                        winner_found = True
                        race_done.set()  # 通知其余任务停止
                        self.graph.set_node_result(nid, output)
                        self.graph.set_node_status(nid, NodeStatus.DONE)
                        if self.on_event:
                            node = self.graph.nodes[nid]
                            self.on_event("race_won", {
                                "race_group": group.race_group,
                                "winner": nid,
                                "tool": node.tool_name,
                            })
                    elif not winner_found:
                        self.graph.set_node_status(nid, NodeStatus.SKIPPED)

        await asyncio.gather(*[_run_one(nid) for nid in group.node_ids])

        # 如果无人胜出，全部标失败
        if not winner_found:
            for nid in group.node_ids:
                if self.graph.nodes[nid].status == NodeStatus.PENDING:
                    self.graph.set_node_status(nid, NodeStatus.FAILED)

    # ── 单节点执行 ──

    async def _execute_node(self, nid: str) -> None:
        async with self._sem:
            result = await self._execute_single(nid)
            success, output = result
            async with self._lock:
                if success:
                    self.results[nid] = output
                    self.graph.set_node_result(nid, output)
                    self.graph.set_node_status(nid, NodeStatus.DONE)
                else:
                    self.errors[nid] = output
                    self.graph.set_node_error(nid, output)
                    self.graph.set_node_status(nid, NodeStatus.FAILED)

    async def _execute_single(self, nid: str,
                               cancel_event: asyncio.Event = None) -> tuple:
        """执行单个节点，返回 (成功, 输出/错误信息)。"""
        node = self.graph.nodes.get(nid)
        if not node:
            return False, f"Node {nid} not found"

        if self.on_event:
            self.on_event("node_start", {"id": nid, "tool": node.tool_name})

        self.graph.set_node_status(nid, NodeStatus.RUNNING)

        # 聚合节点不是外部工具：直接汇总其上游节点的成功结果。
        if node.type == NodeType.AGGREGATE:
            upstream = []
            for dep_id in node.depends_on:
                dep = self.graph.nodes.get(dep_id)
                if dep and dep.status == NodeStatus.DONE and dep.result:
                    upstream.append(f"[{dep.name or dep.id}] {dep.result}")
            if not upstream:
                return False, "No successful upstream results to aggregate"
            output = "\n".join(upstream)
            if self.on_event:
                self.on_event("node_done", {"id": nid, "tool": "aggregate", "status": "done"})
            return True, output

        tool = self.tools.get(node.tool_name)
        if not tool:
            return False, f"Tool '{node.tool_name}' not found"

        try:
            # 调用工具（支持同步和异步）
            if asyncio.iscoroutinefunction(tool):
                result = await tool(node.params)
            elif callable(tool):
                result = tool(node.params)
            else:
                return False, f"Tool '{node.tool_name}' is not callable"

            result_str = str(result) if result else ""
            if self.on_event:
                self.on_event("node_done", {"id": nid, "tool": node.tool_name, "status": "done"})
            return True, result_str
        except asyncio.CancelledError:
            self.graph.set_node_status(nid, NodeStatus.CANCELLED)
            return False, "Task cancelled"
        except Exception as e:
            if self.on_event:
                self.on_event("node_failed", {"id": nid, "tool": node.tool_name, "error": str(e)})
            return False, str(e)

    # ── 辅助 ──

    def _group_by_race(self, level: List[str]) -> List[RaceGroup]:
        group_map: Dict[str, List[str]] = {}
        no_group = []
        for nid in level:
            node = self.graph.nodes.get(nid)
            if node and node.race_group:
                group_map.setdefault(node.race_group, []).append(nid)
            else:
                no_group.append(nid)

        groups = []
        for rg, ids in group_map.items():
            groups.append(RaceGroup(race_group=rg, node_ids=ids))
        for nid in no_group:
            groups.append(RaceGroup(race_group="", node_ids=[nid]))
        return sorted(groups, key=lambda g: g.race_group)

    def _build_result(self) -> GraphResult:
        observations = self.graph.successful_results()
        node_results = {
            nid: NodeResult(status=n.status, result=n.result, error=n.error)
            for nid, n in self.graph.nodes.items()
        }
        return GraphResult(observations=observations, node_results=node_results)

    def _build_interrupted(self, msg: str) -> GraphResult:
        for n in self.graph.nodes.values():
            if n.status in (NodeStatus.PENDING, NodeStatus.RUNNING):
                n.status = NodeStatus.CANCELLED
        result = self._build_result()
        result.interrupted = True
        result.interrupted_msg = msg
        return result


# ── 便捷函数：串联 Planner → GraphRuntime ──

async def run_dag_plan(
    plan_nodes: List[Node],
    tools: Dict[str, Any],
    max_parallel: int = 2,
    enable_racing: bool = True,
    on_event: Callable = None,
) -> GraphResult:
    """一站式：从 Planner 输出的节点列表直接执行。"""
    graph = TaskGraph.from_nodes(plan_nodes)
    cfg = GraphConfig(max_parallel=max_parallel, enable_racing=enable_racing)
    runtime = GraphRuntime(graph, tools, cfg, on_event)
    return await runtime.execute()
