"""
DAG 任务图领域模型 —— Kahn 算法拓扑排序 + 竞速组并行调度。

将传统串行 ReAct（Thought → Action → Observation）升级为
可并行、可竞速的图结构调度。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class NodeType(str, Enum):
    TOOL = "tool"
    SUB_AGENT = "sub_agent"
    THINK = "think"
    AGGREGATE = "aggregate"


class NodeStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


@dataclass
class Node:
    """任务图中的执行单元 —— 一次工具调用、推理或数据聚合。"""
    id: str                              # n1, n2, n3...
    type: NodeType = NodeType.TOOL
    name: str = ""                       # Planner 给出的原因
    tool_name: str = ""                  # 工具节点必填
    agent_name: str = ""                 # 子 Agent 节点必填
    goal: str = ""                       # 子 Agent 任务目标
    params: Dict[str, str] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)  # 入边：依赖的前置节点
    race_group: str = ""                 # 同 group = 竞速执行（First-success-wins）
    status: NodeStatus = NodeStatus.PENDING
    result: str = ""
    error: str = ""
    retry_count: int = 0


@dataclass
class TaskGraph:
    """有向无环图，通过拓扑排序决定节点执行顺序。"""
    nodes: Dict[str, Node] = field(default_factory=dict)
    adj_list: Dict[str, List[str]] = field(default_factory=dict)   # node → 下游
    in_degree: Dict[str, int] = field(default_factory=dict)        # 入度表
    _levels: Optional[List[List[str]]] = field(default=None, repr=False)

    def add_node(self, node: Node) -> None:
        self.nodes[node.id] = node
        self.adj_list.setdefault(node.id, [])
        self.in_degree[node.id] = 0
        self._levels = None

    def add_edge(self, from_id: str, to_id: str) -> None:
        """to 依赖 from：from 完成后才能执行 to。"""
        if from_id not in self.nodes or to_id not in self.nodes:
            raise ValueError(f"Edge {from_id}→{to_id}: node not found")
        self.adj_list.setdefault(from_id, []).append(to_id)
        self.in_degree[to_id] = self.in_degree.get(to_id, 0) + 1
        self._levels = None

    @classmethod
    def from_nodes(cls, nodes: List[Node]) -> "TaskGraph":
        """从节点列表构建图，自动计算邻接表和入度。"""
        tg = cls()
        for n in nodes:
            tg.add_node(n)
        for n in nodes:
            for dep in n.depends_on:
                if dep in tg.nodes:
                    tg.add_edge(dep, n.id)
        return tg

    def topological_levels(self) -> Tuple[List[List[str]], Optional[str]]:
        """Kahn 算法按层拓扑排序，同层节点无依赖可并行。"""
        if self._levels is not None:
            return self._levels, None

        in_deg = dict(self.in_degree)
        levels = []
        processed = 0

        while True:
            ready = [nid for nid, d in in_deg.items() if d == 0]
            if not ready:
                break
            ready.sort()  # 稳定顺序
            levels.append(ready)
            processed += len(ready)
            for nid in ready:
                in_deg[nid] = -1
                for downstream in self.adj_list.get(nid, []):
                    in_deg[downstream] -= 1

        if processed != len(self.nodes):
            return [], f"Graph has cycle: processed {processed}/{len(self.nodes)}"

        self._levels = levels
        return levels, None

    def ready_nodes(self) -> List[str]:
        """返回当前入度为 0 的 PENDING 节点。"""
        return [
            nid for nid, d in self.in_degree.items()
            if d == 0 and self.nodes[nid].status == NodeStatus.PENDING
        ]

    def mark_done(self, nid: str) -> List[str]:
        """标记节点完成，更新下游入度，返回新就绪节点。"""
        self.in_degree[nid] = -1
        newly_ready = []
        for downstream in self.adj_list.get(nid, []):
            self.in_degree[downstream] -= 1
            if self.in_degree[downstream] == 0 and self.nodes[downstream].status == NodeStatus.PENDING:
                newly_ready.append(downstream)
        return newly_ready

    def set_node_status(self, nid: str, status: NodeStatus) -> None:
        if nid in self.nodes:
            self.nodes[nid].status = status

    def set_node_result(self, nid: str, result: str) -> None:
        if nid in self.nodes:
            self.nodes[nid].result = result

    def set_node_error(self, nid: str, error: str) -> None:
        if nid in self.nodes:
            self.nodes[nid].error = error

    def successful_results(self) -> List[str]:
        return [
            f"[{n.tool_name or n.agent_name}] {n.result}"
            for n in self.nodes.values()
            if n.status == NodeStatus.DONE and n.result
        ]

    def validate(self) -> Optional[str]:
        """检测悬空依赖 + 环。"""
        for n in self.nodes.values():
            for dep in n.depends_on:
                if dep not in self.nodes:
                    return f"Node {n.id} depends on nonexistent {dep}"
        _, err = self.topological_levels()
        return err

    def summary(self) -> str:
        levels, err = self.topological_levels()
        if err:
            return f"Graph invalid: {err}"
        lines = [f"Graph: {len(self.nodes)} nodes, {len(levels)} levels"]
        for i, level in enumerate(levels):
            names = [f"{nid}({self.nodes[nid].tool_name or self.nodes[nid].agent_name})" for nid in level]
            lines.append(f"  L{i}: {', '.join(names)}")
        return "\n".join(lines)
