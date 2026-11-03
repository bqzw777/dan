"""测试 RAG 混合检索。"""

from domain.rag import Chunk, HybridResult, HybridStore


class TestHybridStore:
    def test_mode_auto_select(self):
        """自动选择检索模式。"""
        hs = HybridStore(milvus_available=True, es_available=True)
        assert hs.mode == "hybrid"

        hs2 = HybridStore(milvus_available=True, es_available=False)
        assert hs2.mode == "semantic"

        hs3 = HybridStore(milvus_available=False, es_available=True)
        assert hs3.mode == "keyword"

        hs4 = HybridStore(milvus_available=False, es_available=False)
        assert hs4.mode == "unavailable"

    def test_index_and_retrieve(self):
        """索引后能检索到。"""
        hs = HybridStore(milvus_available=True, es_available=True)
        chunks = [
            Chunk(content="Python 是一门动态类型语言"),
            Chunk(content="Go 是一门静态类型语言"),
        ]
        hs.index(chunks, "test doc")

        # 设置模拟召回
        hs._milvus_search = lambda q, k: [{"id": 1}, {"id": 2}]
        hs._es_search = lambda q, k: [{"pg_id": 1}]

        results = hs.search("Python")
        assert len(results) > 0

    def test_rrf_scoring(self):
        """RRF 融合排序：多路命中得分更高。"""
        hs = HybridStore(milvus_available=True, es_available=True, rrf_k=60)
        chunks = [Chunk(content="test chunk")]
        hs.index(chunks)

        # 模拟：chunk1在两路都命中排名第一
        hs._milvus_search = lambda q, k: [{"id": 1}]
        hs._es_search = lambda q, k: [{"pg_id": 1}]

        results = hs.search("test")
        assert len(results) > 0
        # 两路都命中 → 得分 = 2/(60+0+1) = 2/61
        assert results[0].source == "hybrid"


class TestMemory:
    def test_store_and_dedup(self):
        """写入去重。"""
        from domain.memory import LongTermMemory, ConsolidationConfig
        ltm = LongTermMemory()
        ltm.set_config(ConsolidationConfig(dedup_threshold=0.95))

        added1, id1 = ltm.store("user1", "我喜欢 Python", embedding=[1.0, 0.0, 0.0])
        assert added1

        # 相似内容应被去重
        added2, id2 = ltm.store("user1", "我喜欢 Python", embedding=[0.99, 0.01, 0.0])
        assert not added2
        assert id2 == id1

    def test_recall_by_category(self):
        """按分类召回。"""
        from domain.memory import LongTermMemory, RecallFilter
        ltm = LongTermMemory()

        ltm.store("user1", "我是Python开发者", embedding=[1.0, 0.0, 0.0],
                  category="identity")
        ltm.store("user1", "喜欢函数式编程", embedding=[0.0, 1.0, 0.0],
                  category="preference")

        # 用 embedding 做语义召回，只取 identity 类
        results = ltm.recall_by_filter("编程", [1.0, 0.1, 0.0], RecallFilter(
            user_id="user1", categories=["identity"], top_k=10, min_score=0.0,
        ))
        assert len(results) >= 1
        assert all(r.category == "identity" for r in results)

    def test_consolidate_expiry(self):
        """过期淘汰。"""
        import time
        from domain.memory import LongTermMemory, ConsolidationConfig
        ltm = LongTermMemory()
        ltm.set_config(ConsolidationConfig(
            ttl_days=1, min_importance=0.5, decay_rate=1.0,
            trigger_interval=2, dedup_threshold=1.0, similarity_threshold=1.0,
        ))

        # 写入两条低重要性的"老"记忆
        ltm.store("user1", "旧记忆1", importance=0.2,
                  embedding=[1.0, 0.0])
        ltm.store("user1", "旧记忆2", importance=0.1,
                  embedding=[0.0, 1.0])
        # 手动把创建时间改到2天前
        for item in ltm.items:
            item.created_at = time.time() - 2 * 86400

        result = ltm.consolidate()
        assert result.expired >= 2


class TestSandbox:
    def test_block_dangerous_commands(self):
        """危险命令被拦截。"""
        from domain.sandbox import Validator
        v = Validator()

        assert v.validate("rm -rf /").level == "block"
        assert v.validate("sudo ls").level == "block"

    def test_warn_suspicious_commands(self):
        """可疑命令触发警告。"""
        from domain.sandbox import Validator
        v = Validator()

        result = v.validate("pip install requests")
        assert result.level == "warn"

    def test_safe_commands(self):
        """安全命令放行。"""
        from domain.sandbox import Validator
        v = Validator()

        assert v.validate("whoami").level == "safe"
        assert v.validate("pwd").level == "safe"

    def test_exec_safe_command(self):
        """安全沙箱执行。"""
        from domain.sandbox import Sandbox, Validator
        s = Sandbox(Validator())
        result = s.exec("python -c \"print('hello')\"", confirm=True)
        assert result.exit_code == 0
        assert "hello" in result.stdout
