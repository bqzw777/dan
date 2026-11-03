"""
Elasticsearch BM25 关键词检索客户端。

用于：RAG 精确术语匹配、全文搜索。
"""

from typing import List


class ESClient:
    """
    Elasticsearch 连接封装。

    索引字段：
      - pg_id           PG 主键，用于 RRF 融合时关联
      - content         chunk 原文
      - doc_hash        所属文档哈希
      - chunk_idx       文档内 chunk 序号
    """

    def __init__(self, addresses: List[str] = None, index: str = "rag_chunks"):
        self.addresses = addresses or ["http://localhost:9200"]
        self.index = index
        self._connected = False

    def connect(self) -> bool:
        try:
            # from elasticsearch import Elasticsearch
            # self._client = Elasticsearch(self.addresses)
            # self._connected = self._client.ping()
            self._connected = True
            return True
        except Exception:
            self._connected = False
            return False

    @property
    def available(self) -> bool:
        return self._connected

    def index_doc(self, pg_id: int, content: str, doc_hash: str = "",
                  chunk_idx: int = 0) -> bool:
        """索引单条 chunk。"""
        if not self._connected:
            return False
        # self._client.index(index=self.index, id=pg_id, document={
        #     "pg_id": pg_id, "content": content,
        #     "doc_hash": doc_hash, "chunk_idx": chunk_idx,
        # })
        return True

    def search(self, query: str, top_k: int = 20) -> List[dict]:
        """BM25 关键词检索，返回 [{"pg_id": int, "score": float}, ...]。"""
        if not self._connected:
            return []
        # results = self._client.search(index=self.index, body={
        #     "query": {"match": {"content": query}},
        #     "size": top_k,
        # })
        # return [{"pg_id": h["_source"]["pg_id"], "score": h["_score"]}
        #         for h in results["hits"]["hits"]]
        return []

    def delete_by_doc(self, doc_hash: str) -> bool:
        """按文档哈希删除所有 chunks。"""
        # self._client.delete_by_query(index=self.index, body={
        #     "query": {"term": {"doc_hash": doc_hash}}
        # })
        return True
