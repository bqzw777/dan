"""
配置系统 —— YAML 加载 + 环境变量注入 + 默认值。

启动时自动加载项目根目录的 .env 文件（如果存在）。
对应原 Go 版 config/config.go 的完整配置结构。
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


def _load_dotenv(path: str = None):
    """加载 .env 文件到 os.environ（不覆盖已存在的环境变量）。"""
    if path is None:
        path = Path(__file__).parent.parent / ".env"
    if not os.path.isfile(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


# 模块加载时自动执行
_load_dotenv()


@dataclass
class LLMConfig:
    api_url: str = ""
    api_key: str = ""
    model: str = "gpt-4o"
    fast_model: str = ""         # 快模型用于规划/重写/精排
    temperature: float = 0.7


@dataclass
class EmbeddingConfig:
    api_url: str = ""
    api_key: str = ""
    model: str = "text-embedding-3-small"


@dataclass
class RAGConfig:
    chunk_size: int = 512
    chunk_overlap: int = 128
    top_k: int = 10
    rrf_constant_k: int = 60
    semantic_weight: float = 0.7
    enable_hybrid_search: bool = True
    milvus_dim: int = 1024
    rewrite_enabled: bool = True
    rewrite_num_queries: int = 3
    rerank_enabled: bool = True
    rerank_preview_len: int = 200


@dataclass
class MemoryConfig:
    short_term_max_turns: int = 20
    long_term_top_k: int = 5
    consolidation_similarity: float = 0.80
    consolidation_dedup: float = 0.95
    consolidation_ttl_days: int = 30
    consolidation_decay_rate: float = 0.995
    consolidation_min_importance: float = 0.3
    consolidation_trigger: int = 5


@dataclass
class HarnessConfig:
    max_retries: int = 3
    retry_delay_ms: int = 1000
    step_timeout_ms: int = 30000
    max_iterations: int = 10


@dataclass
class SandboxConfigData:
    enabled: bool = True
    backend: str = "local"       # "docker" | "local"
    image: str = "ubuntu:22.04"
    timeout_ms: int = 30000
    max_output_bytes: int = 65536
    memory_limit_mb: int = 256
    cpu_percent: int = 50
    max_pids: int = 64
    network_disabled: bool = True
    readonly_rootfs: bool = True
    artifact_host_dir: str = "~/Desktop/agi-artifacts"


@dataclass
class GraphRuntimeConfig:
    max_parallel: int = 2
    race_timeout_ms: int = 30000
    enable_racing: bool = True
    replan_enabled: bool = True
    max_replan: int = 2
    replan_on_failed: bool = True


@dataclass
class AppConfig:
    """应用全局配置 —— 对应 Go 版的 APIConfig。"""
    # 服务器
    server_port: str = "8080"

    # LLM
    llm: LLMConfig = field(default_factory=LLMConfig)

    # Embedding
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)

    # RAG
    rag: RAGConfig = field(default_factory=RAGConfig)

    # 记忆
    memory: MemoryConfig = field(default_factory=MemoryConfig)

    # 容错
    harness: HarnessConfig = field(default_factory=HarnessConfig)

    # 沙箱
    sandbox: SandboxConfigData = field(default_factory=SandboxConfigData)

    # DAG
    graph: GraphRuntimeConfig = field(default_factory=GraphRuntimeConfig)

    # 存储
    milvus_host: str = "localhost"
    milvus_port: int = 19530
    pg_host: str = "localhost"
    pg_port: int = 5432
    pg_user: str = "postgres"
    pg_password: str = ""
    pg_database: str = "dan"
    es_addresses: List[str] = field(default_factory=lambda: ["http://localhost:9200"])
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""
    kg_max_hops: int = 2
    kg_weight: float = 0.3
    kg_enabled: bool = False
    kafka_brokers: List[str] = field(default_factory=list)

    # 安全
    sec_max_command_length: int = 500

    @classmethod
    def from_env(cls) -> "AppConfig":
        """从环境变量加载配置。"""
        cfg = cls()
        cfg.llm.api_key = os.getenv("LLM_API_KEY", "")
        cfg.llm.api_url = os.getenv("LLM_API_URL", "")
        cfg.llm.model = os.getenv("LLM_MODEL", "gpt-4o")
        cfg.embedding.api_key = os.getenv("EMBEDDING_API_KEY", cfg.llm.api_key)
        cfg.server_port = os.getenv("SERVER_PORT", "8080")
        cfg.pg_password = os.getenv("PG_PASSWORD", "")
        cfg.neo4j_password = os.getenv("NEO4J_PASSWORD", "")
        return cfg
