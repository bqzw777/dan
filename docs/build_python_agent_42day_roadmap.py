from pathlib import Path

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor


OUT = Path(__file__).with_name("Python到AI-Agent_42天学习路线.docx")

NAVY = "17365D"
BLUE = "2F75B5"
LIGHT_BLUE = "D9EAF7"
PALE = "F4F8FC"
GREEN = "E2F0D9"
YELLOW = "FFF2CC"
GRAY = "666666"
RED = "FCE4D6"


def set_font(run, size=10.2, bold=False, color="202020", name="微软雅黑"):
    run.font.name = name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)
    run.font.size = Pt(size)
    run.bold = bold
    run.font.color.rgb = RGBColor.from_string(color)


def shade(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_repeat_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    header = OxmlElement("w:tblHeader")
    header.set(qn("w:val"), "true")
    tr_pr.append(header)


def add_table(doc, headers, rows, widths=None):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = table.rows[0]
    set_repeat_header(hdr)
    for i, text in enumerate(headers):
        shade(hdr.cells[i], NAVY)
        p = hdr.cells[i].paragraphs[0]
        p.paragraph_format.space_after = Pt(0)
        r = p.add_run(text)
        set_font(r, size=9.2, bold=True, color="FFFFFF")
    for ri, values in enumerate(rows):
        cells = table.add_row().cells
        for i, value in enumerate(values):
            if ri % 2:
                shade(cells[i], PALE)
            cells[i].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            p = cells[i].paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.05
            r = p.add_run(str(value))
            set_font(r, size=8.8)
    if widths:
        for row in table.rows:
            for i, width in enumerate(widths):
                row.cells[i].width = Cm(width)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)
    return table


def add_callout(doc, title, text, fill=LIGHT_BLUE):
    table = doc.add_table(rows=1, cols=1)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = table.cell(0, 0)
    shade(cell, fill)
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(0)
    r = p.add_run(title + "\n")
    set_font(r, size=10.2, bold=True, color=NAVY)
    r = p.add_run(text)
    set_font(r, size=9.5)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


def add_bullet(doc, text, checkbox=False, level=0):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.55 + level * 0.45)
    p.paragraph_format.first_line_indent = Cm(-0.3)
    p.paragraph_format.space_after = Pt(1.5)
    p.paragraph_format.line_spacing = 1.08
    prefix = "□ " if checkbox else "• "
    r = p.add_run(prefix + text)
    set_font(r, size=9.5)
    return p


def heading(doc, text, level=1):
    p = doc.add_heading(text, level=level)
    p.paragraph_format.keep_with_next = True
    return p


def join_items(items):
    return "；".join(items) + "。"


weeks = [
    {
        "week": 1,
        "title": "巩固函数、数据结构与程序拆分",
        "goal": "从“会写单个函数”进步到“能把一个小需求拆成多个函数，并用列表、字典保存和处理数据”。",
        "days": [
            (1, "函数复习与返回值", ["位置参数、关键字参数、默认参数", "return与print的区别", "函数命名、单一职责"], ["编写加减乘除四个函数", "实现calculate(a, b, operator)，处理未知操作符和除零"], ["关掉资料独立写5个函数", "能解释参数、返回值和调用顺序", "每个函数只做一件事"], "calculator_v1.py"),
            (2, "列表与循环", ["列表增删改查", "for、enumerate、切片", "列表作为函数参数和返回值"], ["实现成绩平均值、最高分、及格名单", "故意传入空列表并设计合理处理"], ["能遍历并修改列表", "能避免索引越界", "能说出修改原列表和返回新列表的区别"], "score_manager.py"),
            (3, "字典与任务状态", ["get、items、keys、values", "嵌套字典", "in成员判断"], ["用字典保存n1/n2/n3状态", "实现update_status、get_pending_tasks、count_done"], ["能安全读取不存在的键", "能遍历字典键和值", "能用字典表达一条任务"], "task_status.py"),
            (4, "字符串与输入校验", ["strip、split、join、replace", "f-string", "空值、长度和类型校验"], ["实现命令解析器：tool query", "拒绝空工具名、空查询和超长输入"], ["能处理用户输入边界", "能说明校验应该放在哪里", "错误信息清楚可定位"], "command_parser.py"),
            (5, "函数作为对象", ["函数可以赋值给变量", "函数作为字典值", "callable概念"], ["实现search_web和recall_memory", "使用tools字典按名称调用函数"], ["能解释tools[name]得到什么", "能增加第三个工具而不修改主流程", "能处理工具不存在"], "tool_registry_v1.py"),
            (6, "异常处理与Traceback", ["try/except/else/finally", "ValueError与通用Exception", "阅读Traceback"], ["让一个工具主动抛出ValueError", "在调用层捕获并返回明确错误"], ["能从Traceback找到文件和行号", "不使用空except", "知道何时抛异常、何时返回结果"], "tool_errors.py"),
            (7, "周复习：函数版任务管理器", ["需求拆分", "函数间调用", "边界测试"], ["组合本周知识完成任务管理器", "支持创建、查询、完成、失败和统计"], ["不看答案完成150行以内程序", "至少手测8种输入", "能用3分钟讲清程序结构"], "week1_task_manager/"),
        ],
        "milestone": "独立完成函数版任务管理器；看懂dan中普通工具函数和tools字典；不再混淆print与return。",
    },
    {
        "week": 2,
        "title": "类、模块、类型注解、测试与Git",
        "goal": "从函数式小程序过渡到面向对象和多文件项目，为阅读Node、TaskGraph和Repository做准备。",
        "days": [
            (8, "类与对象", ["class、__init__、self", "属性与方法", "实例化"], ["把任务字典改成Task类", "实现finish和fail方法"], ["能解释类和对象的区别", "能解释self指向谁", "能创建多个互不影响的实例"], "models_v1.py"),
            (9, "dataclass与Enum", ["@dataclass自动生成方法", "默认值", "Enum状态约束"], ["用dataclass重写Task", "使用TaskStatus限制状态值"], ["能解释dataclass解决什么问题", "不再用随意字符串表示状态", "能比较枚举值"], "models_v2.py"),
            (10, "组合与职责边界", ["Task与TaskManager组合", "私有方法约定", "避免上帝类"], ["实现TaskManager管理多个Task", "把校验放在合适层"], ["能解释模型与服务的职责", "新增功能不需要复制大量代码", "主流程清楚"], "task_manager_oop.py"),
            (11, "模块与包", ["一个.py文件是模块", "__init__.py", "绝对导入、程序入口"], ["拆分models.py、service.py、main.py", "从main.py导入并运行"], ["能解释import查找过程", "能解决常见ModuleNotFoundError", "知道__name__ == '__main__'作用"], "week2_project/"),
            (12, "类型注解", ["List、Dict、Optional、Callable", "参数与返回类型", "类型提示不等于运行时校验"], ["为任务管理器补全类型注解", "为tools定义Callable类型"], ["能读懂Dict[str, Node]", "能解释Optional含义", "能看懂dan函数签名"], "typed_task_manager.py"),
            (13, "pytest基础", ["测试函数与assert", "Arrange-Act-Assert", "正常、边界、异常测试"], ["为Task和TaskManager写10个测试", "使用pytest.raises验证异常"], ["能一条命令运行测试", "测试互不依赖", "失败时能定位原因"], "tests/test_task_manager.py"),
            (14, "Git与周复习", ["init、status、add、commit、diff", "小步提交", "不提交密钥"], ["为练习项目建立Git仓库", "完成至少3个有意义提交"], ["能查看修改和历史", "提交信息说明改动目的", "知道.env为什么要忽略"], "week2完整项目与提交记录"),
        ],
        "milestone": "独立完成分模块、带类型注解和10个测试的OOP任务管理器；能开始阅读domain/graph.py。",
    },
    {
        "week": 3,
        "title": "Asyncio、HTTP、JSON与LLM工具调用",
        "goal": "掌握Agent最常用的I/O并发模型，理解LLM API和工具注册调用的最小闭环。",
        "days": [
            (15, "同步与异步", ["协程、事件循环", "async def、await", "asyncio.run"], ["编写等待2秒的异步函数", "对比三个任务串行与异步执行耗时"], ["能解释异步不是多线程", "知道哪些场景适合asyncio", "能独立运行协程"], "async_basics.py"),
            (16, "Task与gather", ["create_task", "gather", "任务异常传播"], ["并发执行三个模拟工具", "让其中一个失败并观察gather行为"], ["能解释协程对象与Task区别", "能收集多个结果", "知道异常如何影响整组任务"], "async_gather.py"),
            (17, "wait、超时与取消", ["asyncio.wait", "FIRST_COMPLETED", "wait_for、cancel"], ["实现最先完成返回", "实现2秒超时并清理任务"], ["能解释first-completed不等于first-success", "取消后会await任务结束", "finally负责清理"], "async_timeout.py"),
            (18, "Semaphore与并发限制", ["并发上限", "async with Semaphore", "限流与资源保护"], ["创建10个任务但最多同时运行3个", "记录每个任务开始结束时间"], ["能证明最大并发不超过3", "能解释为什么不能无限并发", "理解吞吐与延迟区别"], "async_semaphore.py"),
            (19, "HTTP与JSON基础", ["请求方法和状态码", "Header、Body、JSON", "API Key与环境变量"], ["调用一个公开或Mock HTTP接口", "解析JSON并处理非200响应"], ["能解释POST请求组成", "不把密钥写进源码", "能处理超时和无效JSON"], "http_client.py"),
            (20, "OpenAI-compatible API", ["messages结构", "model、temperature、max_tokens", "响应choices解析"], ["阅读项目llm_client.py", "使用MockLLM完成单轮对话；有Key再测试真实API"], ["能画出请求响应结构", "能解释System与User消息", "API失败有降级或明确错误"], "llm_chat_demo.py"),
            (21, "工具调用最小Agent", ["工具Schema", "工具注册表", "执行结果回到模型"], ["实现天气Mock、计算器和记忆工具", "完成用户输入→选工具→执行→回答闭环"], ["能增加新工具而不改执行器", "工具参数经过校验", "能在5分钟内讲清调用链"], "mini_agent/"),
        ],
        "milestone": "能独立写异步工具注册表和最小Agent；解释超时、取消、并发限制及LLM API请求结构。",
    },
    {
        "week": 4,
        "title": "吃透dan的DAG与Runtime",
        "goal": "把项目最重要的DAG调度真正学懂，并修复核心Demo中最明显的问题。",
        "days": [
            (22, "阅读Node与TaskGraph", ["Node字段", "adj_list与in_degree", "from_nodes"], ["画出Demo四节点图", "逐个写出节点入度"], ["能解释depends_on", "能说出每个状态含义", "能定位图模型入口"], "DAG结构笔记"),
            (23, "Kahn拓扑排序", ["入度为0集合", "逐轮删除出边", "O(V+E)复杂度"], ["手算线性、并行、带环三种图", "不看源码写简化Kahn算法"], ["能解释环检测", "能列出每一层节点", "能判断哪些任务可并发"], "kahn_practice.py"),
            (24, "Runtime执行链", ["run_dag_plan", "GraphRuntime.execute", "节点状态变化"], ["从main.py逐步跟踪到工具执行", "增加临时日志观察调度顺序"], ["能画Runtime时序图", "知道状态在哪里修改", "知道结果如何汇总"], "Runtime调用链图"),
            (25, "修复AGGREGATE节点", ["节点类型分派", "依赖结果收集", "部分失败策略"], ["先写失败测试复现Tool空名称", "实现聚合执行器并回归"], ["n4不再因空工具失败", "至少5个聚合测试", "能讲清根因和修复"], "Aggregate修复与测试"),
            (26, "Race Strategy", ["Race Group", "first-success-wins", "失败与取消语义"], ["测试先失败后成功、超时后成功、全部失败", "检查竞速后下游是否释放"], ["失败最快者不能获胜", "剩余任务有合理终态", "下游依赖不会永久Pending"], "Race测试集"),
            (27, "修复Planner重复节点", ["_plan调用逻辑", "列表extend位置", "重复ID防御"], ["注册两个search工具复现问题", "修复循环内重复追加并补测试"], ["计划节点数量正确", "TaskGraph拒绝重复ID", "能解释Planner与Runtime边界"], "Planner修复与测试"),
            (28, "DAG周验收", ["异常、超时、失败传播", "测试回归", "口述训练"], ["运行Demo和全部DAG测试", "录制5分钟白板讲解"], ["Demo无非预期失败", "能现场增加一个工具节点", "20道DAG问题答对80%"], "DAG验收报告"),
        ],
        "milestone": "修复Aggregate和重复节点；Demo稳定；能白板讲Kahn、Runtime状态、Race和失败传播。",
    },
    {
        "week": 5,
        "title": "FastAPI、真实流式与RAG闭环",
        "goal": "把算法原型提升为可调用的Agent后端，并完成至少一个真实可验证的文档检索闭环。",
        "days": [
            (29, "FastAPI基础", ["路由、请求模型", "Pydantic校验", "状态码与异常"], ["实现/health和/chat", "使用curl或Swagger调用"], ["接口输入有Schema", "错误返回结构一致", "业务逻辑不堆在路由中"], "FastAPI最小服务"),
            (30, "SSE与Queue", ["StreamingResponse", "SSE事件格式", "asyncio.Queue生产消费"], ["实现每秒输出一条事件", "客户端断开后停止生产者"], ["事件实时到达", "有结束哨兵和异常事件", "能解释SSE与WebSocket区别"], "SSE示例"),
            (31, "改造chat_stream", ["当前完成后回放问题", "Runtime事件生产", "请求取消"], ["用Queue改为真流式", "慢工具验证时间戳"], ["任务完成前收到node_start/node_done", "断连释放资源", "异常不会吞掉"], "真实/chat/stream"),
            (32, "RAG入库基础", ["文档解析", "Chunk与Overlap", "doc_id和chunk_id"], ["读取TXT/Markdown并切片", "保存Chunk及来源元数据"], ["能解释切片取舍", "每块可追溯来源", "删除能按doc_id定位"], "document_ingest.py"),
            (33, "Embedding与向量召回", ["向量与余弦相似度", "Top-K", "本地向量库或内存检索"], ["为Chunk生成向量", "实现问题→Top-K结果"], ["至少一个真实检索闭环", "结果包含分数和来源", "能解释召回错误原因"], "vector_search.py"),
            (34, "BM25与RRF", ["关键词检索价值", "RRF公式", "k和权重"], ["手算A/B/C文档RRF", "实现向量+关键词两路融合"], ["能写出RRF公式", "不直接相加异构分数", "单路失败可降级"], "hybrid_search.py"),
            (35, "RAG周验收", ["检索上下文拼接", "引用来源", "小型评测集"], ["准备20个问题及期望文档", "统计Recall@K并记录失败案例"], ["回答能展示来源", "20题评测可重复", "能提出至少3项改进"], "RAG评测报告"),
        ],
        "milestone": "拥有FastAPI同步/流式接口和真实RAG闭环；能用20题评测集说明检索效果，而非只展示代码。",
    },
    {
        "week": 6,
        "title": "记忆、持久化、安全、可观测性与面试",
        "goal": "补齐项目可信度：数据可保存、用户不串线、执行可追踪、测试可运行、面试能讲清。",
        "days": [
            (36, "聊天历史与长期记忆", ["原始对话与抽取记忆", "短期、长期、偏好、图记忆", "写入条件"], ["阅读memory.py", "为一段对话抽取可保存记忆"], ["能区分五类状态数据", "不把全部聊天写入长期记忆", "能解释记忆污染"], "记忆分类图"),
            (37, "记忆去重与冲突", ["余弦相似度", "importance与衰减", "quarantine与superseded"], ["测试重复记忆", "处理喜欢Java→现在使用Python冲突"], ["旧事实被替代但可审计", "阈值有解释", "召回过滤隔离内容"], "记忆冲突测试"),
            (38, "SQLite/PostgreSQL持久化", ["表、主键、索引", "Repository职责", "启动恢复"], ["先用SQLite保存对话和记忆", "服务重启后重新加载"], ["数据重启不丢", "SQL不散落业务层", "能解释事务基本作用"], "持久化Repository"),
            (39, "多用户隔离", ["user_id/tenant_id", "查询过滤", "缓存和向量过滤"], ["写用户A不能召回用户B数据测试", "检查所有Repository方法"], ["隔离由后端强制", "测试覆盖读写", "日志避免泄露敏感内容"], "多用户隔离测试"),
            (40, "沙箱与Prompt Injection", ["黑名单局限", "最小权限", "工具白名单与参数校验"], ["阅读sandbox.py和DockerExecutor", "增加10种危险输入测试但不执行危险命令"], ["能解释Docker不是绝对安全", "高风险工具需要授权", "知道断网/只读/cap-drop作用"], "安全测试报告"),
            (41, "日志、测试与README", ["task_id/node_id/user_id", "耗时与错误", "单元/集成/端到端"], ["加入结构化日志", "运行全部测试并重写启动说明"], ["能按task_id还原执行", "pytest一条命令运行", "新环境能按README启动"], "回归报告与README"),
            (42, "最终演示与模拟面试", ["30秒/1分钟/3分钟介绍", "项目边界", "现场编码"], ["完整演示上传→检索→DAG→流式回答", "30分钟新增工具并补测试"], ["25道核心问题答对80%", "简历每项都能指向代码证据", "能说3个优点、3个不足、下一步"], "最终演示包与面试录音"),
        ],
        "milestone": "项目可运行、可测试、可追踪、可演示；具备初级AI Agent实习岗位项目面试的基础。",
    },
]


def add_day(doc, day):
    number, title, learn, practice, mastery, deliverable = day
    h = heading(doc, f"第 {number} 天｜{title}", 2)
    h.paragraph_format.space_before = Pt(5)
    rows = [
        ("学习", join_items(learn)),
        ("练习", join_items(practice)),
        ("掌握标准", "；".join("□ " + item for item in mastery) + "。"),
        ("当天交付", deliverable),
    ]
    table = doc.add_table(rows=0, cols=2)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for idx, (label, value) in enumerate(rows):
        cells = table.add_row().cells
        cells[0].width = Cm(2.2)
        cells[1].width = Cm(15.0)
        shade(cells[0], LIGHT_BLUE if idx < 3 else GREEN)
        cells[0].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        p = cells[0].paragraphs[0]
        p.paragraph_format.space_after = Pt(0)
        r = p.add_run(label)
        set_font(r, size=9.2, bold=True, color=NAVY)
        p = cells[1].paragraphs[0]
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.06
        r = p.add_run(value)
        set_font(r, size=9.05)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


def build():
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Cm(1.6)
    section.bottom_margin = Cm(1.5)
    section.left_margin = Cm(1.8)
    section.right_margin = Cm(1.8)
    section.header_distance = Cm(0.7)
    section.footer_distance = Cm(0.7)

    normal = doc.styles["Normal"]
    normal.font.name = "微软雅黑"
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")
    normal.font.size = Pt(10)
    normal.paragraph_format.space_after = Pt(3)
    normal.paragraph_format.line_spacing = 1.12

    for style_name, size, color in [
        ("Title", 24, NAVY),
        ("Heading 1", 17, NAVY),
        ("Heading 2", 12.5, BLUE),
        ("Heading 3", 11, NAVY),
    ]:
        style = doc.styles[style_name]
        style.font.name = "微软雅黑"
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor.from_string(color)

    # Cover
    for _ in range(4):
        doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Python 到 AI Agent")
    set_font(r, size=27, bold=True, color=NAVY)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("42 天逐日学习路线")
    set_font(r, size=22, bold=True, color=BLUE)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(20)
    r = p.add_run("适用起点：已经学习到Python函数｜目标：能够理解、完善并面试讲解dan")
    set_font(r, size=11, color=GRAY)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(80)
    r = p.add_run("建议投入：每天3～4小时｜6周｜每7天完成一个可验证里程碑")
    set_font(r, size=10.5, color=GRAY)

    doc.add_page_break()
    heading(doc, "路线使用说明", 1)
    add_callout(
        doc,
        "核心原则",
        "每天必须产生代码、测试、图或录音之一。不要以“看完视频”作为完成标准；只有关掉资料能写、出现错误能调试、面对追问能解释，才算真正掌握。",
        GREEN,
    )
    heading(doc, "每天固定时间安排", 2)
    add_table(
        doc,
        ["阶段", "时间", "具体做法"],
        [
            ("复习", "20分钟", "不看资料复述昨天内容，重新写一个关键函数"),
            ("学习", "50分钟", "只学习当天列出的概念，记录不理解的问题"),
            ("跟练", "40分钟", "跟随示例敲一遍，禁止复制粘贴整段"),
            ("独立练习", "70分钟", "关掉资料重新实现，主动增加边界和异常"),
            ("测试与复盘", "30分钟", "运行测试、记录错误、用自己的话讲3分钟"),
        ],
        [3.0, 2.5, 11.5],
    )
    heading(doc, "学习时的五级标准", 2)
    add_table(
        doc,
        ["等级", "表现", "是否算完成"],
        [
            ("1 看过", "知道这个名词", "否"),
            ("2 看懂", "看别人代码觉得合理", "否"),
            ("3 会写", "关掉资料能写出核心代码", "基本完成"),
            ("4 会调试", "出错能定位、解释并修复", "真正掌握"),
            ("5 会讲", "能解释为什么这样设计及其缺点", "面试水平"),
        ],
        [2.5, 10.0, 4.5],
    )
    heading(doc, "暂时不要优先学习", 2)
    for item in [
        "LangChain/LangGraph框架细节：先掌握函数、类、Asyncio和Agent主循环。",
        "Milvus、Neo4j、Kafka复杂部署：先完成一个本地真实RAG闭环。",
        "多Agent、MCP、微调、Kubernetes：属于核心项目稳定后的加分项。",
        "大量背面试题：应先用代码和测试建立理解，再整理回答。",
    ]:
        add_bullet(doc, item)

    heading(doc, "6周总览", 2)
    add_table(
        doc,
        ["周", "主题", "核心交付"],
        [(f"第{w['week']}周", w["title"], w["milestone"]) for w in weeks],
        [2.2, 5.0, 10.0],
    )

    for week in weeks:
        doc.add_page_break()
        heading(doc, f"第 {week['week']} 周｜{week['title']}", 1)
        add_callout(doc, "本周目标", week["goal"], LIGHT_BLUE)
        for day in week["days"]:
            add_day(doc, day)
        add_callout(doc, "本周里程碑", week["milestone"], GREEN)

    doc.add_page_break()
    heading(doc, "最终验收清单", 1)
    sections = {
        "Python基础": [
            "能独立使用列表、字典、函数、类、dataclass、Enum和类型注解。",
            "能将一个200行程序拆分为模型、服务、入口和测试。",
            "能阅读Traceback并定位常见导入、类型和异常问题。",
        ],
        "Asyncio与DAG": [
            "能解释协程、Task、gather、wait、Semaphore、超时和取消。",
            "能手写Kahn算法伪代码并计算任务图入度。",
            "能解释Race的first-success、失败传播和下游释放。",
        ],
        "Agent与RAG": [
            "能独立写一个带3个工具的最小Agent。",
            "能画出LLM请求、工具调用和最终回答链路。",
            "能完成真实文档切片、向量召回、RRF融合和引用返回。",
        ],
        "工程与面试": [
            "FastAPI同步和SSE流式接口可运行。",
            "聊天和记忆可持久化，多用户数据不串线。",
            "全部测试可一条命令运行，README能指导新环境启动。",
            "能3分钟介绍项目，并准确说明已完成与未完成部分。",
        ],
    }
    for title, items in sections.items():
        heading(doc, title, 2)
        for item in items:
            add_bullet(doc, item, checkbox=True)

    heading(doc, "项目面试25问", 1)
    questions = [
        "Agent和普通LLM聊天有什么区别？",
        "Tool Calling的完整流程是什么？",
        "为什么LLM输出必须做Schema和权限校验？",
        "Planner与Runtime各自负责什么？",
        "为什么使用DAG而不是完全串行ReAct？",
        "Kahn算法如何工作，复杂度是多少？",
        "如何检测环、悬空依赖和重复节点ID？",
        "Asyncio适合什么场景，为什么不能加速CPU计算？",
        "gather和wait有什么区别？",
        "如何限制最大并发？",
        "如何处理工具超时和任务取消？",
        "first-completed和first-success有什么区别？",
        "上游节点失败后，下游应该怎样处理？",
        "当前项目Aggregate节点原来为什么失败？",
        "RAG文档入库和查询分别经过哪些步骤？",
        "Chunk大小和Overlap如何影响效果？",
        "向量检索和BM25分别适合什么场景？",
        "为什么不同检索分数不能直接相加？",
        "写出RRF公式并解释k。",
        "如何评价RAG召回质量？",
        "聊天历史和长期记忆有什么区别？",
        "如何防止不同用户的记忆串线？",
        "SSE如何实现真正的实时流式？",
        "Docker沙箱为什么不是绝对安全？",
        "当前项目最重要的三个不足和下一步是什么？",
    ]
    for q in questions:
        add_bullet(doc, q, checkbox=True)

    heading(doc, "每日复盘模板", 1)
    for text in [
        "今天关掉资料后，我能独立写出的内容：____________________________",
        "今天遇到的错误、根因和修复：__________________________________",
        "今天仍然说不清的概念：________________________________________",
        "今天的代码/测试/图/录音交付物：_______________________________",
        "明天开始前必须重新写一遍的函数：______________________________",
    ]:
        p = doc.add_paragraph(text)
        p.paragraph_format.space_after = Pt(9)

    # Header and footer
    for sec in doc.sections:
        hp = sec.header.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        r = hp.add_run("Python到AI Agent｜42天逐日学习路线")
        set_font(r, size=8, color=GRAY)
        fp = sec.footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = fp.add_run("第 ")
        set_font(r, size=8, color=GRAY)
        begin = OxmlElement("w:fldChar")
        begin.set(qn("w:fldCharType"), "begin")
        instr = OxmlElement("w:instrText")
        instr.set(qn("xml:space"), "preserve")
        instr.text = "PAGE"
        end = OxmlElement("w:fldChar")
        end.set(qn("w:fldCharType"), "end")
        r._r.append(begin)
        r._r.append(instr)
        r._r.append(end)
        r = fp.add_run(" 页")
        set_font(r, size=8, color=GRAY)

    doc.core_properties.title = "Python到AI Agent 42天逐日学习路线"
    doc.core_properties.subject = "从Python函数到dan项目与AI Agent面试"
    doc.core_properties.author = "Codex"
    doc.core_properties.keywords = "Python, Asyncio, DAG, AI Agent, RAG, 学习路线"
    doc.save(OUT)
    print(OUT)


if __name__ == "__main__":
    build()
