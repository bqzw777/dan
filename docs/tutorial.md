# dan 项目教程

> 面向程序员的 Python AI 学习助手原型 · 从零到跑通完整闭环

本文是一份从入门到精通的教程，带你理解并动手运行 `dan` 这个项目。读完你将掌握：

- 项目解决了什么问题、整体如何分层
- 如何用 4 种方式运行它
- 五大核心技术模块（DAG 调度 / 竞速 / RAG / 记忆 / 沙箱）是怎么实现的
- 如何自己动手改造和扩展它

---

## 目录

1. [项目简介](#1-项目简介)
2. [环境准备与快速开始](#2-环境准备与快速开始)
3. [项目架构总览](#3-项目架构总览)
4. [核心模块精讲](#4-核心模块精讲)
   - 4.1 DAG 任务图与拓扑排序
   - 4.2 Race Group 竞速调度
   - 4.3 Hybrid RAG 混合检索
   - 4.4 四层记忆系统
   - 4.5 安全沙箱
   - 4.6 LLM 客户端与 Mock 降级
   - 4.7 学习教练闭环
5. [完整链路走读：一次对话发生了什么](#5-完整链路走读一次对话发生了什么)
6. [动手实践](#6-动手实践)
7. [当前边界与改进方向](#7-当前边界与改进方向)
8. [常见问题 FAQ](#8-常见问题-faq)

---

## 1. 项目简介

`dan` 是一个**面向程序员的 Python AI 学习助手原型**，它把自学 AI/Agent 时的散乱过程，组织成一条闭环：

```
目标拆解 → 学习练习 → 知识沉淀 → 掌握度评估 → 下一步推荐
```

在学习这条"产品闭环"之外，它还内置了一套**智能体（Agent）的技术底座**，用来支撑"规划、检索、记忆、执行"的协同工作：

| 能力 | 说明 |
|------|------|
| DAG 并行调度 | 把任务拆成有依赖关系的节点，按层并行执行 |
| Race Group 竞速 | 同组节点"谁先成功用谁"，失败者被跳过 |
| Hybrid RAG | 向量 + 关键词 + 知识图谱三路检索，RRF 融合排序 |
| 记忆系统 | 短期 / 长期 / 图 / 偏好四层记忆，支持去重、合并、过期 |
| 安全沙箱 | 命令静态校验 + 风险分级 + 容器隔离 + 审计 |

**它刻意保持轻量**：核心 Demo 只用 Python 标准库，不装任何数据库依赖也能离线跑通。Milvus / Elasticsearch / Neo4j / PostgreSQL 目前只是适配器骨架，价值在于验证思路，而非生产可用。

---

## 2. 环境准备与快速开始

### 2.1 前置条件

- Python 3.10+（推荐 3.11/3.12）
- 不需要 API Key，不需要数据库（核心 Demo 零依赖）

### 2.2 克隆 / 进入目录

```powershell
cd D:\AGI\dan
```

### 2.3 四种运行方式

#### 方式 0：学习闭环 Demo（推荐先跑这个）

```powershell
python main.py learning-demo
```

不需要 API Key，会依次演示：生成 10 天 AI Agent 学习计划 → 完成练习 → 沉淀笔记 → 更新掌握度 → 推荐下一步。

#### 方式 1：DAG + 竞速调度 Demo

```powershell
python main.py demo
```

构建 4 个节点：`n1`、`n2` 是两个搜索节点（属于同一 Race Group，First-success-wins），`n3` 是记忆检索，`n4` 是聚合节点（依赖前三个）。

#### 方式 2：交互式对话

```powershell
python main.py
```

没有 `LLM_API_KEY` 时自动使用 Mock LLM，可离线演示。输入 `quit` 退出。

#### 方式 3：单轮对话测试

```powershell
python main.py chat
```

### 2.4 运行测试

```powershell
python -m pip install pytest pytest-asyncio
python -m pytest tests -v
```

### 2.5 接入真实 LLM（可选）

编辑 `.env` 或设置环境变量：

```text
LLM_API_KEY=你的密钥
LLM_API_URL=https://你的兼容接口/v1
LLM_MODEL=你的模型名
```

---

## 3. 项目架构总览

项目采用**分层架构（Layered Architecture）**，核心思想是：**领域层不依赖 LLM、不依赖数据库**。

```text
dan/
├── main.py                         # Demo、交互、单轮对话入口
├── application/                    # 应用服务层（编排）
│   ├── agent.py                    # 上下文 → 规划 → DAG → 回答 → 记忆
│   ├── learning_coach.py           # 计划 → 练习 → 笔记 → 评估 → 推荐
│   └── dag_runtime.py              # 分层并发、竞速、聚合节点执行
├── domain/                         # 领域模型层（纯 Python，无 IO）
│   ├── learning.py                 # 学习计划、任务、笔记、掌握度模型
│   ├── graph.py                    # Node、TaskGraph、Kahn 拓扑排序
│   ├── rag.py                      # HybridStore 与 RRF 融合
│   ├── memory.py                   # 短期/长期/图/偏好记忆模型
│   └── sandbox.py                  # 命令风险规则和本地执行封装
├── infrastructure/                 # 基础设施层（外部依赖适配）
│   ├── llm_client.py               # OpenAI-compatible HTTP 客户端与 Mock
│   ├── platform/                   # Milvus/ES/Neo4j 适配器骨架
│   └── persistence/                # PostgreSQL 仓储占位实现
├── config/                         # .env 与配置 dataclass
├── interfaces/                     # 对外接口（占位）
├── tests/                          # DAG、RAG、记忆、沙箱测试
└── requirements.txt
```

**依赖方向**（重要）：

```
main.py / interfaces
        ↓
   application  (编排逻辑)
        ↓
      domain    (领域模型，最纯净)
        ↑
   infrastructure (外部 IO 适配器，被注入到上层)
```

`domain` 是最内层，`application` 负责编排，`infrastructure` 负责外部 IO，并通过**依赖注入**的方式交给上层使用，而不是让 `domain` 直接 import 数据库客户端。这也是为什么 Demo 可以离线运行。

---

## 4. 核心模块精讲

### 4.1 DAG 任务图与拓扑排序

**文件**：`domain/graph.py`

DAG（有向无环图）把一次复杂任务拆成多个**节点（Node）**，节点之间有依赖关系，通过**拓扑排序**决定执行顺序。

#### 节点类型与状态

```python
class NodeType(str, Enum):
    TOOL = "tool"          # 调用一个外部工具
    SUB_AGENT = "sub_agent"# 调用子 Agent
    THINK = "think"        # 纯推理
    AGGREGATE = "aggregate"# 聚合上游结果

class NodeStatus(str, Enum):
    PENDING = "pending"    # 等待执行
    RUNNING = "running"    # 执行中
    DONE = "done"          # 成功
    FAILED = "failed"      # 失败
    SKIPPED = "skipped"    # 被跳过（竞速中落败）
    CANCELLED = "cancelled"# 被取消
```

#### 核心数据结构：Node

```python
@dataclass
class Node:
    id: str                              # n1, n2, n3...
    type: NodeType = NodeType.TOOL
    name: str = ""                       # Planner 给出的原因
    tool_name: str = ""                  # 工具节点必填
    params: Dict[str, str] = ...         # 传给工具的参数
    depends_on: List[str] = ...          # 依赖的前置节点 id
    race_group: str = ""                 # 同 group = 竞速执行
    status: NodeStatus = NodeStatus.PENDING
    result: str = ""
    error: str = ""
```

#### Kahn 拓扑排序算法

`TaskGraph.topological_levels()` 用 **Kahn 算法** 按层排序，**同层节点互不依赖，可以并行执行**：

```python
def topological_levels(self):
    in_deg = dict(self.in_degree)
    levels = []
    processed = 0
    while True:
        ready = [nid for nid, d in in_deg.items() if d == 0]  # 入度为 0 的节点
        if not ready:
            break
        ready.sort()
        levels.append(ready)
        processed += len(ready)
        for nid in ready:
            in_deg[nid] = -1
            for downstream in self.adj_list.get(nid, []):
                in_deg[downstream] -= 1    # 下游入度减一
    if processed != len(self.nodes):
        return [], "Graph has cycle ..."   # 有环则报错
    return levels, None
```

**关键点**：如果处理完的节点数 ≠ 总节点数，说明图中有环（cycle），直接返回错误——这是 DAG 有效性的核心校验。

---

### 4.2 Race Group 竞速调度

**文件**：`application/dag_runtime.py`

`GraphRuntime` 是真正的调度引擎。它的主循环逻辑：

```python
while True:
    level = self.graph.ready_nodes()   # 取当前入度为 0 的 PENDING 节点
    if not level:
        break
    groups = self._group_by_race(level)  # 按 race_group 分组
    tasks = []
    for g in groups:
        if g.race_group and self.cfg.enable_racing:
            tasks.append(self._race_group(g))   # 同组竞速
        else:
            for nid in g.node_ids:
                tasks.append(self._execute_node(nid))  # 独立并行
    await asyncio.gather(*tasks, return_exceptions=True)
    # 更新下游入度
    for nid in level:
        ...
        self.graph.mark_done(nid)
```

#### 竞速（First-success-wins）的核心

`_race_group` 里，同一 Race Group 的多个节点并发执行，**谁先成功返回，谁就胜出，其余被标记为 `SKIPPED`**：

```python
async def _run_one(nid):
    async with self._sem:
        if race_done.is_set():          # 已有胜者，直接跳过
            self.graph.set_node_status(nid, NodeStatus.SKIPPED)
            return
        success, output = await self._execute_single(nid, race_done)
        async with winner_lock:
            if success and not winner_found:
                winner_found = True
                race_done.set()          # 通知其余任务停止
                self.graph.set_node_result(nid, output)
                self.graph.set_node_status(nid, NodeStatus.DONE)
            elif not winner_found:
                self.graph.set_node_status(nid, NodeStatus.SKIPPED)
```

**为什么要竞速？** 比如同时问两个搜索引擎或两个模型，谁先返回好结果就用谁，降低单点慢/失败的延迟，提高鲁棒性。

---

### 4.3 Hybrid RAG 混合检索

**文件**：`domain/rag.py`

RAG（检索增强生成）解决 LLM 的"知识过时 / 幻觉"问题：先从知识库**检索**相关资料，再喂给 LLM **生成**。

`dan` 的 `HybridStore` 设计了三路检索 + 一路融合：

| 检索路 | 技术 | 找什么 |
|--------|------|--------|
| 向量检索 | Milvus | 语义相近的段落 |
| 关键词检索 | Elasticsearch BM25 | 精确匹配的词 |
| 知识图谱 | Neo4j | 关系关联的实体 |

#### RRF 融合算法

三路结果用 **Reciprocal Rank Fusion（RRF）** 融合，核心公式：

```
RRF score(d) = Σ w_i / (k + rank_i(d))
```

其中 `k = 60` 是平滑常数，向量和关键词权重各 1.0，知识图谱权重默认 0.3。

```python
rrf_scores: Dict[int, float] = {}
for rank, hit in enumerate(milvus_hits):
    pg_id = hit.get("id", rank)
    rrf_scores[pg_id] = rrf_scores.get(pg_id, 0) + 1.0 / (k + rank + 1)
for rank, hit in enumerate(es_hits):
    pg_id = hit.get("pg_id", rank)
    rrf_scores[pg_id] = rrf_scores.get(pg_id, 0) + 1.0 / (k + rank + 1)
# KG 第三路：权重 0.3
if self._kg_ok and self._kg_search:
    for rank, hit in enumerate(kg_hits):
        rrf_scores[pg_id] += self.kg_weight / (k + rank + 1)
```

#### 自动降级

`HybridStore` 会根据可用的服务自动选择模式：

```
Milvus + ES  →  hybrid（混合）
仅 Milvus    →  semantic（语义）
仅 ES        →  keyword（关键词）
都没有       →  unavailable（不可用）
```

这意味着即使没有装任何数据库，代码也能正常运行（只是返回空结果），符合"骨架可离线跑"的设计。

---

### 4.4 四层记忆系统

**文件**：`domain/memory.py`

记忆系统的分层：

| 层 | 类 | 用途 | 特点 |
|----|----|------|------|
| 短期记忆 | `ShortTermMemory` | 最近 N 轮对话 | FIFO 淘汰 |
| 长期记忆 | `LongTermMemory` | 用户知识/偏好 | 语义检索 + 去重 + 合并 + 过期 |
| 图记忆 | `GraphMemory` | 记忆间关系 | FOLLOWS / SIMILAR_TO / CAUSES 边 |
| 偏好记忆 | `PreferenceMemory` | 稳定的用户级配置 | key-value |

#### 长期记忆的核心能力

1. **写入去重**：新记忆与已有记忆的 embedding 余弦相似度 ≥ `dedup_threshold`（0.95）时，视为重复，只更新重要性而不新增。

2. **语义召回**：`recall_by_filter` 用 `Schema-driven` 过滤 + 余弦相似度打分：

```python
score = sim * 0.7 + item.importance * 0.3
```

3. **周期合并（Consolidation）**，四个阶段：
   - **衰减**：重要性按时间指数衰减
   - **去重/合并**：相似度 ≥ 0.95 去重，≥ 0.80 合并
   - **过期淘汰**：超过 TTL 且重要性低于阈值
   - **保护钩子**：图记忆可注入保护函数（如保护高中心度节点）

4. **多租户隔离**：每条记忆带 `user_id`，召回时严格按 `user_id` 过滤，避免不同用户数据串联。

---

### 4.5 安全沙箱

**文件**：`domain/sandbox.py`

沙箱让 Agent 可以在受控环境中执行命令，四层防线：

1. **静态正则校验**：22 条 Block 规则 + 11 条 Warn 规则
2. **风险分级**：`Safe` / `Warn` / `Block`
3. **Docker 隔离**：`--network none --read-only --cap-drop ALL --no-new-privileges`
4. **审计日志**：Kafka 异步推送

#### 校验流程

```python
def exec(self, command, confirm=False, timeout=0):
    validation = self.validator.validate(command)
    if validation.level == RiskLevel.BLOCK:
        # 拒绝执行
        ...
    if validation.level == RiskLevel.WARN and not confirm:
        # 需要确认
        ...
    # 执行 subprocess.run(...)
```

**Block 规则示例**（会直接拒绝）：

- `rm -rf /`（删除根路径）
- `sudo`、`su`（权限提升）
- `$(...)`、反引号（命令替换注入）
- `/etc/passwd`、`~/.ssh`（访问凭证）
- `curl ... http`（网络外联）

**Warn 规则示例**（需 `confirm=True` 才执行）：

- `rm`（删除文件）、`pip install`、`|` 管道、`&&` 命令链等

> 💡 理解设计：静态正则只是第一道防线，真正的隔离靠 Docker 容器。当前项目里 Docker 部分是骨架，本地 `backend="local"` 时会真正调用 `subprocess` 执行——所以**不要在生产环境对不可信命令用 local 后端**。

---

### 4.6 LLM 客户端与 Mock 降级

**文件**：`infrastructure/llm_client.py`

- `LLMClient`：用标准库 `urllib` 实现的最小 OpenAI 兼容客户端，零第三方依赖。
- `MockLLM`：没有 API Key 时的 fallback，基于关键词模板回答，让 Demo 能离线跑。
- `create_llm()`：工厂函数，自动选择真实 / Mock。

```python
def create_llm(api_key="", model="gpt-4o", api_url=""):
    key = api_key or os.getenv("LLM_API_KEY", "")
    if key:
        return LLMClient(api_url=api_url, api_key=key, model=model)
    print("[INFO] 未检测到 LLM_API_KEY，使用 Mock LLM（模板回答）")
    return MockLLM()
```

---

### 4.7 学习教练闭环

**文件**：`application/learning_coach.py` + `domain/learning.py`

`LearningCoach` 是"产品闭环"的服务层，围绕可验收任务维护用户学习状态：

```python
coach = LearningCoach()
plan = coach.create_plan("demo-user", "10 天入门 Python AI Agent", days=10)
coach.complete_task("demo-user", "day-1", 80, "复盘笔记...")
dashboard = coach.dashboard("demo-user")
```

**内置的 AI Agent 学习路线**（`AI_AGENT_PATH`）包含 10 个主题：

1. Python 基础 → 2. 面向对象与类型 → 3. 异常与测试 → 4. 异步编程 → 5. LLM 与 Prompt → 6. RAG → 7. Agent 工具调用 → 8. DAG 调度 → 9. 记忆系统 → 10. 项目交付

每个主题都定义了三要素：

- **objective**（学习目标）
- **practice**（练习任务）
- **acceptance**（验收标准）

#### 掌握度计算（`TopicMastery.record`）

```python
current = score / 100
self.mastery = current if self.attempts == 1 else self.mastery * 0.7 + current * 0.3
```

首次以本次成绩为主，后续用**加权移动平均**（旧值 0.7 + 新值 0.3），避免一次低分把长期积累清空。

#### 下一步推荐逻辑（`recommend_next`）

优先级：复习薄弱项 → 完成下一个待办 → 沉淀笔记 → 综合演示。

---

## 5. 完整链路走读：一次对话发生了什么

在 `application/agent.py` 的 `UnifiedAgent.chat()` 里，一次对话被拆成 5 步：

```python
async def chat(self, user_id, message):
    # 1. 装配上下文（短期记忆 + 长期记忆 + RAG）
    ctx = await self._assemble_context(user_id, message)

    # 2. 规划任务图
    plan_nodes = self._plan(message, ctx)

    # 3. 执行 DAG
    result = await run_dag_plan(plan_nodes, self.tools, max_parallel=2, enable_racing=True)

    # 4. 生成回答
    answer = await self._generate_answer(message, result.observations, ctx)

    # 5. 更新记忆
    self._update_memory(user_id, message, answer)
    return answer
```

各阶段会通过事件流实时推送（`context_ready` / `plan_ready` / `answer_ready` / `done`），`chat_stream()` 就是把这些事件收集后统一 yield 出去。

**数据流图**：

```
用户消息
  ↓
[1] 装配上下文：短期记忆 + 长期语义召回 + RAG 检索 → ctx
  ↓
[2] 规划：搜索节点(可能竞速) + 记忆节点 + 聚合节点 → Node[]
  ↓
[3] 执行：GraphRuntime 按层并行 + 竞速 → observations
  ↓
[4] 生成：prompt(ctx + observations + 问题) → LLM/Mock → answer
  ↓
[5] 记忆：写入短期记忆 + 图记忆(长期)
  ↓
返回 answer
```

---

## 6. 动手实践

学完概念后，试着完成下面的练习，逐步深入：

### 练习 1：看懂 Demo 输出

运行 `python main.py demo`，回答：

- 最终 `n4` 的状态是什么？（应该是 `done`）
- `n1` 和 `n2` 谁赢了竞速？为什么另一个是 `SKIPPED`？
- `TaskGraph.summary()` 打印了几层（level）？每层有哪些节点？

### 练习 2：给 Demo 增加一个依赖节点

修改 `main.py` 的 `demo()`，在 `n4` 之前加一个节点 `n5`，让它依赖 `n3` 的结果（提示：设置 `depends_on=["n3"]`，并让 `n4` 也依赖 `n5`）。观察输出层级的变化。

### 练习 3：新增一个可被 Agent 调用的工具

在 `main.py` 里加一个函数，比如：

```python
def get_time(params: dict) -> str:
    from datetime import datetime
    return f"[时间] {datetime.now().isoformat()}"
```

然后把它注册到 `build_agent()` 里（`agent.register_tool("get_time", get_time)`），并在交互模式里问一个相关问题。

### 练习 4：体验记忆去重

写一个临时脚本，往 `LongTermMemory` 写入两条相似记忆（相同 embedding），观察 `store()` 的返回值和 `count` 是否增长。

### 练习 5：测试沙箱校验

写一个脚本，用 `Validator` 校验以下命令，观察返回的 `RiskLevel`：

- `echo hello`
- `rm -rf /`
- `ls | grep foo`

---

## 7. 当前边界与改进方向

这是原型项目，很多地方是骨架。了解边界，才能知道从哪改进。

**已可运行**：

- DAG 模型、拓扑分层、并发调度、Race Group、聚合节点
- 内存版 RRF / 记忆 / Mock LLM
- 命令静态校验

**部分实现**：

- Agent 规划规则简单（`_plan` 只是"搜索 + 记忆 + 聚合"的固定模板）
- `chat_stream` 是先收集事件再统一产出，不是真正逐 token 流式

**占位 / 未闭环**：

- Milvus、ES、Neo4j、PostgreSQL 生产接入
- Docker / Kafka 完整链路
- 任务快照恢复
- 学习助手目前用规则模板生成 AI Agent 路线，尚未根据岗位 JD、代码仓库、错题动态生成个性化计划

**可选的改进方向**（按难度排序）：

1. 让 `_plan` 支持真正的 LLM 规划（用 LLM 生成节点列表 JSON）
2. 给 `chat_stream` 接上真正的流式 LLM（逐 token yield）
3. 实现一个内存版向量检索，替换 `HybridStore` 的 `_milvus_search`
4. 给学习教练接入 LLM，根据用户错题动态生成练习

---

## 8. 常见问题 FAQ

**Q1：为什么 `python main.py demo` 不用装任何依赖就能跑？**

因为 `main.py` 的 Demo 只用到 `domain` 和 `application` 层的纯 Python 代码，没有 import 任何数据库客户端。`requirements.txt` 里的 pymilvus、elasticsearch 等只在真正接入对应服务时才需要。

**Q2：没有 API Key 会怎样？**

`create_llm()` 会自动降级到 `MockLLM`，用关键词模板回答。交互模式依然可以跑，只是回答是模板式的。

**Q3：为什么 `n4` 聚合节点有时候报 "No successful upstream results"？**

聚合节点只汇总状态为 `DONE` 且 `result` 非空的上游节点。如果竞速组里无人成功，或上游都失败了，聚合就会失败。正常 Demo 中 `n1`/`n2` 至少一个成功，所以不会触发。

**Q4：竞速组里谁算赢？**

第一个**成功**返回（`success=True`）的节点。注意是"成功"而不是"先返回"——一个节点即使先返回但报错了，也不算赢。

**Q5：记忆的 `min_score` 默认 0.4 是什么意思？**

召回时综合分 `score = 相似度 × 0.7 + 重要性 × 0.3`，低于 0.4 的记忆不会返回。这避免了把大量无关记忆塞进上下文。

**Q6：我能把这个项目当生产系统用吗？**

不建议直接用于生产。它是原型，数据库接入是骨架，沙箱的 Docker 隔离也未闭环。适合用来学习 Agent 架构、做面试演示、验证产品思路。
