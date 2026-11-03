"""
LLM 客户端 —— 支持 OpenAI / Ollama / DeepSeek 等兼容 API。
零依赖：纯 httpx + json，或者用标准库 urllib。
"""

import json
import os
import urllib.request
from typing import List, Optional


class LLMClient:
    """最小的 LLM 客户端，支持任何 OpenAI 兼容 API。"""

    def __init__(
        self,
        api_url: str = "",
        api_key: str = "",
        model: str = "gpt-4o",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ):
        self.api_url = api_url or os.getenv("LLM_API_URL", "https://api.openai.com/v1")
        self.api_key = api_key or os.getenv("LLM_API_KEY", "")
        self.model = model or os.getenv("LLM_MODEL", "gpt-4o")
        self.temperature = temperature
        self.max_tokens = max_tokens

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def chat(self, prompt: str, system: str = "") -> str:
        """发送 Chat Completion 请求。"""
        if not self.available:
            return ""

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        body = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        url = self.api_url.rstrip("/")
        if not url.endswith("/chat/completions"):
            url += "/chat/completions"

        try:
            data_bytes = json.dumps(body, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data_bytes,
                headers={
                    "Content-Type": "application/json; charset=utf-8",
                    "Authorization": f"Bearer {self.api_key}",
                },
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            return f"[LLM Error: {e}]"


class MockLLM:
    """模拟 LLM —— 没有 API Key 时的 fallback。"""

    def __init__(self):
        self.model = "mock"

    @property
    def available(self):
        return True

    def chat(self, prompt: str, system: str = "") -> str:
        return self._mock_answer(prompt)

    def _mock_answer(self, prompt: str) -> str:
        """基于关键词的简单模板回答，至少能让 Demo 跑起来。"""
        p = prompt.lower()

        if "python" in p and ("async" in p or "asyncio" in p):
            return """Python asyncio 的核心是事件循环（event loop）。

关键概念：
1. async/await —— 定义和等待协程
2. asyncio.run() —— 启动事件循环
3. asyncio.gather() —— 并发执行多个协程
4. asyncio.create_task() —— 创建后台任务

示例：
```python
import asyncio

async def fetch(url):
    await asyncio.sleep(1)
    return f"Result from {url}"

async def main():
    results = await asyncio.gather(
        fetch("url1"), fetch("url2"), fetch("url3")
    )
    print(results)

asyncio.run(main())
```"""

        if "dag" in p or "拓扑" in p or "并行" in p:
            return """DAG（有向无环图）调度算法的关键是：

1. Kahn 算法：从入度为 0 的节点开始，逐层执行
2. 同层节点互不依赖 → 可以并行执行
3. Race Group：同组的节点竞速，谁先完成用谁的结果
4. 故障恢复：每个节点的状态持久化，中断后从未完成处继续"""

        if "rag" in p or "检索" in p or "召回" in p:
            return """RAG（检索增强生成）的核心流程：

1. 文档清洗 → Chunk 切片（512 tokens，128 overlap）
2. 向量化 → 存入 Milvus
3. 查询时三路召回：
   - 向量检索（Milvus）：找语义相近的
   - 关键词检索（ES BM25）：找精确匹配的
   - 知识图谱（Neo4j）：找关系关联的
4. RRF 融合排序 → 返回最相关的 Top-K"""

        if "记忆" in p or "memory" in p:
            return """记忆系统分为四层：

1. 短期记忆（Redis）：最近 N 轮对话，24h TTL
2. 长期记忆（Milvus）：用户偏好和知识，语义检索
3. 图记忆（Neo4j）：记忆间的 FOLLOWS/SIMILAR_TO 关系
4. 运行时状态：当前任务进度和工具调用历史"""

        return """我是 dan，一个 AI 智能体助手。

我的核心能力：
- DAG 并行调度：把任务拆成节点并行执行
- Hybrid RAG 检索：从向量库+搜索引擎+知识图谱三路找资料
- 四层记忆：记住对话、偏好和知识
- 安全沙箱：在隔离环境中执行代码

你可以问我关于 Python、DAG、RAG、记忆系统的问题。"""


def create_llm(api_key: str = "", model: str = "gpt-4o", api_url: str = "") -> object:
    """工厂函数：有 Key 用真实 LLM，没有用 Mock。"""
    key = api_key or os.getenv("LLM_API_KEY", "")
    if key:
        return LLMClient(api_url=api_url, api_key=key, model=model)
    print("[INFO] 未检测到 LLM_API_KEY，使用 Mock LLM（模板回答）")
    print("[INFO] 设置环境变量 LLM_API_KEY 即可接入真实 LLM")
    return MockLLM()
