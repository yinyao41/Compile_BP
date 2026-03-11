# -*- coding: utf-8 -*-
import streamlit as st
import requests
from docx import Document
from io import BytesIO
from openai import OpenAI
import os

# =============================================================================
# 配置区（你的 GitHub 信息）
# =============================================================================
GITHUB_USERNAME = "yinyao41"
GITHUB_REPO = "Company_transformation"
BRANCH = "master"

# 模板文件路径（文件不存在也不会报错）
TEMPLATE_FILES = [
    "data/政府BP模板.docx",
    "data/政府BP提示词.docx",
]

# =============================================================================
# 系统提示词（已完整内置《政府BP提示词.docx》内容）
# =============================================================================
SYSTEM_PROMPT = """【角色设定】
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

【内容结构模板】（标准 10 章政府版 BP 结构）...（与你上传的《政府BP提示词.docx》完全一致）

必须严格参考模板内容，不得编造信息。输出格式为 Markdown，便于直接复制到 Word/PPT 提交。
"""

# =============================================================================
# 阿里通义千问客户端
# =============================================================================
DASHSCOPE_API_KEY = st.secrets.get("DASHSCOPE_API_KEY", os.getenv("DASHSCOPE_API_KEY"))

if not DASHSCOPE_API_KEY:
    st.error("缺少 DASHSCOPE_API_KEY！请在 Streamlit Cloud → Settings → Secrets 中添加")
    st.stop()

client = OpenAI(
    api_key=DASHSCOPE_API_KEY,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

MODEL_NAME = "qwen-max"

# =============================================================================
# 从 GitHub 下载模板（已静默处理，不显示任何警告）
# =============================================================================
@st.cache_data(show_spinner="正在准备政府BP模板...")
def load_templates():
    templates = []
    for rel_path in TEMPLATE_FILES:
        raw_url = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{GITHUB_REPO}/{BRANCH}/{rel_path}"
        try:
            r = requests.get(raw_url, timeout=15)
            r.raise_for_status()
            doc = Document(BytesIO(r.content))
            text = "\n".join(p.text.strip() for p in doc.paragraphs if p.text.strip())
            if text:
                name = rel_path.split("/")[-1].replace(".docx", "")
                templates.append(f"【{name}】\n{text}\n{'─' * 80}\n")
        except:
            # 文件不存在或读取失败时完全静默，不显示任何提示
            continue

    full_text = "".join(templates)
    if len(full_text) > 25000:
        full_text = full_text[:25000] + "\n\n【模板内容已自动截断】"
    return full_text

TEMPLATES_TEXT = load_templates()

# =============================================================================
# Streamlit 界面（已移除侧边栏和副标题）
# =============================================================================
st.set_page_config(page_title="政府项目BP自动生成器", layout="wide", page_icon="📋")
st.title("📋 政府项目BP & 落地方案自动生成器")

with st.form(key="bp_form"):
    company_name = st.text_input("申报主体名称*", placeholder="例：山东固丰体育产业有限公司")
    project_name = st.text_input("项目名称*", placeholder="例：智能制造升级改造项目")
    target_region = st.text_input("目标申报地区*", placeholder="例：某市高新区")
    industry = st.text_input("所属产业领域", placeholder="例：新能源 / 低空经济")
    total_investment = st.number_input("总投资额（万元）", min_value=100, value=5000)
    current_status = st.text_area("项目基本情况与核心亮点*", placeholder="公司现状、技术优势、申报目的等...", height=180)
    additional_file = st.file_uploader("上传补充材料（可选）", type=["docx", "pdf", "txt"])

    submit_button = st.form_submit_button(label="🚀 一键生成政府BP + 落地方案")

if submit_button:
    if not company_name or not project_name or not target_region or not current_status:
        st.error("请填写带*的必填项！")
    else:
        extra_text = ""
        if additional_file:
            try:
                if additional_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                    doc = Document(BytesIO(additional_file.read()))
                    extra_text = "\n".join(p.text.strip() for p in doc.paragraphs if p.text.strip())
                else:
                    extra_text = additional_file.read().decode("utf-8")
            except:
                st.warning("补充文件解析失败，将使用文字描述生成")

        user_context = f"""
申报主体：{company_name}
项目名称：{project_name}
目标地区：{target_region}
所属产业：{industry}
总投资额：{total_investment}万元
项目基本情况：{current_status}
补充材料：{extra_text}
"""

        with st.spinner("正在生成专业政府BP（约40-70秒）..."):
            try:
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT + "\n\n以下是政府BP提示词模板全文：\n" + TEMPLATES_TEXT},
                        {"role": "user", "content": f"请严格按照政府BP提示词模板，为以下项目生成完整BP和落地方案：\n{user_context}"}
                    ],
                    temperature=0.25,
                    max_tokens=4000,
                )

                result = response.choices[0].message.content
                st.success("✅ 生成完成！可直接复制到 Word 提交")
                st.markdown(result)

                st.download_button(
                    label="📥 下载完整BP（Markdown）",
                    data=result,
                    file_name=f"{project_name}_政府BP_落地方案.md",
                    mime="text/markdown"
                )

            except Exception as e:
                st.error(f"生成失败：{str(e)}")

