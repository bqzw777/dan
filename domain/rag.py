"""
Hybrid RAG 检索引擎 —— Milvus 向量 + ES BM25 + Neo4j 知识图谱 + RRF 融合。

核心公式：RRF score(d) = Σ w_i / (k + rank_i(d))
k=60 为平滑常数，KG 权重默认 0.3，向量和关键词权重各 1.0。
"""

import asyncio
import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class Chunk:
    content: str
    parent_content: str = ""


@dataclass
class HybridResult:
    chunk: Chunk
    score: float
    source: str           # "hybrid" | "semantic" | "keyword" | "unavailable"
    parent: str = ""


@dataclass
class IndexedChunk:
    id: int                # 文档内 chunk idx (0-based)
    pg_id: int             # PostgreSQL 自增 ID
    content: str


class Reranker:
    """LLM listwise 精排接口。"""

    def rerank(self, query: str, results: List[HybridResult], top_k: int) -> List[HybridResult]:
        """子类实现：用 Cross-encoder 或 LLM 对候选列表精排。"""
        if len(results) <= top_k:
            return results
        return sorted(results, key=lambda r: r.score, reverse=True)[:top_k]


class HybridStore:
    """
    混合检索存储：
      - Milvus 语义向量检索
      - Elasticsearch BM25 关键词检索
      - Neo4j 知识图谱实体遍历检索
      - Reciprocal Rank Fusion 三路融合

    自动降级：Milvus+ES→hybrid，仅Milvus→semantic，仅ES→keyword，都不可用→unavailable
    """

    def __init__(
        self,
        milvus_available: bool = False,
        es_available: bool = False,
        kg_available: bool = False,
        rrf_k: int = 60,
        kg_weight: float = 0.3,
        reranker: Optional[Reranker] = None,
    ):
        self._milvus_ok = milvus_available
        self._es_ok = es_available
        self._kg_ok = kg_available
        self.rrf_k = rrf_k
        self.kg_weight = kg_weight
        self.reranker = reranker

        if milvus_available and es_available:
            self.mode = "hybrid"
        elif milvus_available:
            self.mode = "semantic"
        elif es_available:
            self.mode = "keyword"
        else:
            self.mode = "unavailable"

        self.embed_fn: Optional[Callable[[str], List[float]]] = None
        self._milvus_search: Optional[Callable] = None
        self._es_search: Optional[Callable] = None
        self._kg_search: Optional[Callable] = None
        self._chunk_loader: Optional[Callable] = None

        # 内存存储（无 PG 时的 fallback）
        self._chunks: Dict[int, Chunk] = {}
        self._next_id = 1

    # ── 依赖注入 ──

    def set_embed_fn(self, fn: Callable[[str], List[float]]) -> None:
        self.embed_fn = fn

    def set_milvus_search(self, fn: Callable) -> None:
        self._milvus_search = fn

    def set_es_search(self, fn: Callable) -> None:
        self._es_search = fn

    def set_kg_search(self, fn: Callable) -> None:
        self._kg_search = fn

    def set_chunk_loader(self, fn: Callable) -> None:
        self._chunk_loader = fn

    # ── 索引 ──

    def index(self, chunks: List[Chunk], doc_content: str = "") -> str:
        """将 chunks 持久化，返回文档哈希。"""
        doc_hash = hashlib.sha256(doc_content.encode()).hexdigest()[:16]
        indexed = []
        for i, c in enumerate(chunks):
            pg_id = self._next_id
            self._next_id += 1
            self._chunks[pg_id] = c
            indexed.append(IndexedChunk(id=i, pg_id=pg_id, content=c.content))
        return doc_hash

    def delete(self, doc_hash: str) -> None:
        """按 doc_hash 删除文档所有 chunks。"""
        self._chunks.clear()

    # ── 检索 ──

    def search(self, query: str, top_k: int = 10) -> List[HybridResult]:
        """单查询入口。"""
        return self._search_one(query, top_k)

    def search_multi(self, queries: List[str], top_k: int = 10) -> List[HybridResult]:
        """多查询：每条 query 独立 RRF，再跨 query RRF 合并。"""
        if not queries:
            return []
        if len(queries) == 1:
            return self._finalize(queries[0], self._search_one(queries[0], self._rerank_pool(top_k)), top_k)

        pool = self._rerank_pool(top_k)

        async def _run():
            async def _one(q):
                return self._search_one(q, pool)
            return await asyncio.gather(*[_one(q) for q in queries])

        all_results = asyncio.run(_run())

        # 跨查询 RRF 合并（以 chunk content 为聚合键）
        k = self.rrf_k
        merged: Dict[str, HybridResult] = {}
        for results in all_results:
            for rank, hr in enumerate(results):
                key = hr.chunk.content
                if key in merged:
                    merged[key].score += 1.0 / (k + rank + 1)
                    if hr.score > merged[key].score:
                        merged[key] = hr
                else:
                    hr.score = 1.0 / (k + rank + 1)
                    merged[key] = hr

        out = sorted(merged.values(), key=lambda r: r.score, reverse=True)
        if len(out) > pool:
            out = out[:pool]
        return self._finalize(queries[0], out, top_k)

    # ── 内部方法 ──

    def _rerank_pool(self, top_k: int) -> int:
        pool = top_k * 4 if self.reranker else top_k * 2
        return max(pool, 10)

    def _finalize(self, query: str, results: List[HybridResult], top_k: int) -> List[HybridResult]:
        if self.reranker and len(results) > 1:
            results = self.reranker.rerank(query, results, top_k)
        elif len(results) > top_k:
            results = results[:top_k]
        return results

    def _search_one(self, query: str, top_k: int) -> List[HybridResult]:
        if self.mode == "hybrid":
            return self._search_hybrid(query, top_k)
        elif self.mode == "semantic":
            return self._search_semantic(query, top_k)
        elif self.mode == "keyword":
            return self._search_keyword(query, top_k)
        return []

    def _search_hybrid(self, query: str, top_k: int) -> List[HybridResult]:
        """三路 RRF 融合检索。"""
        fetch_k = max(top_k * 2, 10)
        k = self.rrf_k

        # 各路检索（带 fallback）
        milvus_hits = self._milvus_search(query, fetch_k) if self._milvus_search else []
        es_hits = self._es_search(query, fetch_k) if self._es_search else []

        # RRF 累加
        rrf_scores: Dict[int, float] = {}
        for rank, hit in enumerate(milvus_hits):
            pg_id = hit.get("id", rank)
            rrf_scores[pg_id] = rrf_scores.get(pg_id, 0) + 1.0 / (k + rank + 1)
        for rank, hit in enumerate(es_hits):
            pg_id = hit.get("pg_id", rank)
            rrf_scores[pg_id] = rrf_scores.get(pg_id, 0) + 1.0 / (k + rank + 1)

        # KG 第三路
        if self._kg_ok and self._kg_search:
            kg_hits = self._kg_search(query, fetch_k)
            for rank, hit in enumerate(kg_hits):
                pg_id = hit.get("pg_id", 0)
                if pg_id == 0:
                    continue
                rrf_scores[pg_id] = rrf_scores.get(pg_id, 0) + self.kg_weight / (k + rank + 1)

        # 排序
        sorted_ids = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        # 批量取回 chunk 内容
        results = []
        for pg_id, score in sorted_ids:
            chunk = self._chunks.get(pg_id, Chunk(content=f"chunk_{pg_id}"))
            results.append(HybridResult(chunk=chunk, score=score, source="hybrid", parent=chunk.parent_content))
        return results

    def _search_semantic(self, query: str, top_k: int) -> List[HybridResult]:
        if not self._milvus_search:
            return []
        hits = self._milvus_search(query, top_k)
        return [
            HybridResult(
                chunk=self._chunks.get(h.get("id", i), Chunk(content="")),
                score=h.get("distance", 0),
                source="semantic",
            )
            for i, h in enumerate(hits)
        ]

    def _search_keyword(self, query: str, top_k: int) -> List[HybridResult]:
        if not self._es_search:
            return []
        hits = self._es_search(query, top_k)
        return [
            HybridResult(
                chunk=self._chunks.get(h.get("pg_id", i), Chunk(content="")),
                score=h.get("score", 0),
                source="keyword",
            )
            for i, h in enumerate(hits)
        ]
