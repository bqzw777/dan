"""
RAG Chunk 数据仓储 —— PostgreSQL 持久化。

对应 Go 版 infrastructure/persistence/ragchunk/ragchunk.go。
"""

from typing import Any, Dict, List, Optional


class RAGChunkRepo:
    """
    RAG Chunk 的 PG 持久化操作。

    核心方法：
      - save(chunk)        写入单条 chunk
      - load_by_ids(ids)   批量按 ID 取回
      - delete_by_doc(hash) 按文档哈希级联删除
    """

    def __init__(self, pg_conn=None):
        self._pg = pg_conn

    # 实际实现需要 psycopg2 连接和建表语句
    # CREATE TABLE IF NOT EXISTS rag_chunks (
    #     id BIGSERIAL PRIMARY KEY,
    #     doc_hash VARCHAR(16),
    #     chunk_idx INT,
    #     content TEXT,
    #     parent_content TEXT,
    #     embedding JSONB,
    #     created_at TIMESTAMP DEFAULT NOW()
    # );

    def save(self, doc_hash: str, chunk_idx: int, content: str,
             parent_content: str = "", embedding_json: str = "") -> Optional[int]:
        """写入单条 chunk，返回自增 ID。"""
        return None

    def load_by_ids(self, ids: List[int]) -> List[Dict[str, Any]]:
        """批量取回 chunks，返回 [{id, content, parent_content}, ...]。"""
        return []

    def delete_by_doc(self, doc_hash: str) -> int:
        """按文档哈希删除所有 chunks，返回删除行数。"""
        return 0
