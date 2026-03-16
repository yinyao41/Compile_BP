# -*- coding: utf-8 -*-
import streamlit as st
import requests
from docx import Document
from io import BytesIO
from openai import OpenAI
import os
import time

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
# 极简系统提示词（速度优化版）
# =============================================================================
SYSTEM_PROMPT = """你是一位资深的政府产业基金投资决策顾问。
请严格按照「政府BP提示词.docx」中的10章标准结构和政府语言风格，
为用户项目生成一份完整、可直接提交的BP及落地方案。
输出必须包含一页纸决策单 + 完整10章BP + 详细落地方案。
使用用户提供的真实信息，不得编造。
现在开始生成。"""

# =============================================================================
# 阿里通义千问客户端（使用最快模型）
# =============================================================================
DASHSCOPE_API_KEY = st.secrets.get("DASHSCOPE_API_KEY", os.getenv("DASHSCOPE_API_KEY"))
if not DASHSCOPE_API_KEY:
    st.error("缺少 DASHSCOPE_API_KEY！请在 Streamlit Secrets 中添加")
    st.stop()

client = OpenAI(
    api_key=DASHSCOPE_API_KEY,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

MODEL_NAME = "qwen-turbo"   # ← 关键优化：使用最快模型

# =============================================================================
# 加载模板（强力截断，保证速度）
# =============================================================================
@st.cache_data(show_spinner="正在准备模板...")
def load_templates():
    templates = []
    for rel_path in TEMPLATE_FILES:
        raw_url = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{GITHUB_REPO}/{BRANCH}/{rel_path}"
        try:
            r = requests.get(raw_url, timeout=10)
            r.raise_for_status()
            doc = Document(BytesIO(r.content))
            text = "\n".join(p.text.strip() for p in doc.paragraphs if p.text.strip())
            if text:
                name = rel_path.split("/")[-1].replace(".docx", "")
                templates.append(f"【{name}】\n{text}\n{'─' * 50}\n")
        except:
            continue
    full_text = "".join(templates)
    if len(full_text) > 12000:          # 严格控制长度
        full_text = full_text[:12000] + "\n\n【模板已截断以确保60秒内输出】"
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
    current_status = st.text_area("项目基本情况与核心亮点*", placeholder="公司现状、技术优势、申报目的等...", height=160)
    additional_file = st.file_uploader("上传补充材料（可选）", type=["docx", "pdf", "txt"])

    submit_button = st.form_submit_button(label="🚀 一键生成政府BP + 落地方案（限时60秒）")

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

        start_time = time.time()
        with st.spinner("正在生成专业政府BP（限时60秒）..."):
            try:
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT + "\n\n以下是政府BP提示词模板全文：\n" + TEMPLATES_TEXT},
                        {"role": "user", "content": f"请严格按照模板格式，为以下项目生成完整BP和落地方案：\n{user_context}"}
                    ],
                    temperature=0.3,
                    max_tokens=1800,          # 严格控制输出长度
                    stream=False
                )
                result = response.choices[0].message.content
                
                elapsed = time.time() - start_time
                st.success(f"✅ 生成完成！（耗时 {elapsed:.1f} 秒）")
                st.markdown(result)

                st.download_button(
                    label="📥 下载完整BP（Markdown）",
                    data=result,
                    file_name=f"{project_name}_政府BP_落地方案.md",
                    mime="text/markdown"
                )

            except Exception as e:
                if time.time() - start_time > 58:
                    st.error("生成超时（超过60秒），请简化描述后重试")
                else:
                    st.error(f"生成失败：{str(e)}")
