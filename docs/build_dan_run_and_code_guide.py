from pathlib import Path
import sys
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

sys.path.insert(0, r"D:\AGI\AGI-engine")

from build_7day_learning_guide import (
    set_run_font, add_num_definition, set_num, configure_styles,
    add_heading, add_body, add_bullets, add_callout,
    apply_table_geometry, shade_cell,
)


OUT = Path(__file__).with_name("dan项目运行与代码分析手册.docx")
NAVY = "0B2545"
BLUE = "2E74B5"
MUTED = "5F6670"
LIGHT_BLUE = "E8EEF5"
GOLD = "FFF8E8"
GREEN = "EAF4EA"


def add_code(doc, code):
    table = doc.add_table(rows=1, cols=1)
    apply_table_geometry(table, [9360])
    cell = table.cell(0, 0)
    shade_cell(cell, "F4F6F9")
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1.05
    for index, line in enumerate(code.splitlines()):
        if index:
            p.add_run("\n")
        run = p.add_run(line or " ")
        set_run_font(run, size=8.5, name="Consolas")
    doc.add_paragraph().paragraph_format.space_after = Pt(1)


def add_matrix(doc, headers, rows, widths):
    table = doc.add_table(rows=1, cols=len(headers))
    apply_table_geometry(table, widths)
    for index, header in enumerate(headers):
        cell = table.cell(0, index)
        shade_cell(cell, LIGHT_BLUE)
        p = cell.paragraphs[0]
        p.paragraph_format.space_after = Pt(0)
        run = p.add_run(header)
        set_run_font(run, size=9.5, bold=True, color=NAVY)
    for row in rows:
        cells = table.add_row().cells
        for index, value in enumerate(row):
            p = cells[index].paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.15
            run = p.add_run(value)
            set_run_font(run, size=9, bold=(index == 0), color=NAVY if index == 0 else None)
    apply_table_geometry(table, widths)


def build():
    doc = Document()
    sec = doc.sections[0]
    sec.page_width = Inches(8.5)
    sec.page_height = Inches(11)
    sec.top_margin = Inches(1)
    sec.right_margin = Inches(1)
    sec.bottom_margin = Inches(1)
    sec.left_margin = Inches(1)
    sec.header_distance = Inches(0.492)
    sec.footer_distance = Inches(0.492)
    configure_styles(doc)
    bullet_id = add_num_definition(doc, "bullet", "•")

    header = sec.header.paragraphs[0]
    header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = header.add_run("dan｜运行与代码分析手册")
    set_run_font(run, size=8.5, color=MUTED)
    footer = sec.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = footer.add_run("面试学习版｜以实际代码和运行结果为准")
    set_run_font(run, size=8, color=MUTED)

    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(0)
    run = p.add_run("项目学习手册")
    set_run_font(run, size=10.5, bold=True, color=BLUE)
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(6)
    run = p.add_run("dan：运行方法与代码分析")
    set_run_font(run, size=28, bold=True, color=NAVY)
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(16)
    run = p.add_run("Python AI Agent 原型｜DAG 调度｜Race Group｜Hybrid RAG｜记忆｜安全校验")
    set_run_font(run, size=12.5, color=MUTED)

    add_callout(doc, "先说结论", "离线 Demo 已实际运行成功：n1 搜索成功、n2 竞速跳过、n3 记忆成功、n4 聚合成功。真实 LLM 模式需要网络和有效 API；数据库适配器仍以骨架/占位为主。", GREEN)

    add_heading(doc, "1. 项目是什么", 1)
    add_body(doc, "dan 是一个分层设计的 Python AI Agent 原型。它把用户请求装配上下文、规划为任务节点、构建 DAG、并发执行工具，再生成回答和更新记忆。核心价值是展示 Agent 编排思路，不是完整生产系统。")
    add_matrix(doc, ["层", "目录/文件", "职责"], [
        ("入口", "main.py", "Demo、交互模式、单轮对话，注册示例工具。"),
        ("应用层", "application/agent.py", "串联上下文、规划、DAG、回答与记忆。"),
        ("应用层", "application/dag_runtime.py", "分层调度、并发限制、竞速与聚合。"),
        ("领域层", "domain/graph.py", "Node、状态、邻接表、入度和 Kahn 算法。"),
        ("领域层", "domain/rag.py", "混合检索模式与 RRF 融合。"),
        ("领域层", "domain/memory.py", "短期、长期、图和偏好记忆模型。"),
        ("领域层", "domain/sandbox.py", "静态风险规则、确认和本地执行封装。"),
        ("基础设施", "infrastructure/", "LLM 客户端和数据库/持久化适配器。"),
    ], [1300, 3000, 5060])

    add_heading(doc, "2. 第一次运行：只跑离线 Demo", 1)
    add_body(doc, "这是最适合你当前阶段的运行方式。它不需要 API Key，也不需要 Milvus、ES、Neo4j 或 PostgreSQL。")
    add_code(doc, r"""cd D:\AGI\dan
python main.py demo""")
    add_body(doc, "如果 PowerShell 提示找不到 python，请找到 Python 安装路径，再使用完整路径：")
    add_code(doc, r"""& "C:\Path\To\python.exe" D:\AGI\dan\main.py demo""")
    add_heading(doc, "看到什么才算成功", 2)
    add_bullets(doc, [
        "标题显示 dan Demo: DAG + Race Strategy。",
        "n1/n2 中一个为 done，另一个通常为 skipped，表示竞速只保留一个胜者。",
        "n3 为 done，表示记忆工具执行成功。",
        "n4 为 done，并包含上游成功结果；不能再出现 Tool '' not found。",
        "Graph 显示两层：L0 为检索/记忆，L1 为聚合。",
    ], bullet_id)

    add_heading(doc, "3. 交互模式与真实 LLM", 1)
    add_code(doc, r"""cd D:\AGI\dan
python main.py

# 单轮预设问题
python main.py chat""")
    add_body(doc, "项目启动时读取根目录 `.env`。如果 `LLM_API_KEY` 为空，会使用 Mock LLM；如果存在 Key，会调用 `LLM_API_URL` 指向的 OpenAI-compatible `/chat/completions` 接口。")
    add_code(doc, """LLM_API_KEY=你的密钥
LLM_API_URL=https://你的兼容接口/v1
LLM_MODEL=你的模型名""")
    add_callout(doc, "安全提醒", "不要把真实密钥提交到公开仓库。当前环境的网络请求被沙箱阻止，所以本次只能验证离线 Demo；这不等于接口配置一定错误。", GOLD)

    add_heading(doc, "4. 运行测试", 1)
    add_code(doc, """cd D:\\AGI\\dan
python -m pip install pytest pytest-asyncio
python -m pytest tests -v

# 单独测试
python -m pytest tests/test_graph.py -v
python -m pytest tests/test_rag.py -v""")
    add_body(doc, "当前 Codex 专用 Python 环境没有 pytest，因此本次未能执行 pytest。已执行 `compileall` 通过，并实际运行 Demo 通过。你在本机安装 pytest 后，应保存完整测试输出，再决定是否在简历中写“19个测试全部通过”。")

    add_heading(doc, "5. 一次请求如何流动", 1)
    add_bullets(doc, [
        "main.py：构建 UnifiedAgent，注入 LLM，并注册 search_web、recall_memory。",
        "UnifiedAgent.chat：先 `_assemble_context`，读取最近对话、长期记忆和 RAG 文档。",
        "`_plan`：按工具名称生成搜索节点、记忆节点和聚合节点。",
        "run_dag_plan：把 Node 列表转换成 TaskGraph，并创建 GraphRuntime。",
        "GraphRuntime.execute：循环读取入度为0的 pending 节点；同层并发，同 race_group 竞速。",
        "聚合节点：读取 depends_on 中成功节点的结果并拼接。",
        "`_generate_answer`：把上下文、工具观察和问题交给 LLM。",
        "`_update_memory`：写入短期对话和一条图/长期记忆。",
    ], bullet_id)

    add_heading(doc, "6. DAG 与调度器代码分析", 1)
    add_heading(doc, "Node 与 TaskGraph", 2)
    add_body(doc, "`domain/graph.py` 用 dataclass 表达任务节点。`depends_on` 表示入边，`race_group` 表示等价数据源的竞速组。TaskGraph 保存 nodes、adj_list 和 in_degree。")
    add_bullets(doc, [
        "from_nodes：先加入所有节点，再根据 depends_on 建边。",
        "topological_levels：复制入度表，反复取入度0节点形成层级；处理数不足说明有环。",
        "ready_nodes：运行时只返回入度0且状态为 pending 的节点。",
        "mark_done：把当前节点入度标记为 -1，并减少下游入度。",
    ], bullet_id)
    add_heading(doc, "GraphRuntime", 2)
    add_bullets(doc, [
        "Semaphore 控制 max_parallel，防止同一层无限并发。",
        "`_group_by_race` 把同层节点按 race_group 分组。",
        "`_race_group` 实现 First-success-wins；胜者 done，其余 skipped。",
        "`_execute_single` 区分聚合节点和工具节点；工具支持同步函数和 async 函数。",
        "每层结束后调用 mark_done，释放下游节点。",
    ], bullet_id)

    add_heading(doc, "7. Agent 代码分析", 1)
    add_body(doc, "`application/agent.py` 是用例编排层。它本身不负责底层算法，而是把 RAG、Memory、Planner、Runtime 和 LLM 串起来。")
    add_matrix(doc, ["方法", "作用", "当前边界"], [
        ("chat", "五阶段主流程", "没有重试、超时和真正的循环 ReAct。"),
        ("chat_stream", "输出阶段事件", "先完整执行并收集，再 yield；不是真正实时流。"),
        ("_assemble_context", "装配短期、长期、RAG", "长期语义召回依赖 rag_store 的 embed_fn。"),
        ("_plan", "规则生成 Node", "不是 LLM Planner；按工具名称包含 search 判断。"),
        ("_generate_answer", "调用 LLM", "失败时把错误字符串作为回答返回。"),
        ("_update_memory", "保存会话信息", "写入内存结构，不是数据库持久化。"),
    ], [1900, 2600, 4860])

    add_heading(doc, "8. RAG 代码分析", 1)
    add_body(doc, "`domain/rag.py` 的 HybridStore 是领域逻辑。它通过依赖注入接收 Milvus、ES 和 KG 查询函数，再用 RRF 融合排名。")
    add_bullets(doc, [
        "模式选择：Milvus+ES=hybrid，仅Milvus=semantic，仅ES=keyword，均无=unavailable。",
        "RRF：对各路第 rank 名增加 `1/(k+rank+1)`；KG 再乘 kg_weight。",
        "内存 `_chunks` 用于无 PostgreSQL 时保存内容；这只是进程内数据。",
        "Milvus/ES/Neo4j 客户端的真实 SDK 调用大多被注释，connect 甚至会直接标记成功，因此不能声称生产接入。",
    ], bullet_id)

    add_heading(doc, "9. 记忆与安全代码分析", 1)
    add_heading(doc, "记忆", 2)
    add_bullets(doc, [
        "ShortTermMemory 保存最近 N 轮对话。",
        "LongTermMemory 支持向量相似度、过滤召回、去重、衰减、过期和 superseded/quarantined 标记。",
        "GraphMemory 在 Neo4j 可用时做邻居扩展；当前客户端仍是占位。",
        "PreferenceMemory 用 user_id → key/value 字典保存偏好。",
    ], bullet_id)
    add_heading(doc, "安全", 2)
    add_bullets(doc, [
        "Validator 用正则把命令分成 safe、warn、block。",
        "Warn 命令需要 confirm=True；Block 直接拒绝。",
        "Sandbox 的 local backend 最终仍使用 shell=True 在本机执行；它不是强隔离。",
        "真正 Docker 隔离代码位于 infrastructure/sandbox，但项目主流程没有完整接通。",
    ], bullet_id)

    add_heading(doc, "10. 本次修复和仍需完善", 1)
    add_matrix(doc, ["项目", "结果", "说明"], [
        ("项目改名", "完成", "目录、README、输出、提示词和数据库默认名改为 dan。"),
        ("聚合节点", "已修复", "n4 不再按空工具名执行，改为汇总上游成功结果。"),
        ("Planner 重复节点", "已修复", "search_nodes 循环结束后只添加一次。"),
        ("离线 Demo", "通过", "n1/n3/n4 done，n2 skipped。"),
        ("Python 编译", "通过", "compileall 未报告语法错误。"),
        ("pytest", "未验证", "当前环境缺少 pytest；需本机安装后运行。"),
        ("真实 LLM", "环境受限", "当前沙箱网络被拒绝；需本机网络验证。"),
    ], [2100, 1500, 5760])

    add_heading(doc, "11. 你应该怎样学习这份代码", 1)
    add_bullets(doc, [
        "第一遍：只运行 main.py demo，按终端顺序找到对应代码。",
        "第二遍：从 Node → TaskGraph → GraphRuntime，手画 n1-n4 的入度变化。",
        "第三遍：在 `_execute_single` 下断点，看工具节点和聚合节点走不同分支。",
        "第四遍：修改一个搜索工具为 async 并加入 sleep，观察竞速胜者变化。",
        "第五遍：给 `_plan` 写测试，确认节点ID不重复、聚合依赖完整。",
        "第六遍：用内存数据手算 RRF，再对照 HybridStore 输出。",
        "第七遍：逐项标注真实实现、部分实现和占位接口，准备面试回答。",
    ], bullet_id)

    add_heading(doc, "12. 面试时必须能回答", 1)
    add_bullets(doc, [
        "一次请求从 main.py 到最终回答经历哪些方法？",
        "Kahn 算法如何得到并行层，怎样检测环？",
        "Race Group 的 First-success-wins 是如何实现的？",
        "聚合节点为什么不能当普通工具执行？",
        "RRF 为什么比直接相加 Milvus/ES 分数更合理？",
        "chat_stream 为什么不算真正的流式？",
        "哪些数据库接口还只是骨架？你准备如何完成真实接入？",
        "Sandbox 为什么不能只靠正则和 shell=True 就称为安全沙箱？",
    ], bullet_id)

    doc.core_properties.title = "dan项目运行与代码分析手册"
    doc.core_properties.subject = "Python AI Agent 项目运行、架构分析与面试准备"
    doc.core_properties.author = "OpenAI Codex"
    doc.save(OUT)
    print(OUT)


if __name__ == "__main__":
    build()
