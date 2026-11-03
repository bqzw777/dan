# dan

面向程序员的 Python AI 学习助手原型：帮助用户完成“目标拆解 → 学习练习 → 知识沉淀 → 掌握度评估 → 下一步推荐”的个人成长闭环。底层包含 DAG 并行调度、Race Group 竞速、Hybrid RAG、记忆治理与命令安全校验。

## 最快运行

项目核心 Demo 只使用 Python 标准库，不需要先安装全部数据库依赖。

```powershell
cd D:\AGI\dan
python main.py demo
```

如果系统无法识别 `python`，请把命令中的 `python` 换成你本机 Python 的完整路径，例如：

```powershell
& "C:\Path\To\python.exe" main.py demo
```

## 四种运行方式

### 0. Learning Demo：程序员学习闭环

```powershell
python main.py learning-demo
```

该演示不需要 API Key，会依次展示：生成 10 天 AI Agent 学习计划、完成练习、保存复盘笔记、更新知识掌握度和推荐下一步。

### 1. Demo：DAG 与竞速调度

```powershell
python main.py demo
```

Demo 构建 4 个节点：

- `n1`、`n2`：两个搜索节点，属于同一个 Race Group，采用 First-success-wins。
- `n3`：记忆检索节点。
- `n4`：聚合节点，依赖前面三个节点并汇总成功结果。

成功时 `n4` 应为 `done`，而不是出现 `Tool '' not found`。

### 2. 交互模式

```powershell
python main.py
```

没有配置 `LLM_API_KEY` 时自动使用 Mock LLM，可以离线演示；输入 `quit` 退出。

### 3. 单轮对话测试

```powershell
python main.py chat
```

## 运行测试

先安装测试依赖：

```powershell
python -m pip install pytest pytest-asyncio
python -m pytest tests -v
```

当前测试文件覆盖 DAG、竞速、RRF、记忆和安全校验。是否“全部通过”应以你本机实际运行输出为准。

## 可选：接入真实 LLM

编辑 `.env` 或设置环境变量：

```text
LLM_API_KEY=你的密钥
LLM_API_URL=https://你的兼容接口/v1
LLM_MODEL=你的模型名
```

不要把包含真实密钥的 `.env` 上传到公开仓库。

## 可选：安装全部基础设施依赖

```powershell
python -m pip install -r requirements.txt
```

注意：Milvus、Elasticsearch、Neo4j 和 PostgreSQL 客户端目前主要是适配器骨架或占位实现。安装依赖不等于已经完成真实数据库闭环。

## 项目结构

```text
dan/
├── main.py                         # Demo、交互、单轮对话入口
├── application/
│   ├── agent.py                    # 上下文 → 规划 → DAG → 回答 → 记忆
│   ├── learning_coach.py           # 计划 → 练习 → 笔记 → 评估 → 推荐
│   └── dag_runtime.py              # 分层并发、竞速、聚合节点执行
├── domain/
│   ├── learning.py                 # 学习计划、任务、笔记、掌握度模型
│   ├── graph.py                    # Node、TaskGraph、Kahn 拓扑排序
│   ├── rag.py                      # HybridStore 与 RRF 融合
│   ├── memory.py                   # 短期/长期/图/偏好记忆模型
│   └── sandbox.py                  # 命令风险规则和本地执行封装
├── infrastructure/
│   ├── llm_client.py               # OpenAI-compatible HTTP 客户端与 Mock
│   ├── platform/                   # Milvus/ES/Neo4j 适配器骨架
│   └── persistence/                # PostgreSQL 仓储占位实现
├── config/                         # .env 与配置 dataclass
├── tests/                          # DAG、RAG、记忆、沙箱测试
└── requirements.txt
```

## 当前真实边界

- 可运行：DAG 模型、拓扑层级、并发调度、Race Group、聚合、内存版 RRF/记忆、Mock LLM、命令静态校验。
- 部分实现：Agent 规划规则简单；`chat_stream` 是先收集事件再统一产出，不是真正逐 token 流式。
- 占位或未闭环：Milvus、ES、Neo4j、PostgreSQL 生产接入，Docker/Kafka 完整链路，任务快照恢复。
- 学习助手当前使用规则模板生成 AI Agent 路线，支持 JSON 状态持久化；尚未实现根据岗位 JD、代码仓库和错题动态生成个性化计划。
