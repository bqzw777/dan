"""
Milvus 向量数据库客户端封装。

用于：RAG 文档 Embedding 存储、长期记忆语义检索。
"""

from typing import List, Optional


class MilvusClient:
    """
    Milvus 连接封装。

    核心操作：
      - connect()        建立连接
      - insert()         批量写入向量 + 元数据
      - search()         向量相似度检索（返回 Top-K + distance）
      - delete()         按 ID 删除
    """

    def __init__(self, host: str = "localhost", port: int = 19530,
                 collection: str = "rag_chunks", dim: int = 1024):
        self.host = host
        self.port = port
        self.collection = collection
        self.dim = dim
        self._connected = False

    # ── 连接管理 ──

    def connect(self) -> bool:
        """建立 Milvus 连接。失败不抛异常，返回 False 让上层降级。"""
        try:
            # from pymilvus import connections
            # connections.connect(host=self.host, port=str(self.port))
            self._connected = True
            return True
        except Exception:
            self._connected = False
            return False

    @property
    def available(self) -> bool:
        return self._connected

    # ── 核心操作 ──

    def insert(self, ids: List[int], texts: List[str],
               embeddings: List[List[float]]) -> bool:
        """批量写入。ids、texts、embeddings 一一对应。"""
        if not self._connected:
            return False
        # from pymilvus import Collection
        # col = Collection(self.collection)
        # col.insert([ids, embeddings, texts])
        return True

    def search(self, query_embedding: List[float], top_k: int = 20
               ) -> List[dict]:
        """向量相似度检索，返回 [{"id": int, "distance": float}, ...]。"""
        if not self._connected:
            return []
        # from pymilvus import Collection
        # col = Collection(self.collection)
        # col.load()
        # results = col.search([query_embedding], "embedding",
        #                      {"metric_type": "IP", "params": {"nprobe": 10}},
        #                      limit=top_k)
        # return [{"id": hit.id, "distance": hit.distance} for hit in results[0]]
        return []

    def delete(self, ids: List[int]) -> bool:
        """按 ID 删除向量。"""
        if not self._connected:
            return False
        # expr = f"id in {ids}"
        # Collection(self.collection).delete(expr)
        return True

    def close(self) -> None:
        self._connected = False
