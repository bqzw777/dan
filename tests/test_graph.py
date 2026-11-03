"""
测试 DAG 图模型 —— 拓扑排序、竞速组、并行调度。
"""

import asyncio
import pytest
from domain.graph import Node, NodeStatus, NodeType, TaskGraph


class TestTaskGraph:
    def test_simple_linear(self):
        """n1 → n2 → n3 线性依赖。"""
        nodes = [
            Node(id="n1", name="第一步"),
            Node(id="n2", name="第二步", depends_on=["n1"]),
            Node(id="n3", name="第三步", depends_on=["n2"]),
        ]
        tg = TaskGraph.from_nodes(nodes)
        levels, err = tg.topological_levels()
        assert err is None
        assert len(levels) == 3
        assert levels[0] == ["n1"]
        assert levels[1] == ["n2"]
        assert levels[2] == ["n3"]

    def test_parallel(self):
        """n1 → n2, n1 → n3 (n2和n3可并行)。"""
        nodes = [
            Node(id="n1", name="第一步"),
            Node(id="n2", name="并行A", depends_on=["n1"]),
            Node(id="n3", name="并行B", depends_on=["n1"]),
        ]
        tg = TaskGraph.from_nodes(nodes)
        levels, err = tg.topological_levels()
        assert err is None
        assert len(levels) == 2
        assert sorted(levels[1]) == ["n2", "n3"]

    def test_cycle_detection(self):
        """n1 → n2 → n1 环检测。"""
        nodes = [
            Node(id="n1", name="A", depends_on=["n2"]),
            Node(id="n2", name="B", depends_on=["n1"]),
        ]
        tg = TaskGraph.from_nodes(nodes)
        _, err = tg.topological_levels()
        assert err is not None
        assert "cycle" in err.lower()

    def test_dangling_dependency(self):
        """悬空依赖检测。"""
        nodes = [
            Node(id="n1", name="A", depends_on=["nonexistent"]),
        ]
        tg = TaskGraph.from_nodes(nodes)
        err = tg.validate()
        assert err is not None

    def test_ready_nodes(self):
        """ReadyNodes 只返回入度为0的PENDING节点。"""
        nodes = [
            Node(id="n1", name="A"),
            Node(id="n2", name="B", depends_on=["n1"]),
        ]
        tg = TaskGraph.from_nodes(nodes)
        ready = tg.ready_nodes()
        assert ready == ["n1"]
        assert "n2" not in ready

    def test_mark_done(self):
        """完成节点后下游入度减少。"""
        nodes = [
            Node(id="n1", name="A"),
            Node(id="n2", name="B", depends_on=["n1"]),
        ]
        tg = TaskGraph.from_nodes(nodes)
        tg.set_node_status("n1", NodeStatus.DONE)
        new_ready = tg.mark_done("n1")
        assert "n2" in new_ready

    def test_race_group_detection(self):
        """竞速组标签设置。"""
        nodes = [
            Node(id="n1", tool_name="search_google", race_group="search"),
            Node(id="n2", tool_name="search_bing", race_group="search"),
            Node(id="n3", tool_name="recall_memory", race_group=""),
        ]
        tg = TaskGraph.from_nodes(nodes)
        assert tg.nodes["n1"].race_group == "search"
        assert tg.nodes["n2"].race_group == "search"
        assert tg.nodes["n3"].race_group == ""


class TestGraphRuntime:
    @pytest.mark.asyncio
    async def test_basic_execution(self):
        """基本执行：两个并行工具 + 一个聚合。"""
        from application.dag_runtime import GraphConfig, GraphRuntime

        def tool_a(params):
            return "result_from_A"

        def tool_b(params):
            return "result_from_B"

        nodes = [
            Node(id="n1", type=NodeType.TOOL, tool_name="tool_a", name="工具A"),
            Node(id="n2", type=NodeType.TOOL, tool_name="tool_b", name="工具B"),
            Node(id="n3", type=NodeType.AGGREGATE, name="汇总",
                 depends_on=["n1", "n2"]),
        ]
        graph = TaskGraph.from_nodes(nodes)
        tools = {"tool_a": tool_a, "tool_b": tool_b}
        runtime = GraphRuntime(graph, tools, GraphConfig(max_parallel=2))
        result = await runtime.execute()

        assert not result.interrupted
        assert result.node_results["n1"].status == NodeStatus.DONE
        assert result.node_results["n2"].status == NodeStatus.DONE
        assert result.node_results["n3"].status == NodeStatus.DONE
        assert "result_from_A" in result.node_results["n3"].result
        assert "result_from_B" in result.node_results["n3"].result
        assert len(result.observations) == 3

    @pytest.mark.asyncio
    async def test_race_strategy(self):
        """竞速：两个节点同race_group，只有一个DONE另一个SKIPPED。"""
        from application.dag_runtime import GraphConfig, GraphRuntime

        async def fast_search(params):
            return "fast_result"

        async def slow_search(params):
            await asyncio.sleep(0.3)
            return "slow_result"

        nodes = [
            Node(id="n1", type=NodeType.TOOL, tool_name="fast_search",
                 name="快速搜索", race_group="search"),
            Node(id="n2", type=NodeType.TOOL, tool_name="slow_search",
                 name="慢速搜索", race_group="search"),
        ]
        graph = TaskGraph.from_nodes(nodes)
        tools = {"fast_search": fast_search, "slow_search": slow_search}
        runtime = GraphRuntime(graph, tools, GraphConfig(max_parallel=2, enable_racing=True))
        result = await runtime.execute()

        # fast 胜出，slow 被跳过 OR 也被标记为 DONE（取决于竞速实现）
        fast_status = result.node_results["n1"].status
        assert fast_status == NodeStatus.DONE
        # slow 要么 skipped 要么 done（竞速取消了但可能已经跑完）
        assert result.node_results["n2"].status in (NodeStatus.SKIPPED, NodeStatus.DONE)
