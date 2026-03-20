# -*- coding: utf-8 -*-
import streamlit as st
import os
from io import BytesIO
import time
from openai import OpenAI

# 初始化通义千问 client
api_key = os.getenv("DASHSCOPE_API_KEY")
if not api_key:
    st.error("未找到环境变量 DASHSCOPE_API_KEY，请在 Streamlit Cloud Secrets 中设置")
    st.stop()

client = OpenAI(
    api_key=api_key,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

MODEL_NAME = "qwen-max"          # 建议升级到 qwen-max 或 qwen-plus，更适合长结构化输出
MAX_GENERATION_SECONDS = 180     # 内容更复杂，适当放宽时间
MAX_TOKENS = 8000                # 需要更长的输出长度
TEMPERATURE = 0.15               # 降低创造性，更严格遵循模板

# ────────────────────────────────────────────────
#  核心提示词 —— 直接使用你上传文档中的完整内容
# ────────────────────────────────────────────────
GOV_BP_SYSTEM_PROMPT = """【角色设定】
你是一位资深的政府产业基金投资决策顾问与商业计划书撰写专家，擅长将技术型企业的商业方案转化为符合政府招商逻辑、产业基金评审标准的 BP 文档。你深谙 2024-2025 年政府投资关注的核心：产业链补链强链与供应链安全、财政资金安全退出机制、落地可行性、亩均税收贡献、固定资产投资强度、国产替代价值及 ESG 合规。

【任务目标】
基于用户上传的项目附件材料，撰写一份面向 [目标地区，如：某市/某高新区] 政府及产业投资机构的《商业计划书结构化提纲》（含完整落地实施计划）。该提纲为通用框架，可转化为 PPT、Word 或 PDF 格式，用于政府评审会、基金投决会或招商路演。

【输入材料分析框架】
请从附件中提取以下关键信息并填入对应占位符：
- 项目主体：[实施主体名称]（母公司）+ [项目公司 Name]（SPV 主体）
- 所属产业：[如：新能源/集成电路/生物医药/高端装备/低空经济/新材料]
- 技术路线：[核心技术 1] + [核心技术 2]，双轨并行/单点突破
- 核心产品：[产品名称]，[市场定位，如：国内首创/进口替代/行业首创/解决卡脖子]
- 负责人：[负责人姓名]（[核心履历标签，如：20 年行业经验/院士/国家级人才/上市公司高管]）
- 合作方：[技术合作方/订单合作方]（[合作模式，如：技术入股+订单对赌]）
- 融资计划：总投资[金额]亿，一期[金额]亿（出让[比例]%股权），其中申请政府引导基金[金额]亿（占股[比例]%，[投资方式，如：优先股/名股实债]，[保底收益率]%保底收益+优先退出）
- 落地计划：[开工年份]年建设[产能/产线]，[达产年份]年满产，[扩产年份]年二期扩产
- 产业链地位：[在产业链中的位置，如：上游材料/中游制造/下游应用]，填补[地区]产业空白

【占位符使用规范】
全文使用以下占位符标记需根据附件填写的关键数据：
[投资总额]、[一期投资]、[政府申请金额]、[出让股权比例]、[建设周期]、[达产年产值]、[达产年税收]、[亩均税收]、[直接就业人数]、[核心技术指标]、[关键时间节点]、[合作方名称]、[订单保底金额]、[目标地区]、[国产替代对象]、[卡脖子环节]

【输出格式要求】
1. 生成结构化的商业计划书提纲（标题层级：零、一、（一）、1.（1）），可直接用于制作 PPT 或排版为 Word/PDF
2. 每个章节标题后附【内容要点提示】，说明该部分需撰写的核心论点
3. 所有关键数据使用[]标注，提醒后续替换为实际数值
4. 落地计划章节需包含具体的时间表（季度维度）、责任主体、里程碑成果、需政府配合事项
5. 政府诉求章节需明确列出"需要政府提供的具体支持事项"（资金、土地、订单、政策）及替代方案
6. 使用 Markdown 格式输出：
   - 一级标题：一、二、三...（使用 # ）
   - 二级标题：（一）（二）（三）...（使用 ## ）
   - 三级标题：1. 2. 3.（使用 ### ）
   - 四级标题：（1）（2）（3）...（使用 #### ）
   - 表格使用 Markdown 表格语法
7. 语气正式、数据导向、专业，充满政府招商常用术语（补链强链、亩均税收、当年开工当年投产、标准地出让、容缺受理、新质生产力等）

请严格按照下面【内容结构模板】的章节顺序和层级输出，不要增删章节，不要改变顺序，不要写多余的开头结尾说明，直接开始输出。

【内容结构模板】（标准 10 章政府版 BP 结构）

零、 Executive Summary / 项目决策摘要（One-Page Summary）
   【内容要点：政府领导 3 分钟决策版，放在最前但建议最后写】
   （一）核心数据速览（投资三问：投多少？赚多少？风险多大？）
   （二）一句话价值定位（30 秒电梯演讲）
   （三）战略卡位与供应链安全价值
   （四）决策建议

一、 项目概述与战略价值（政府决策依据）
   （一）项目基本信息表（政府"一键看板"）
   （二）政府投资价值亮点（5 大核心卖点）
   （三）战略契合度分析

二、 市场分析：万亿级赛道与供应链安全
   （一）行业痛点与国产替代刚需
   （二）技术趋势与竞争格局
   （三）[目标地区]产业基础与供应链缺口

三、 技术实力与产品壁垒
   （一）技术路线与成熟度（降低政府投资风险）
   （二）核心壁垒与首创性（3 个首创点）
   （三）供应链安全价值（新增，国产替代叙事）
   （四）产学研体系与团队

四、 产业化落地实施计划（核心章节，占全文 30%篇幅）
   （一）总体实施路径图（[起始年]-[结束年]三阶段）
   （二）一期项目落地时间表（[年份]年 Q1-Q4，投资[金额]亿）
   （三）二期扩产计划（[年份]-[年份]，投资[金额]亿）
   （四）供应链本地化与人才落地

五、 商业模式与财务预测
   （一）商业模式（B2B+B2G 双轮驱动）
   （二）财务预测与税收贡献（保守估算）
   （三）政府投资安全保障条款（可执行清单，重点章节）

六、 产业带动与社会效益（政府 KPI 导向）
   （一）产业链集聚效应（招商价值）
   （二）就业与税收贡献
   （三）技术创新与标准建设
   （四）ESG 与双碳贡献（新增，政府关切，否决项）
   （五）城市品牌与示范效应

七、 政策支持诉求与替代方案（具体可执行清单）
   （一）资金支持（一期[金额]亿构成）
   （二）落地保障（要素供给）
   （三）市场与应用场景支持（B2G 订单，关键诉求）
   （四）人才与研发支持
   （五）投资替代方案（Plan B，如政府资金紧张时的灵活方案，新增）

八、 风险分析与防控措施（打消政府顾虑，体现专业性）
   （一）技术风险
   （二）市场风险
   （三）资金风险
   （四）政策与合规风险
   （五）团队风险

九、 投资结论与下一步行动计划
   （一）项目综合评价（五星评分制，客观评估）
   （二）政府投资建议
   （三）Immediate Action Plan（3 个月落地路线图）

现在根据用户提供的项目信息和上传的补充材料，严格按照以上结构和 Markdown 格式要求，输出完整的结构化商业计划书提纲。
不要输出任何前言、说明、道歉，直接从「零、 Executive Summary」开始。
"""

st.title("政府产业投资 BP 生成工具（结构化提纲版）")

with st.form("project_form"):
    company_name = st.text_input("申报主体*", placeholder="例：XX科技有限公司")
    project_name = st.text_input("项目名称*", placeholder="例：固态电池正极材料产业化项目")
    target_region = st.text_input("目标地区*", placeholder="例：济南高新区 / 青岛西海岸新区")
    industry = st.text_input("所属产业领域", placeholder="例：新能源、新材料、低空经济")
    
    total_investment = st.number_input(
        "总投资额（万元）",
        min_value=100.0,
        value=None,
        step=100.0,
        format="%.0f"
    )
    
    current_status = st.text_area(
        "项目基本情况与核心亮点*（越详细越好）",
        height=220
    )
    
    additional_file = st.file_uploader("上传项目详细材料（.docx / .pdf / .txt）*", 
                                      type=["docx", "pdf", "txt"], 
                                      help="请上传最核心的项目介绍、商业计划书草稿或技术资料")
    
    submit_button = st.form_submit_button("生成政府版 BP 结构化提纲")

if submit_button:
    required_fields = {
        "申报主体": company_name.strip(),
        "项目名称": project_name.strip(),
        "目标地区": target_region.strip(),
        "项目基本情况与核心亮点": current_status.strip(),
        "项目详细材料": additional_file
    }
    
    missing = [k for k, v in required_fields.items() if not v]
    if missing or total_investment is None:
        st.error("请填写所有带 * 的必填项")
        st.stop()

    # 读取上传文件内容
    extra_text = ""
    try:
        content = additional_file.read()
        file_type = additional_file.type
        
        if "officedocument.wordprocessingml" in file_type or file_type.endswith("docx"):
            from docx import Document
            doc = Document(BytesIO(content))
            extra_text = "\n".join([p.text.strip() for p in doc.paragraphs if p.text.strip()])[:3000]
        elif file_type == "application/pdf":
            # 如有 pdf 解析库可加，这里简单处理
            extra_text = "[PDF 内容已上传，但当前仅支持文本提取预览]\n" + str(content[:500])
        else:
            extra_text = content.decode("utf-8", errors="ignore")[:3000]
    except Exception as e:
        st.warning(f"文件解析出现问题：{str(e)}，将仅使用表单填写的信息")

    investment_str = f"{total_investment:,.0f}" if total_investment else "未填写"

    user_context = f"""\
目标地区：{target_region}
项目主体/申报单位：{company_name}
项目名称：{project_name}
所属产业：{industry}
计划总投资：{investment_str} 万元
项目基本情况与核心亮点：
{current_status}

【最重要参考材料】（请务必深度分析并提取关键数据填充所有 [占位符]）
{extra_text}
"""

    start_time = time.time()
    with st.spinner("正在生成符合政府投资逻辑的结构化 BP 提纲（可能需要 1-3 分钟）..."):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": GOV_BP_SYSTEM_PROMPT},
                    {"role": "user", "content": user_context + "\n\n请严格按照模板结构和 Markdown 格式要求输出完整提纲。"}
                ],
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS,
                stream=False
            )
            
            result = response.choices[0].message.content.strip()
            elapsed = time.time() - start_time
            
            if elapsed > MAX_GENERATION_SECONDS - 10:
                st.warning(f"生成耗时较长（{elapsed:.1f}秒），内容可能已截断，请检查完整性")
            
            st.success(f"生成完成（耗时 {elapsed:.1f} 秒）")
            
            st.markdown("### 生成结果（Markdown 渲染预览，可直接复制到 Word/PPT）")
            st.markdown("---")
            
            # 渲染 Markdown，支持表格、标题等
            st.markdown(result, unsafe_allow_html=True)
            
            st.markdown("---")
            
            # 下载按钮 - 提供原始 Markdown 文本
            safe_filename = f"{project_name.replace(' ', '_')}_{target_region or '未知地区'}"
            st.download_button(
                label="下载 Markdown 版（建议用 Typora / Obsidian / Word 打开）",
                data=result,
                file_name=f"{safe_filename}_政府BP提纲_{time.strftime('%Y%m%d')}.md",
                mime="text/markdown"
            )
            
            st.download_button(
                label="下载纯文本版（备用）",
                data=result,
                file_name=f"{safe_filename}_纯文本_{time.strftime('%Y%m%d')}.txt",
                mime="text/plain"
            )
            
        except Exception as e:
            elapsed = time.time() - start_time
            err_str = str(e).lower()
            if "timeout" in err_str or elapsed > MAX_GENERATION_SECONDS:
                st.error("生成超时，建议：\n1. 缩短补充材料长度\n2. 使用更强的模型（如 qwen-max）\n3. 分段生成或稍后重试")
            elif "token" in err_str or "limit" in err_str:
                st.error("输出长度超出模型限制，请减少补充材料字数或提高 max_tokens")
            else:
                st.error(f"生成失败：{str(e)}\n请检查 API Key、网络或联系管理员")
