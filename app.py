# -*- coding: utf-8 -*-
import streamlit as st
import requests
from docx import Document
from io import BytesIO
from openai import OpenAI
import os
import time

# =============================================================================
# 配置区（只读取政府BP提示词.docx）
# =============================================================================
GITHUB_USERNAME = "yinyao41"
GITHUB_REPO = "Company_transformation"
BRANCH = "master"

# 只读取这个文件作为模板
TEMPLATE_FILE = "data/政府BP提示词.docx"

# =============================================================================
# 系统提示词（强制按照提示词文件格式输出纯文本）
# =============================================================================
SYSTEM_PROMPT = """你是一位政府项目BP撰写专家。
请严格按照「政府BP提示词.docx」中的10章标准结构、标题层级（零、一、（一）、1.（1））、语言风格和所有要求，
为用户项目生成一份完整、可直接提交的商业计划书（BP）及落地方案。
输出必须是纯文本（不要使用任何Markdown符号，如#、**、-、|等）。
一级标题前后使用 === 加粗，例如：
================== 一、项目概述 ==================

必须包含：
- 一页纸决策单（首页）
- 完整10章BP
- 详细落地方案（时间表、资金计划、政策诉求、风险对冲）

使用用户提供的真实信息，不得编造或省略任何章节。
现在立即开始生成纯文本报告。"""

# =============================================================================
# 客户端（最快模型）
# =============================================================================
DASHSCOPE_API_KEY = st.secrets.get("DASHSCOPE_API_KEY", os.getenv("DASHSCOPE_API_KEY"))
if not DASHSCOPE_API_KEY:
    st.error("缺少 DASHSCOPE_API_KEY！请在 Streamlit Secrets 中添加")
    st.stop()

client = OpenAI(
    api_key=DASHSCOPE_API_KEY,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

MODEL_NAME = "qwen-turbo"

# =============================================================================
# 只加载政府BP提示词.docx（截断到8000字符）
# =============================================================================
@st.cache_data(show_spinner="正在加载政府BP提示词模板...")
def load_template():
    raw_url = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{GITHUB_REPO}/{BRANCH}/{TEMPLATE_FILE}"
    try:
        r = requests.get(raw_url, timeout=8)
        r.raise_for_status()
        doc = Document(BytesIO(r.content))
        text = "\n".join(p.text.strip() for p in doc.paragraphs if p.text.strip())
        if not text:
            st.error("模板文件内容为空！")
            st.stop()
        if len(text) > 8000:
            text = text[:8000] + "\n[模板内容已截断以确保60秒内生成完整报告]"
        return text
    except Exception as e:
        st.error(f"加载模板失败：{str(e)}")
        st.stop()

TEMPLATE_TEXT = load_template()

# =============================================================================
# Streamlit 界面
# =============================================================================
st.set_page_config(page_title="政府项目BP生成器", layout="wide")
st.title("政府项目BP & 落地方案生成器（限时60秒）")

with st.form(key="bp_form"):
    company_name = st.text_input("申报主体名称*", placeholder="例：山东固丰体育产业有限公司")
    project_name = st.text_input("项目名称*", placeholder="例：智能制造升级改造项目")
    target_region = st.text_input("目标申报地区*", placeholder="例：某市高新区")
    industry = st.text_input("所属产业领域", placeholder="例：新能源")
    total_investment = st.number_input("总投资额（万元）", min_value=100, value=5000)
    current_status = st.text_area("项目基本情况与核心亮点*", height=140)
    additional_file = st.file_uploader("上传补充材料（可选）", type=["docx", "pdf", "txt"])

    submit_button = st.form_submit_button("生成BP & 落地方案（60秒内完成）")

if submit_button:
    if not company_name or not project_name or not target_region or not current_status:
        st.error("请填写带*的必填项！")
    else:
        extra_text = ""
        if additional_file:
            try:
                if additional_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                    doc = Document(BytesIO(additional_file.read()))
                    extra_text = "\n".join(p.text.strip() for p in doc.paragraphs if p.text.strip())[:1500]
                else:
                    extra_text = additional_file.read().decode("utf-8")[:1500]
            except:
                st.warning("文件解析失败，仅使用文字描述")

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
        with st.spinner("正在生成完整BP（限时60秒）..."):
            try:
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT + "\n\n政府BP提示词模板全文：\n" + TEMPLATE_TEXT},
                        {"role": "user", "content": f"请严格按照模板格式，为以下项目生成完整BP及落地方案（纯文本，一级标题加粗）：\n{user_context}"}
                    ],
                    temperature=0.3,
                    max_tokens=1400,
                    stream=False
                )
                result = response.choices[0].message.content

                elapsed = time.time() - start_time
                if elapsed > 58:
                    st.warning("生成接近超时，但已尽力输出完整报告")
                st.success(f"生成完成！（耗时 {elapsed:.1f} 秒）")
                st.text(result)  # 纯文本显示

                st.download_button(
                    label="下载完整报告（纯文本）",
                    data=result,
                    file_name=f"{project_name}_政府BP_落地方案.txt",
                    mime="text/plain"
                )

            except Exception as e:
                if time.time() - start_time > 58:
                    st.error("生成超时（超过60秒），请简化描述或减少补充材料后重试")
                else:
                    st.error(f"生成失败：{str(e)}")
