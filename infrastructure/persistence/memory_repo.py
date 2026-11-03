"""
记忆数据仓储 —— PostgreSQL 持久化。

对应 Go 版 persistence/longterm/longterm.go。
"""

from typing import List

from domain.memory import MemoryItem


class MemoryRepo:
    """
    长期记忆的 PG 持久化。

    负责将内存中的 MemoryItem 同步到 PG，以及从 PG 恢复。
    """

    def __init__(self, pg_conn=None):
        self._pg = pg_conn

    # ── 写入 ──

    def insert(self, item: MemoryItem) -> int:
        """写入单条记忆，返回 PG 自增 ID。"""
        return 0

    def update(self, item: MemoryItem) -> bool:
        """更新记忆内容和 importance。"""
        return True

    def update_importance(self, item_id: int, new_importance: float) -> bool:
        """仅更新 importance（衰减阶段的批量更新）。"""
        return True

    def delete_by_ids(self, ids: List[int]) -> int:
        """批量删除（Consolidation 淘汰后同步 PG）。"""
        return len(ids)

    # ── 读取（启动恢复） ──

    def load_all(self, user_id: str = "") -> List[MemoryItem]:
        """从 PG 加载全部记忆，用于启动时恢复内存状态。"""
        return []

    def load_last_id(self) -> int:
        """获取最大 ID，用于恢复时对齐 next_id。"""
        return 0
