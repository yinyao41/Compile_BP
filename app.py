# -*- coding: utf-8 -*-
import streamlit as st
import requests
from docx import Document
from io import BytesIO
from openai import OpenAI
import os

# =============================================================================
# 配置区
# =============================================================================
GITHUB_USERNAME = "yinyao41"
GITHUB_REPO = "Company_transformation"
BRANCH = "master"

TEMPLATE_FILES = [
    "data/政府BP模板.docx",
    "data/政府BP提示词.docx",
]

# =============================================================================
# 精简系统提示词（关键修复：不再嵌入几千字模板）
# =============================================================================
SYSTEM_PROMPT = """你是一位资深的政府产业基金投资决策顾问与商业计划书撰写专家。
请严格按照「政府BP提示词.docx」中的 10 章标准结构、输出格式、语言风格和所有铁律要求，
为用户提供的项目生成一份完整、可直接提交的政府项目商业计划书（BP）及落地方案。
输出必须使用 Markdown 格式，包含一页纸决策单 + 完整 10 章 BP + 详细落地方案。
所有关键数据使用用户提供的真实信息，不得编造。
现在请开始生成。"""

# =============================================================================
# 阿里通义千问客户端
# =============================================================================
DASHSCOPE_API_KEY = st.secrets.get("DASHSCOPE_API_KEY", os.getenv("DASHSCOPE_API_KEY"))
if not DASHSCOPE_API_KEY:
    st.error("缺少 DASHSCOPE_API_KEY！请在 Streamlit Secrets 中添加")
    st.stop()

client = OpenAI(
    api_key=DASHSCOPE_API_KEY,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

MODEL_NAME = "qwen-max"

# =============================================================================
# 加载模板（静默 + 强力截断）
# =============================================================================
@st.cache_data(show_spinner="正在准备模板...")
def load_templates():
    templates = []
    for rel_path in TEMPLATE_FILES:
        raw_url = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{GITHUB_REPO}/{BRANCH}/{rel_path}"
        try:
            r = requests.get(raw_url, timeout=12)
            r.raise_for_status()
            doc = Document(BytesIO(r.content))
            text = "\n".join(p.text.strip() for p in doc.paragraphs if p.text.strip())
            if text:
                name = rel_path.split("/")[-1].replace(".docx", "")
                templates.append(f"【{name}】\n{text}\n{'─' * 60}\n")
        except:
            continue
    full_text = "".join(templates)
    if len(full_text) > 15000:          # 更严格截断
        full_text = full_text[:15000] + "\n\n【模板已自动截断】"
    return full_text

TEMPLATES_TEXT = load_templates()

# =============================================================================
# Streamlit 界面
# =============================================================================
st.set_page_config(page_title="政府项目BP自动生成器", layout="wide")
st.title("📋 政府项目BP & 落地方案自动生成器")

with st.form(key="bp_form"):
    company_name = st.text_input("申报主体名称*", placeholder="例：山东固丰体育产业有限公司")
    project_name = st.text_input("项目名称*", placeholder="例：智能制造升级改造项目")
    target_region = st.text_input("目标申报地区*", placeholder="例：某市高新区")
    industry = st.text_input("所属产业领域", placeholder="例：新能源")
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
                st.warning("补充文件解析失败，将使用文字描述")

        user_context = f"""
申报主体：{company_name}
项目名称：{project_name}
目标地区：{target_region}
所属产业：{industry}
总投资额：{total_investment}万元
项目基本情况：{current_status}
补充材料：{extra_text}
"""

        with st.spinner("正在生成专业政府BP（约30-60秒）..."):
            try:
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT + "\n\n以下是政府BP提示词模板全文：\n" + TEMPLATES_TEXT},
                        {"role": "user", "content": f"请严格按照模板格式，为以下项目生成完整BP和落地方案：\n{user_context}"}
                    ],
                    temperature=0.25,
                    max_tokens=2800,          # 关键修复：降低防止超限
                    stream=False
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
                error_str = str(e).lower()
                if "context length" in error_str or "maximum" in error_str:
                    st.error("提示词过长，请简化项目描述后重试")
                else:
                    st.error(f"生成失败：{str(e)}")
