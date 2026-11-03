"""
四层记忆系统 —— 短期/长期语义/图记忆/运行时状态。

长期记忆核心特性：
  - Store 写入前自动去重（cosine ≥ DedupThreshold 视为重复）
  - RecallByFilter 按 Schema-driven 过滤做语义召回
  - Consolidate 周期性合并：衰减 → 去重/合并 → 过期淘汰
  - 矛盾治理：Superseded 软删除 + 隔离（Quarantined）
"""

import math
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ───────────────────────── 长期记忆 ─────────────────────────

@dataclass
class MemoryItem:
    id: int
    content: str
    importance: float = 0.5          # 0~1
    embedding: List[float] = field(default_factory=list)
    score: float = 0.0               # 召回综合分（不持久化）
    user_id: str = "legacy"
    category: str = "general"        # identity / preference / fact / episodic
    tags: List[str] = field(default_factory=list)
    slot_hint: str = ""
    created_at: float = 0.0
    last_accessed: float = 0.0
    quarantined: bool = False        # 隔离（软删除）
    superseded: bool = False         # 被新记忆取代
    supersedes: List[int] = field(default_factory=list)


@dataclass
class RecallFilter:
    user_id: str = ""
    categories: List[str] = field(default_factory=list)
    require_tags: List[str] = field(default_factory=list)
    min_score: float = 0.4
    top_k: int = 10
    max_age_hours: int = 0
    include_quarantined: bool = False
    include_superseded: bool = False


@dataclass
class ConsolidationConfig:
    similarity_threshold: float = 0.80   # 合并阈值
    dedup_threshold: float = 0.95        # 去重阈值
    ttl_days: int = 30                   # 过期天数
    decay_rate: float = 0.995            # 每日衰减系数
    min_importance: float = 0.3          # 低于此重要性且超TTL则淘汰
    trigger_interval: int = 5            # 每 N 条新记忆触发合并
    protect_fn: Optional[callable] = None  # 删除保护钩子（图记忆注入）


@dataclass
class ConsolidationResult:
    deduped: int = 0
    merged: int = 0
    expired: int = 0
    delete_ids: List[int] = field(default_factory=list)
    update_items: List[MemoryItem] = field(default_factory=list)


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """余弦相似度。"""
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class LongTermMemory:
    """长期语义记忆 —— embedding 优先，TF 词袋降级。"""

    def __init__(self):
        self.items: List[MemoryItem] = []
        self._next_id = 0
        self._store_count = 0
        self._consolidation_cfg: Optional[ConsolidationConfig] = None

    def set_config(self, cfg: ConsolidationConfig) -> None:
        self._consolidation_cfg = cfg

    @property
    def count(self) -> int:
        return len(self.items)

    # ── 写入 ──

    def store(self, user_id: str, content: str, importance: float = 0.5,
              embedding: List[float] = None, category: str = "general",
              tags: List[str] = None, slot_hint: str = "") -> Tuple[bool, int]:
        """写入长期记忆，自动去重。返回 (是否新增, item_id)。"""
        if embedding is None:
            embedding = []
        if tags is None:
            tags = []

        # Embedding 去重
        if self._consolidation_cfg and embedding:
            for item in self.items:
                if item.user_id != user_id or len(item.embedding) != len(embedding):
                    continue
                sim = cosine_similarity(embedding, item.embedding)
                if sim >= self._consolidation_cfg.dedup_threshold:
                    # 命中：更新重要性 + 分类
                    if importance > item.importance:
                        item.importance = importance
                    item.last_accessed = time.time()
                    if category != "general" and (item.category == "" or item.category == "general"):
                        item.category = category
                    return False, item.id

        now = time.time()
        item = MemoryItem(
            id=self._next_id, content=content, importance=importance,
            embedding=embedding, user_id=user_id, category=category,
            tags=tags, slot_hint=slot_hint, created_at=now, last_accessed=now,
        )
        self.items.append(item)
        self._next_id += 1
        self._store_count += 1
        return True, item.id

    # ── 召回 ──

    def recall(self, user_id: str, query: str, top_k: int = 10,
               query_embedding: List[float] = None) -> List[MemoryItem]:
        return self.recall_by_filter(query, query_embedding, RecallFilter(
            user_id=user_id, top_k=top_k, min_score=0.4,
        ))

    def recall_by_filter(self, query: str, query_embedding: List[float],
                         flt: RecallFilter) -> List[MemoryItem]:
        """Schema-driven 语义召回。"""
        if not flt.user_id or not self.items:
            return []

        threshold = flt.min_score or 0.4
        now = time.time()
        scored = []

        for item in self.items:
            # 多租户隔离
            if item.user_id != flt.user_id:
                continue
            # 隔离/取代过滤
            if item.quarantined and not flt.include_quarantined:
                continue
            if item.superseded and not flt.include_superseded:
                continue
            # 类别过滤
            if flt.categories and item.category not in flt.categories:
                continue
            # 标签过滤
            if flt.require_tags and not all(t in (item.tags or []) for t in flt.require_tags):
                continue
            # 年龄过滤
            if flt.max_age_hours > 0:
                if (now - item.created_at) / 3600 > flt.max_age_hours:
                    continue

            # 相似度计算
            if query_embedding and len(item.embedding) == len(query_embedding):
                sim = cosine_similarity(query_embedding, item.embedding)
            else:
                sim = 0.0  # TF fallback 略

            score = sim * 0.7 + item.importance * 0.3
            if score >= threshold:
                item.last_accessed = now
                item.score = score
                scored.append(item)

        scored.sort(key=lambda x: x.score, reverse=True)
        if flt.top_k > 0 and len(scored) > flt.top_k:
            scored = scored[:flt.top_k]
        return scored

    # ── 合并 ──

    def need_consolidation(self) -> bool:
        if not self._consolidation_cfg:
            return False
        return (self._consolidation_cfg.trigger_interval > 0 and
                self._store_count >= self._consolidation_cfg.trigger_interval)

    def consolidate(self) -> ConsolidationResult:
        """执行记忆合并：衰减 → 去重+合并 → 过期淘汰。"""
        cfg = self._consolidation_cfg
        if not cfg or len(self.items) <= 1:
            return ConsolidationResult()

        result = ConsolidationResult()
        self._store_count = 0
        removed = set()

        # Phase 1: 重要性衰减
        now = time.time()
        for item in self.items:
            days = (now - item.created_at) / 86400
            item.importance *= math.pow(cfg.decay_rate, days)

        # Phase 2: 去重 + 合并
        for i in range(len(self.items)):
            if i in removed:
                continue
            for j in range(i + 1, len(self.items)):
                if j in removed:
                    continue
                sim = self._item_similarity(self.items[i], self.items[j])
                if sim >= cfg.dedup_threshold:
                    # 去重：保留重要性更高的
                    if self.items[j].importance >= self.items[i].importance:
                        removed.add(i)
                        result.delete_ids.append(self.items[i].id)
                    else:
                        removed.add(j)
                        result.delete_ids.append(self.items[j].id)
                    result.deduped += 1
                elif sim >= cfg.similarity_threshold:
                    # 合并
                    merged_item = self._merge_items(self.items[i], self.items[j])
                    self.items[i] = merged_item
                    removed.add(j)
                    result.delete_ids.append(self.items[j].id)
                    result.update_items.append(merged_item)
                    result.merged += 1

        # Phase 3: 过期淘汰
        for i, item in enumerate(self.items):
            if i in removed:
                continue
            days = (now - item.created_at) / 86400
            if cfg.ttl_days > 0 and days > cfg.ttl_days and item.importance < cfg.min_importance:
                removed.add(i)
                result.delete_ids.append(item.id)
                result.expired += 1

        # Phase 4: 保护钩子
        if cfg.protect_fn and result.delete_ids:
            protected = cfg.protect_fn(result.delete_ids)
            if protected:
                prot_set = set(protected)
                result.delete_ids = [x for x in result.delete_ids if x not in prot_set]

        # 重建列表
        self.items = [item for i, item in enumerate(self.items) if i not in removed]
        return result

    def _item_similarity(self, a: MemoryItem, b: MemoryItem) -> float:
        if a.embedding and b.embedding and len(a.embedding) == len(b.embedding):
            return cosine_similarity(a.embedding, b.embedding)
        return 0.0

    def _merge_items(self, a: MemoryItem, b: MemoryItem) -> MemoryItem:
        """合并两条语义相近的记忆。"""
        base, other = (a, b) if a.importance >= b.importance else (b, a)
        base.importance = max(a.importance, b.importance)
        if b.content not in a.content and a.content not in b.content:
            base.content = f"{a.content}；{b.content}"
        elif len(b.content) > len(a.content):
            base.content = b.content
        if a.embedding and b.embedding and len(a.embedding) == len(b.embedding):
            w_a, w_b = a.importance, b.importance
            total = w_a + w_b
            if total > 0:
                base.embedding = [(a.embedding[i] * w_a + b.embedding[i] * w_b) / total
                                  for i in range(len(a.embedding))]
        return base


# ───────────────────────── 短期记忆 ─────────────────────────

class ShortTermMemory:
    """短期会话记忆 —— 最近 N 轮对话，FIFO 淘汰。"""

    def __init__(self, max_turns: int = 20):
        self.max_turns = max_turns
        self.messages: List[Dict[str, str]] = []

    def add(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})
        while len(self.messages) > self.max_turns * 2:  # 每轮一问一答
            self.messages.pop(0)

    def get_recent(self, n: int = 10) -> List[Dict[str, str]]:
        return self.messages[-n:]

    def clear(self) -> None:
        self.messages.clear()


# ───────────────────────── 图记忆 ─────────────────────────

class GraphMemory:
    """
    图增强长期记忆 —— Neo4j Memory Graph 叠加层。

    边类型：FOLLOWS(时序) / SIMILAR_TO(语义) / CAUSES(因果) / BELONGS_TO(话题)
    """

    def __init__(self, ltm: LongTermMemory, sim_threshold: float = 0.7):
        self.ltm = ltm
        self.sim_threshold = sim_threshold
        self.prev_id: int = -1
        self._neo4j = None  # 注入 Neo4j client

    def set_neo4j(self, client) -> None:
        self._neo4j = client

    def neo_available(self) -> bool:
        return self._neo4j is not None

    def store(self, user_id: str, content: str, importance: float = 0.5,
              embedding: List[float] = None) -> Tuple[bool, int]:
        """写入 LTM + 建图节点和边。"""
        added, item_id = self.ltm.store(user_id, content, importance, embedding)

        if added and self.neo_available() and item_id >= 0:
            # 异步建 FOLLOWS 边
            if self.prev_id >= 0:
                self._neo4j.add_edge(self.prev_id, item_id, "FOLLOWS", 1.0)
            # 异步建 SIMILAR_TO 边
            self._link_similar(item_id, embedding)
            self.prev_id = item_id

        return added, item_id

    def _link_similar(self, new_id: int, embedding: List[float]) -> None:
        """找语义相近的已有条目建立 SIMILAR_TO 边。"""
        if not embedding or not self.neo_available():
            return
        recent = self.ltm.items[-50:]  # 只看最近50条
        for old in recent:
            if old.id == new_id or not old.embedding:
                continue
            sim = cosine_similarity(embedding, old.embedding)
            if sim >= self.sim_threshold:
                self._neo4j.add_edge(old.id, new_id, "SIMILAR_TO", sim)

    def recall(self, query: str, top_k: int, query_embedding: List[float] = None) -> List[MemoryItem]:
        """向量召回 + 1-hop 图扩展。"""
        seeds = self.ltm.recall("", query, top_k, query_embedding)
        if not self.neo_available() or not seeds:
            return seeds

        seed_ids = [item.id for item in seeds]
        expanded_ids = self._neo4j.expand_neighbors(seed_ids, hops=1)
        if not expanded_ids:
            return seeds

        id_set = set(seed_ids)
        for eid in expanded_ids:
            if eid in id_set:
                continue
            for item in self.ltm.items:
                if item.id == eid:
                    item.score = 0.45  # 图扩展的稍低分
                    seeds.append(item)
                    id_set.add(eid)
                    break

        seeds.sort(key=lambda x: x.score, reverse=True)
        return seeds[:top_k]

    def consolidate(self) -> ConsolidationResult:
        """图感知合并：保护入度≥3的高中心度节点。"""
        if self.neo_available():
            # 注入保护钩子
            cfg = self.ltm._consolidation_cfg
            if cfg and not cfg.protect_fn:

                def _protect(candidates):
                    return self._neo4j.get_high_centrality(candidates, threshold=3)

                cfg.protect_fn = _protect
                self.ltm.set_config(cfg)
        return self.ltm.consolidate()


# ───────────────────────── 偏好记忆 ─────────────────────────

class PreferenceMemory:
    """用户偏好记忆 —— 稳定的用户级配置（编程语言、框架、风格偏好等）。"""

    def __init__(self):
        self.prefs: Dict[str, Dict[str, Any]] = {}

    def set(self, user_id: str, key: str, value: Any) -> None:
        self.prefs.setdefault(user_id, {})[key] = value

    def get(self, user_id: str, key: str, default: Any = None) -> Any:
        return self.prefs.get(user_id, {}).get(key, default)

    def get_all(self, user_id: str) -> Dict[str, Any]:
        return self.prefs.get(user_id, {})
