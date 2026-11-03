from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor


OUT = Path(__file__).with_name("dan项目10天学习与面试准备计划.docx")

BLUE = "1F4E78"
MID_BLUE = "5B9BD5"
LIGHT_BLUE = "D9EAF7"
PALE = "EEF5FA"
GRAY = "666666"
GREEN = "E2F0D9"
YELLOW = "FFF2CC"
RED = "FCE4D6"


def set_cell_shading(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_text(cell, text, bold=False, color=None, size=9.5):
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(0)
    r = p.add_run(text)
    r.bold = bold
    r.font.size = Pt(size)
    r.font.name = "微软雅黑"
    r._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")
    if color:
        r.font.color.rgb = RGBColor.from_string(color)


def set_repeat_table_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def add_table(doc, headers, rows, widths=None):
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"
    hdr = table.rows[0]
    set_repeat_table_header(hdr)
    for idx, h in enumerate(headers):
        set_cell_shading(hdr.cells[idx], BLUE)
        set_cell_text(hdr.cells[idx], h, bold=True, color="FFFFFF", size=9.5)
        hdr.cells[idx].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    for row_idx, values in enumerate(rows):
        cells = table.add_row().cells
        for idx, value in enumerate(values):
            if row_idx % 2:
                set_cell_shading(cells[idx], PALE)
            set_cell_text(cells[idx], str(value), size=9)
            cells[idx].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
    if widths:
        for row in table.rows:
            for idx, width in enumerate(widths):
                row.cells[idx].width = Cm(width)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)
    return table


def add_bullet(doc, text, level=0, checkbox=False):
    p = doc.add_paragraph(style="List Bullet" if level == 0 else "List Bullet 2")
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.1
    prefix = "□ " if checkbox else ""
    p.add_run(prefix + text)
    return p


def add_number(doc, text):
    p = doc.add_paragraph(style="List Number")
    p.paragraph_format.space_after = Pt(2)
    p.add_run(text)
    return p


def add_callout(doc, title, text, fill=LIGHT_BLUE):
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"
    cell = table.cell(0, 0)
    set_cell_shading(cell, fill)
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run(title + "\n")
    r.bold = True
    r.font.color.rgb = RGBColor.from_string(BLUE)
    p.add_run(text)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


def heading(doc, text, level=1):
    return doc.add_heading(text, level=level)


def add_day(doc, day):
    doc.add_page_break()
    title = doc.add_heading(f"第 {day['day']} 天｜{day['title']}", level=1)
    title.paragraph_format.space_after = Pt(5)
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(6)
    r = p.add_run(day["goal"])
    r.bold = True
    r.font.color.rgb = RGBColor.from_string(BLUE)

    add_table(
        doc,
        ["时间", "任务", "具体行动", "产出"],
        day["schedule"],
        [2.2, 3.2, 9.2, 3.0],
    )

    heading(doc, "当天必须掌握", 2)
    for item in day["master"]:
        add_bullet(doc, item)

    heading(doc, "代码实践", 2)
    for item in day["practice"]:
        add_number(doc, item)

    heading(doc, "达到什么程度才算完成", 2)
    for item in day["acceptance"]:
        add_bullet(doc, item, checkbox=True)

    heading(doc, "当天面试题", 2)
    for q, key in day["questions"]:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(1)
        r = p.add_run("问：" + q)
        r.bold = True
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.7)
        p.paragraph_format.space_after = Pt(4)
        p.add_run("回答要点：" + key)

    add_callout(doc, "当天交付物", day["deliverable"], GREEN)


def build_document():
    doc = Document()
    sec = doc.sections[0]
    sec.top_margin = Cm(1.8)
    sec.bottom_margin = Cm(1.8)
    sec.left_margin = Cm(2.1)
    sec.right_margin = Cm(2.1)

    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "微软雅黑"
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")
    normal.font.size = Pt(10.5)
    normal.paragraph_format.line_spacing = 1.2
    normal.paragraph_format.space_after = Pt(4)

    for style_name, size, color in [
        ("Title", 24, BLUE),
        ("Heading 1", 17, BLUE),
        ("Heading 2", 13, MID_BLUE),
        ("Heading 3", 11, BLUE),
    ]:
        style = styles[style_name]
        style.font.name = "微软雅黑"
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")
        style.font.size = Pt(size)
        style.font.color.rgb = RGBColor.from_string(color)
        style.font.bold = True

    # 封面
    for _ in range(4):
        doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("dan 项目")
    r.bold = True
    r.font.size = Pt(27)
    r.font.color.rgb = RGBColor.from_string(BLUE)
    r.font.name = "微软雅黑"
    r._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("10 天学习与面试准备计划")
    r.bold = True
    r.font.size = Pt(22)
    r.font.color.rgb = RGBColor.from_string(MID_BLUE)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(20)
    r = p.add_run("目标：从“能运行项目”提升到“能讲清架构、能修改代码、能应对追问”")
    r.font.size = Pt(12)
    r.font.color.rgb = RGBColor.from_string(GRAY)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(90)
    p.add_run("建议投入：每天 6～8 小时｜适用方向：Python 后端 / AI Agent / RAG 应用开发")

    doc.add_page_break()
    heading(doc, "使用说明", 1)
    add_callout(
        doc,
        "10 天后的目标",
        "能够在 3 分钟内完整介绍项目；不看代码画出执行链路；解释 DAG、Asyncio、Race、RRF、记忆与沙箱；现场运行无明显失败；能够修改一个工具节点并为其补测试。",
        GREEN,
    )
    heading(doc, "每天固定节奏", 2)
    add_table(
        doc,
        ["阶段", "建议用时", "方法"],
        [
            ("复习", "30 分钟", "不看资料复述前一天内容，检查遗留问题"),
            ("原理", "1.5～2 小时", "学习当天核心概念，手绘流程或数据结构"),
            ("读代码", "1.5 小时", "从入口沿调用链阅读，标注输入、状态变化、输出和异常"),
            ("动手实践", "2～3 小时", "修改代码、补测试、运行 Demo，保留结果"),
            ("面试复盘", "45 分钟", "口述回答当天问题并录音，回答控制在 1～2 分钟"),
        ],
        [3, 3, 11],
    )
    heading(doc, "学习规则", 2)
    for item in [
        "每天必须产生可验证交付物，不能只看视频或阅读代码。",
        "简历只写已经真实完成并能现场解释的能力；占位客户端不能描述为生产接入。",
        "遇到代码问题先画状态变化，再调试，不直接背结论。",
        "每晚用自己的话回答：为什么这样设计、替代方案是什么、当前实现有什么不足。",
        "第 7 天前先保证核心 Demo 正确，第 8～10 天再做展示与面试包装。",
    ]:
        add_bullet(doc, item)

    heading(doc, "当前项目基线与风险", 2)
    add_table(
        doc,
        ["现状", "风险", "本计划处理方式"],
        [
            ("AGGREGATE 节点缺少执行逻辑", "Demo 的 n4 报 Tool '' not found", "第 4 天修复并补测试"),
            ("Planner 循环内重复追加搜索节点", "多个搜索工具时节点重复", "第 5 天修复"),
            ("chat_stream 完成后回放事件", "不是真正实时流式", "第 8 天改为 Queue 驱动"),
            ("Milvus/ES/Neo4j/PG 多为占位实现", "简历容易夸大", "第 6～7 天明确边界，至少接通一个真实闭环"),
            ("项目当前不是 Git 仓库", "修改过程难追踪", "建议学习前初始化个人版本控制并分天提交"),
        ],
        [5, 6, 6],
    )

    days = [
        {
            "day": 1,
            "title": "建立全局认知与请求执行链",
            "goal": "目标：知道项目为什么存在、每个目录负责什么，并能独立画出一次请求的完整链路。",
            "schedule": [
                ("09:00–09:30", "建立基线", "运行 main.py demo 和交互模式；记录输出、错误、耗时与环境要求。", "基线记录"),
                ("09:30–11:00", "阅读入口", "阅读 README、main.py、config；梳理启动参数、MockLLM、工具注册和 Agent 构建。", "入口笔记"),
                ("13:30–15:00", "阅读主链路", "沿 UnifiedAgent.chat → 上下文 → plan → run_dag_plan → answer → memory 阅读。", "调用链图"),
                ("15:10–16:30", "目录职责", "给 domain、application、infrastructure、interfaces、tests 各写一句职责。", "模块表"),
                ("16:40–17:30", "口述训练", "录制 1 分钟与 3 分钟项目介绍，回听并删除模糊表述。", "介绍录音"),
            ],
            "master": [
                "领域层保存核心规则，应用层负责编排用例，基础设施层适配外部服务。",
                "一次请求经过上下文装配、任务规划、DAG 执行、回答生成和记忆更新。",
                "当前项目是可运行的核心原型，真实基础设施连接仍需完善。",
                "RAG、Memory、Tool、Sandbox 分别解决知识、个性化、行动能力和执行安全问题。",
            ],
            "practice": [
                "在纸上或 draw.io 画出请求时序图，必须标注每一步输入和输出。",
                "给 main.py 中 search_web 和 recall_memory 各增加一条日志，观察工具何时执行。",
                "建立《项目问题清单》，记录至少 8 个疑问或缺陷，后续逐项关闭。",
            ],
            "acceptance": [
                "不看代码说出四个目录职责。",
                "能在 3 分钟内讲完请求执行链，没有明显断点。",
                "能明确说出项目已完成能力与占位能力。",
                "能成功运行 Demo，并解释当前 n4 为什么失败。",
            ],
            "questions": [
                ("项目解决了什么问题？", "传统 ReAct 串行、检索来源单一、长期对话缺乏记忆治理；项目用 DAG、Hybrid RAG 和多层记忆改善。"),
                ("为什么采用分层架构？", "隔离业务规则与外部服务，便于测试、替换数据库或 LLM，并减少耦合。"),
                ("项目现在是生产系统吗？", "不是；核心领域算法和 Demo 已完成，接口、持久化、真实索引和可靠性仍在完善。"),
            ],
            "deliverable": "一张项目架构图、一张请求调用链图、一份模块职责表，以及 1 分钟项目介绍稿。",
        },
        {
            "day": 2,
            "title": "掌握 DAG 数据结构与 Kahn 拓扑排序",
            "goal": "目标：能手算入度和拓扑层级，解释环检测，并从代码层掌握 TaskGraph 的状态变化。",
            "schedule": [
                ("09:00–10:30", "DAG 原理", "学习节点、边、入度、出度、拓扑排序、环、悬空依赖。", "概念卡片"),
                ("10:40–12:00", "手算 Kahn", "分别手算线性图、并行图、带环图，写出每轮 ready 集合。", "三组演算"),
                ("13:30–15:00", "阅读 graph.py", "逐方法阅读 Node、TaskGraph、from_nodes、topological_levels、mark_done、validate。", "代码注释"),
                ("15:10–16:40", "测试驱动", "运行并阅读 test_graph；补重复 ID、空图、自依赖和多层图测试。", "新增测试"),
                ("16:50–17:30", "口述复盘", "白板讲 Kahn 算法及复杂度，回答环检测问题。", "复盘记录"),
            ],
            "master": [
                "Kahn 算法不断选择入度为 0 的节点，删除其出边，直到处理全部节点。",
                "若处理数量小于节点总数，剩余节点构成环或受环影响。",
                "时间复杂度为 O(V+E)，空间复杂度为 O(V+E)。",
                "同一拓扑层仅表示无图依赖，不代表业务上一定可以无限并发。",
                "TaskGraph 的静态拓扑计算与运行时 in_degree 更新是两个不同视角。",
            ],
            "practice": [
                "构造 A→C、B→C、C→D 的图，手算每一步 in_degree。",
                "新增自依赖、两节点环、依赖不存在、重复节点 ID 测试。",
                "检查 add_node 重复 ID 的行为，写下应覆盖、拒绝还是合并的设计选择。",
            ],
            "acceptance": [
                "能在白板上从零写出 Kahn 算法伪代码。",
                "能解释 topological_levels 与 ready_nodes 的区别。",
                "能在 2 分钟内定位一个图为什么卡在 Pending。",
                "至少新增 4 个图模型边界测试。",
            ],
            "questions": [
                ("如何检测 DAG 中存在环？", "执行 Kahn；最终 processed 小于节点总数即存在环。"),
                ("为什么同层节点可以并行？", "它们之间没有尚未满足的依赖边，但仍需受资源、限流和业务约束控制。"),
                ("重复节点 ID 有什么风险？", "字典覆盖会导致边、入度和计划节点数量不一致，应在建图时显式拒绝。"),
            ],
            "deliverable": "Kahn 算法手算稿、DAG 状态图、至少 4 个新增测试和一段 2 分钟讲解录音。",
        },
        {
            "day": 3,
            "title": "吃透 Asyncio 并发、超时、取消与 Race",
            "goal": "目标：理解 Python 异步调度，不把并发说成并行，并能实现可靠的 First-success-wins。",
            "schedule": [
                ("09:00–10:30", "Asyncio 基础", "学习事件循环、协程、Task、await、gather、wait、Semaphore。", "概念对照表"),
                ("10:40–12:00", "并发实验", "实现 2/3/4 秒任务的串行与并发版本，记录耗时。", "性能记录"),
                ("13:30–15:00", "阅读 Runtime", "跟踪 execute、节点调度、工具调用、状态更新和事件回调。", "状态时序图"),
                ("15:10–16:30", "Race 实验", "实现先完成与先成功的对照；覆盖先失败、后成功、全部失败。", "Race 测试"),
                ("16:40–17:30", "异常治理", "练习 wait_for 超时、CancelledError、finally 释放资源。", "异常清单"),
            ],
            "master": [
                "Asyncio 提升 I/O 等待阶段吞吐，不会自动加速 CPU 密集型计算。",
                "gather 等待一组结果；wait(FIRST_COMPLETED) 可观察首先完成任务，但首先完成不等于首先成功。",
                "取消是协作式的：Task 收到取消请求后，需要在 await 点响应并在 finally 中清理。",
                "Semaphore 控制并发量，超时必须同时考虑单节点和整个任务。",
                "竞速组的下游依赖应在组获得有效结果后释放，而不是等待全部成员完成。",
            ],
            "practice": [
                "编写 async_demo.py，对比串行和并发耗时并解释结果。",
                "为竞速组补充：A 先失败 B 后成功、A 超时 B 成功、A/B 全失败三组测试。",
                "检查被取消任务最终状态是 CANCELLED 还是 SKIPPED，并统一语义。",
            ],
            "acceptance": [
                "能解释协程、线程、进程的差异和使用场景。",
                "能从零写出带并发限制和超时的工具调用代码。",
                "能说清 first-completed 与 first-success 的区别。",
                "能解释取消为什么可能没有立即停止外部请求。",
            ],
            "questions": [
                ("为什么 Agent 适合 asyncio？", "LLM、HTTP、搜索和数据库主要是 I/O 等待，可重叠等待时间降低总耗时。"),
                ("asyncio.gather 和 wait 有什么区别？", "gather 聚合整组结果；wait 可按完成条件返回，更适合竞速和逐步调度。"),
                ("如何真正取消 HTTP 请求？", "取消上层 Task，并确保客户端支持异步取消、关闭响应流和连接；服务端不一定停止处理。"),
            ],
            "deliverable": "并发耗时对比、Runtime 状态时序图，以及不少于 3 个 Race 异常测试。",
        },
        {
            "day": 4,
            "title": "修复 DAG Runtime，让核心 Demo 完整成功",
            "goal": "目标：解决 AGGREGATE 节点失败，定义失败传播规则，并让核心 Demo 与测试全部通过。",
            "schedule": [
                ("09:00–10:00", "定位故障", "从 n4 错误回溯节点类型分派，确认 AGGREGATE 被送入普通工具执行路径。", "根因记录"),
                ("10:10–12:00", "设计聚合语义", "定义聚合输入、输出、部分失败处理、空结果处理和顺序。", "设计说明"),
                ("13:30–15:30", "编码修复", "实现聚合节点执行器，读取依赖结果；修正竞速组对依赖完成度的影响。", "代码提交"),
                ("15:40–16:40", "补测试", "覆盖全部成功、部分失败、无依赖、竞速组、全部失败。", "测试报告"),
                ("16:50–17:30", "回归", "运行 Demo 和测试，保存终端输出并检查状态一致性。", "成功截图"),
            ],
            "master": [
                "节点类型必须通过清晰的执行器分派，不能让非工具节点落入 Tool Registry。",
                "聚合节点应读取依赖节点结果，而不是再次调用不存在的工具。",
                "失败传播需要策略：fail-fast、允许部分结果、跳过下游或触发 replan。",
                "状态终态应互斥且可解释：DONE、FAILED、SKIPPED、CANCELLED。",
                "修复完成的标准是测试和 Demo 一致，不是仅让异常消失。",
            ],
            "practice": [
                "先写失败测试复现 Tool '' not found，再实现修复。",
                "为 AGGREGATE 定义结果格式，例如按依赖顺序组合成功结果并标记来源。",
                "故意让 n1 失败，观察 n4 是否符合设计策略。",
            ],
            "acceptance": [
                "Demo 中所有预期节点进入合理终态，n4 不再失败。",
                "至少 5 个聚合与失败传播测试通过。",
                "能解释修复前后的调用路径差异。",
                "能够展示先写失败测试、再修复、最后回归的过程。",
            ],
            "questions": [
                ("项目中遇到的一个真实 Bug？", "AGGREGATE 没有类型分派，被当成空工具调用；通过失败测试、独立执行器和回归测试修复。"),
                ("一个上游失败，下游怎么办？", "取决于节点策略；强依赖通常跳过，容错聚合可使用部分成功结果，同时记录缺失来源。"),
                ("为什么不能只捕获异常返回空字符串？", "会掩盖失败，使下游误判成功，破坏可观测性与恢复语义。"),
            ],
            "deliverable": "AGGREGATE 修复、失败传播说明、5 个以上测试，以及无明显失败的 Demo 输出。",
        },
        {
            "day": 5,
            "title": "理解 Agent 编排与 Planner，修复重复节点",
            "goal": "目标：掌握 UnifiedAgent 主循环，理解规则 Planner 的局限，并设计可靠的结构化 LLM Planner。",
            "schedule": [
                ("09:00–10:30", "阅读 Agent", "分析上下文装配、规划、执行、答案生成和记忆更新的边界。", "职责表"),
                ("10:40–12:00", "修复重复节点", "复现多个 search 工具时 nodes.extend 位于循环内部导致的重复，修复并补测试。", "修复提交"),
                ("13:30–15:00", "Planner 设计", "设计 JSON Schema：节点 ID、类型、工具、参数、依赖、竞速组。", "Schema 草案"),
                ("15:10–16:20", "安全校验", "设计工具白名单、最大节点数、参数类型、悬空依赖和环检测。", "校验清单"),
                ("16:30–17:30", "Replan 思考", "定义何时重试、何时换工具、何时重新规划、如何限制循环。", "状态机"),
            ],
            "master": [
                "当前 _plan 是工具名规则，不是 LLM 自主规划，必须准确描述。",
                "LLM Planner 输出必须经过 Schema、工具权限、依赖和资源限制校验。",
                "Planner 负责决定做什么，Runtime 负责可靠地执行，两者不应混在一起。",
                "Replan 需要携带失败原因和已有观察结果，同时限制次数避免无限循环。",
                "重复 ID 应在 TaskGraph 建图阶段拒绝，形成第二道防线。",
            ],
            "practice": [
                "注册两个名称包含 search 的工具，写测试复现节点重复。",
                "将 nodes.extend 移出循环并为节点 ID 唯一性补断言。",
                "用 Pydantic 写出 Planner 输出模型，验证一个正确和三个错误 JSON。",
            ],
            "acceptance": [
                "能解释 Planner 与 Runtime 的职责边界。",
                "多搜索工具不再产生重复节点。",
                "能列出至少 6 项 LLM 计划校验规则。",
                "能画出失败→重试→Replan→终止的状态机。",
            ],
            "questions": [
                ("如何防止 LLM 生成不存在的工具？", "将可用工具 Schema 提供给模型，执行前按用户权限白名单进行服务端校验。"),
                ("如何防止 Planner 生成环？", "Pydantic 校验结构后，用 TaskGraph.validate/Kahn 做语义校验，不通过则修复或重新规划。"),
                ("重试和 Replan 有什么区别？", "重试保持同一动作，适合瞬时故障；Replan 改变任务图或工具，适合策略错误和不可恢复失败。"),
            ],
            "deliverable": "重复节点修复、结构化 Planner Schema、校验清单与 Replan 状态机。",
        },
        {
            "day": 6,
            "title": "掌握 Hybrid RAG 与 RRF 融合",
            "goal": "目标：能完整解释文档入库和查询链路，手算 RRF，并明确当前真实实现与占位实现的边界。",
            "schedule": [
                ("09:00–10:30", "RAG 全链路", "学习清洗、切片、Embedding、索引、召回、融合、重排、引用生成。", "流程图"),
                ("10:40–12:00", "三路检索", "对比向量、BM25、知识图谱适用场景、分数和失败模式。", "对比表"),
                ("13:30–14:40", "RRF 手算", "用两份排名列表计算文档 A/B/C 的融合分数，分析 k 与权重。", "计算稿"),
                ("14:50–16:10", "阅读 rag.py", "跟踪 index、search、search_multi、降级、rerank 与 chunk 取回。", "代码笔记"),
                ("16:20–17:30", "基础设施审计", "检查 Milvus、ES、Neo4j、PG 客户端，标注真实逻辑、注释逻辑和固定返回。", "完成度矩阵"),
            ],
            "master": [
                "Milvus 擅长语义相似，ES 擅长精确词项，Neo4j 擅长关系和多跳。",
                "原始分数尺度不同，不能简单相加；RRF 使用排名进行稳健融合。",
                "k 越大，前后排名差异被平滑；权重表达通道可信度，不应随意设置。",
                "Rerank 是对候选集精排，不能替代初始高召回阶段。",
                "生产 RAG 必须返回来源、chunk_id 和 doc_id，支持引用与删除。",
            ],
            "practice": [
                "手算两路 RRF 并用 Python 验证结果。",
                "为重复文档、单路降级、空结果、多 query 融合补测试。",
                "把所有基础设施方法标成：真实、部分实现、占位，并据此修正项目介绍。",
            ],
            "acceptance": [
                "能在 5 分钟内画出完整 RAG 入库与查询链路。",
                "能不看资料写出 RRF 公式并解释 k。",
                "能说出向量检索不擅长的两个场景。",
                "能准确指出当前哪些客户端尚未真实接通。",
            ],
            "questions": [
                ("为什么不直接相加 Milvus 和 BM25 分数？", "距离、相似度和 BM25 的范围与方向不同，直接相加缺乏可比性；RRF 使用排名融合。"),
                ("为什么需要 BM25？", "专有名词、错误码、编号和精确术语常被语义向量弱化，关键词检索可补足。"),
                ("RAG 结果不相关如何排查？", "逐层检查切片、Embedding、索引、召回、融合、重排和提示拼接，并观察每路候选。"),
            ],
            "deliverable": "RAG 双链路图、RRF 手算表、三路检索对比表、基础设施完成度矩阵。",
        },
        {
            "day": 7,
            "title": "掌握记忆系统、持久化和多用户隔离",
            "goal": "目标：区分聊天记录与长期记忆，理解去重、衰减、冲突治理，并设计数据持久化与一致性方案。",
            "schedule": [
                ("09:00–10:20", "记忆分类", "学习短期、长期、偏好、图记忆和任务快照的区别。", "记忆分类图"),
                ("10:30–12:00", "阅读 memory.py", "跟踪 Store、Recall、Filter、Consolidate、Quarantine、Superseded。", "状态图"),
                ("13:30–14:30", "相似度与衰减", "手算余弦相似度，分析阈值、TTL、importance 与 decay。", "计算稿"),
                ("14:40–16:00", "持久化设计", "设计 PostgreSQL 表、user_id/tenant_id、索引、启动恢复和事务边界。", "表结构草案"),
                ("16:10–17:30", "一致性与测试", "设计 PG→Milvus/ES 的 Outbox 与补偿；补多用户隔离和冲突测试。", "一致性图"),
            ],
            "master": [
                "聊天记录是原始事件，长期记忆是筛选后的可复用信息。",
                "长期记忆不能无限写入，需要抽取、去重、衰减、淘汰和冲突治理。",
                "Quarantine 用于隔离可疑记忆；Superseded 表示被新事实替代但保留审计。",
                "所有存储与缓存查询必须携带 user_id/tenant_id，不能只在 UI 层过滤。",
                "跨 PG、Milvus、ES 不适合分布式强事务，可使用 Outbox、幂等和补偿。",
            ],
            "practice": [
                "构造“用户喜欢 Java→现在主要使用 Python”的冲突案例并定义治理结果。",
                "补充用户 A 的查询不能召回用户 B 记忆的测试。",
                "设计 memories、conversation_messages、rag_chunks 三张表的关键字段。",
            ],
            "acceptance": [
                "能解释五类状态数据的边界。",
                "能手算两个简单向量的余弦相似度。",
                "能说明如何防止跨用户记忆串线。",
                "能讲清 PG 与向量索引最终一致性的实现。",
            ],
            "questions": [
                ("记忆和聊天记录有什么区别？", "聊天记录是原始事件；记忆是抽取、分类、评分后对未来有价值的信息。"),
                ("如何处理相互矛盾的记忆？", "识别同一 slot/实体的冲突，新事实 supersede 旧事实；高风险内容先隔离并保留审计。"),
                ("如何保证多用户隔离？", "表字段、仓储方法、向量过滤、图节点、缓存键和权限测试全链路带 tenant/user 标识。"),
            ],
            "deliverable": "记忆生命周期图、表结构草案、多用户隔离测试和跨存储一致性方案。",
        },
        {
            "day": 8,
            "title": "实现真正流式输出，并补齐 FastAPI 展示层",
            "goal": "目标：理解 SSE，使用 asyncio.Queue 让运行事件实时返回，并形成可演示的后端接口。",
            "schedule": [
                ("09:00–10:20", "HTTP 与 SSE", "学习 FastAPI 路由、请求模型、StreamingResponse、SSE 格式和断连。", "接口设计"),
                ("10:30–11:30", "定位伪流式", "阅读 chat_stream，确认先 await chat 再回放 events 的问题。", "时序对照"),
                ("11:30–12:00", "Queue 方案", "设计生产者任务、事件队列、结束哨兵、异常与客户端取消。", "设计图"),
                ("13:30–15:30", "编码实现", "新增 FastAPI /health、/chat、/chat/stream；接入 Queue 驱动事件。", "可运行 API"),
                ("15:40–17:30", "接口测试", "使用 curl/浏览器验证事件逐步到达；测试异常、断连和并发请求。", "接口记录"),
            ],
            "master": [
                "SSE 是服务器到客户端的单向文本事件流，适合 Agent 进度和 token 推送。",
                "真正流式必须在任务执行过程中 yield，不能等任务完成后回放。",
                "Queue 解耦执行生产者与 HTTP 消费者，并需要结束哨兵和异常事件。",
                "客户端断连后应取消后台任务，避免继续消耗 LLM 和工具资源。",
                "接口层负责协议转换与认证，不应包含 DAG 业务规则。",
            ],
            "practice": [
                "实现最小 FastAPI 服务和 Pydantic ChatRequest。",
                "用 asyncio.Queue 改造 chat_stream，确保 node_start/node_done 实时出现。",
                "写一个慢工具验证事件时间戳不是任务结束后集中返回。",
            ],
            "acceptance": [
                "curl 调用流式接口时可以逐条看到事件。",
                "接口包含健康检查、同步聊天和流式聊天。",
                "客户端断开后后台任务能被取消或及时停止。",
                "能解释 SSE 与 WebSocket 的选择差异。",
            ],
            "questions": [
                ("你怎么证明是真流式？", "使用慢工具和事件时间戳，客户端在任务完成前收到 node_start/node_done，而非结束后集中返回。"),
                ("SSE 与 WebSocket 如何选择？", "单向进度/token 推送优先 SSE；需要频繁双向实时通信时选择 WebSocket。"),
                ("客户端断开怎么办？", "检测断连，取消生产者 Task，关闭外部响应流，并在 finally 中释放资源。"),
            ],
            "deliverable": "FastAPI 最小后端、真正 SSE 流、接口测试记录和新旧流式时序对比图。",
        },
        {
            "day": 9,
            "title": "安全沙箱、测试体系与可观测性",
            "goal": "目标：能够从攻击面解释沙箱设计，为核心链路建立测试和日志证据，而不只展示功能。",
            "schedule": [
                ("09:00–10:20", "安全模型", "学习命令注入、路径逃逸、Prompt Injection、容器逃逸与最小权限。", "威胁清单"),
                ("10:30–12:00", "阅读 Sandbox", "检查 Validator、DockerExecutor、资源限制、超时和产物目录。", "安全矩阵"),
                ("13:30–14:30", "测试分层", "整理单元、集成、端到端测试；运行全部测试并修复失败。", "测试报告"),
                ("14:40–16:00", "可观测性", "统一 task_id/node_id/user_id 日志字段，记录耗时、状态、重试与错误。", "日志样例"),
                ("16:10–17:30", "故障演练", "模拟工具超时、异常、全部竞速失败、RAG 空结果和客户端断开。", "演练记录"),
            ],
            "master": [
                "黑名单只能降低已知风险，不能替代白名单、参数化执行和强隔离。",
                "Docker 共享宿主机内核，不是绝对安全边界。",
                "断网、只读根、cap-drop、no-new-privileges、非 root 和资源限额需要组合使用。",
                "日志要支持按 task_id 重建一次执行，指标要关注成功率、P95、超时和重试。",
                "单元测试验证规则，集成测试验证适配器，端到端测试验证完整业务链。",
            ],
            "practice": [
                "新增至少 10 条危险命令或绕过形式测试，不执行真实危险操作。",
                "为工具调用增加结构化日志与耗时统计。",
                "执行 5 种故障演练，确认系统产生明确终态和错误事件。",
            ],
            "acceptance": [
                "能够列出 Docker 沙箱至少 6 项安全措施。",
                "全部核心测试可一条命令运行，并保存通过结果。",
                "能根据 task_id 从日志还原节点执行顺序。",
                "系统面对超时和异常不会永久 Pending。",
            ],
            "questions": [
                ("Docker 沙箱绝对安全吗？", "不安全；共享宿主机内核，还需 seccomp/AppArmor、非 root、镜像白名单和独立执行节点。"),
                ("为什么命令黑名单不够？", "编码、拼接、解释器和新命令都可能绕过；应优先白名单、结构化参数和隔离。"),
                ("如何排查一个慢任务？", "按 task_id 查看各节点开始结束时间、外部调用耗时、并发等待、重试和超时指标。"),
            ],
            "deliverable": "安全威胁矩阵、完整测试报告、结构化日志样例和 5 组故障演练结果。",
        },
        {
            "day": 10,
            "title": "整合成果、量化测试与模拟面试",
            "goal": "目标：把项目整理成可信的面试作品，能够展示、讲解、追问和现场修改。",
            "schedule": [
                ("09:00–10:00", "最终回归", "从全新终端按 README 启动，运行 Demo、API 和全部测试。", "回归报告"),
                ("10:10–11:30", "量化实验", "对比串行/并发耗时，记录 DAG 节点数、成功率和 P95；结果真实可复现。", "数据表"),
                ("11:30–12:00", "整理 README", "补架构、启动、配置、限制、测试命令和演示步骤。", "新版 README"),
                ("13:30–14:30", "简历材料", "写 4～5 条项目职责，只保留实际完成能力并加入量化结果。", "简历稿"),
                ("14:40–16:00", "模拟面试", "完成 30 秒、1 分钟、3 分钟介绍和 20 道追问。", "录音与评分"),
                ("16:10–17:30", "现场编码", "在 30 分钟内新增工具、接入节点、补测试并演示结果。", "现场演练"),
            ],
            "master": [
                "任何简历表述都能指向具体代码、测试或运行证据。",
                "能够说明技术选择、替代方案、缺点、故障处理和下一步计划。",
                "核心亮点优先讲 DAG + Asyncio + Race，再讲 RAG、记忆与安全。",
                "量化数据必须来自真实实验，记录硬件、输入、并发和测量方法。",
                "明确项目边界不会减分，夸大占位实现会显著降低可信度。",
            ],
            "practice": [
                "邀请朋友连续追问 20 分钟，要求对方专门质疑真实性和边界。",
                "不看代码画架构、DAG 状态机、RAG 流程和记忆生命周期。",
                "现场新增一个 weather_mock 工具并加入任务图，补一个成功测试。",
            ],
            "acceptance": [
                "Demo、API 和测试均能稳定运行。",
                "3 分钟项目介绍结构清楚且不过度宣传。",
                "能回答本计划末尾 20 道核心问题的 80% 以上。",
                "能在 30 分钟内完成一次小功能修改与测试。",
                "最终 README、架构图、简历稿和演示脚本完整。",
            ],
            "questions": [
                ("项目最有价值的设计是什么？", "选择一个真正掌握的点，推荐 DAG 并发与竞速；从问题、方案、难点、验证、局限五步回答。"),
                ("项目目前最大的不足是什么？", "真实基础设施、可靠恢复和生产级安全仍需完善；说明已制定的具体路线。"),
                ("如果再给一周会做什么？", "优先接通真实 RAG 闭环、任务快照恢复、多用户认证和压测，而不是继续增加空接口。"),
            ],
            "deliverable": "最终可演示版本、测试与性能数据、README、简历项目经历、演示脚本和模拟面试记录。",
        },
    ]

    for day in days:
        add_day(doc, day)

    doc.add_page_break()
    heading(doc, "最终面试材料", 1)
    heading(doc, "1 分钟项目介绍模板", 2)
    add_callout(
        doc,
        "建议表述",
        "这是一个基于 Python 的 AI Agent 任务编排项目，主要解决传统 ReAct 串行执行延迟高、检索来源单一和长期对话缺少记忆治理的问题。系统把复杂任务建模为 DAG，通过 Kahn 算法识别就绪节点，并使用 asyncio 并发执行；对于多个等价搜索源采用 First-success-wins 竞速策略。检索部分设计了向量、BM25 和知识图谱三路召回，再通过 RRF 融合。记忆部分包含短期、长期、偏好和图记忆，并实现去重、衰减和冲突治理。当前我重点完成并验证了核心调度链路，同时在继续完善真实基础设施、持久化和服务可靠性。",
        LIGHT_BLUE,
    )

    heading(doc, "20 道核心自测题", 2)
    questions = [
        "1. 一次用户请求经过哪些模块？每一步输入输出是什么？",
        "2. 为什么使用 DAG 而不是普通串行 ReAct？",
        "3. Kahn 算法如何工作，复杂度是多少？",
        "4. 如何检测环、悬空依赖和重复节点 ID？",
        "5. Python 协程、线程和进程有什么区别？",
        "6. gather、wait 和 create_task 分别适合什么场景？",
        "7. First-completed 与 First-success 有什么区别？",
        "8. Race 中一个节点失败、另一个仍执行时怎么办？",
        "9. 上游失败时下游的失败传播策略有哪些？",
        "10. Planner 与 Runtime 的职责如何划分？",
        "11. 如何校验 LLM 生成的任务图？",
        "12. 为什么 Milvus、ES 和 Neo4j 的分数不能直接相加？",
        "13. 写出 RRF 公式并解释 k 与权重。",
        "14. 如何保证 RAG 删除时多个存储最终一致？",
        "15. 长期记忆与聊天记录有什么区别？",
        "16. 如何处理记忆冲突和多用户隔离？",
        "17. 当前 chat_stream 为什么不是真流式，如何改造？",
        "18. Docker 沙箱为什么不是绝对安全？",
        "19. 项目遇到过什么 Bug，你如何定位、修复和验证？",
        "20. 当前哪些模块是真实实现，哪些仍是占位，下一步优先级是什么？",
    ]
    for q in questions:
        add_bullet(doc, q, checkbox=True)

    heading(doc, "最终完成度评分表", 2)
    add_table(
        doc,
        ["能力", "合格标准", "权重", "自评分"],
        [
            ("项目理解", "3 分钟讲清完整链路和模块边界", "15%", "__/10"),
            ("DAG 与 Asyncio", "能手写核心伪代码并解释状态和异常", "25%", "__/10"),
            ("RAG 与记忆", "能画流程、手算 RRF、说明隔离与一致性", "20%", "__/10"),
            ("编码与测试", "Demo 无明显失败，核心测试通过，可现场改功能", "20%", "__/10"),
            ("工程与安全", "能解释 API、流式、日志、沙箱和故障治理", "10%", "__/10"),
            ("表达与诚信", "表述准确，能明确完成度和不足", "10%", "__/10"),
        ],
        [3.2, 9.0, 2.2, 2.4],
    )
    add_callout(
        doc,
        "面试就绪线",
        "总分达到 75/100，且“DAG 与 Asyncio”“编码与测试”两项均不低于 7 分。若核心 Demo 仍失败、测试不能运行或无法解释占位实现，先不要把相关能力写成已完成。",
        YELLOW,
    )

    heading(doc, "每日复盘模板", 2)
    for item in [
        "今天我真正理解的三个概念：____________________________",
        "今天完成的代码与测试：________________________________",
        "仍然说不清的问题：____________________________________",
        "一个真实 Bug 及根因：__________________________________",
        "如果面试官追问，我最担心的问题：______________________",
        "明天开始前必须复习：__________________________________",
    ]:
        p = doc.add_paragraph(item)
        p.paragraph_format.space_after = Pt(8)

    # 页眉页脚
    for section in doc.sections:
        header = section.header.paragraphs[0]
        header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        run = header.add_run("dan｜10 天学习与面试准备计划")
        run.font.size = Pt(8)
        run.font.color.rgb = RGBColor.from_string(GRAY)
        footer = section.footer.paragraphs[0]
        footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = footer.add_run("第 ")
        fld_char1 = OxmlElement("w:fldChar")
        fld_char1.set(qn("w:fldCharType"), "begin")
        instr_text = OxmlElement("w:instrText")
        instr_text.set(qn("xml:space"), "preserve")
        instr_text.text = "PAGE"
        fld_char2 = OxmlElement("w:fldChar")
        fld_char2.set(qn("w:fldCharType"), "end")
        run._r.append(fld_char1)
        run._r.append(instr_text)
        run._r.append(fld_char2)
        footer.add_run(" 页")

    doc.core_properties.title = "dan 项目10天学习与面试准备计划"
    doc.core_properties.subject = "Python AI Agent 项目学习计划"
    doc.core_properties.author = "Codex"
    doc.core_properties.keywords = "Python, AI Agent, DAG, Asyncio, RAG, 面试"
    doc.save(OUT)
    print(OUT)


if __name__ == "__main__":
    build_document()
