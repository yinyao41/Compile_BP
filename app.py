# -*- coding: utf-8 -*-
import streamlit as st
import requests
from docx import Document
from io import BytesIO
from openai import OpenAI
import os

# =============================================================================
# 配置区（请根据你的 GitHub 实际情况修改）
# =============================================================================
GITHUB_USERNAME = "yinyao41"          # 你的 GitHub 用户名
GITHUB_REPO = "Company_transformation"  # 你的仓库名（可改）
BRANCH = "master"

# 必须上传到 data/ 目录下的政府 BP 模板文件（已包含）
TEMPLATE_FILES = [
    "data/政府BP模板.docx",                    # ← 政府项目申报专用模板
    "data/山东固丰体育产业有限公司转型升级分析报告.docx",  # 可保留原模板做参考
]

# =============================================================================
# 系统提示词（严格基于政府BP模板，输出专业、可直接使用的BP+落地方案）
# =============================================================================
SYSTEM_PROMPT = """你是一位资深政府项目申报专家 + 商业计划书撰写专家。
你的全部知识仅来源于用户提供的《政府BP模板.docx》以及其他参考模板。

任务：根据用户输入的公司/项目信息，**严格按照政府BP模板结构**，自动生成一份完整、可直接提交的：
1. 政府项目商业计划书（BP）（8-12页标准结构）
2. 配套落地方案（实施路线图、资金使用计划、风险防控、绩效目标）

**必须严格遵循以下输出格式**（Markdown）：

### 第一部分：一页纸高管/申报决策单（首页）
- 项目名称
- 申报主体
- 申报额度
- 推荐方案一句话总结
- 核心亮点（3条）
- 预期效益（数字）
- 风险等级 & 对冲措施

### 第二部分：完整商业计划书（政府标准版）
1. 项目背景与必要性
2. 市场分析与需求预测
3. 技术/方案可行性
4. 实施主体基本情况
5. 建设内容与进度安排
6. 投资估算与资金筹措
7. 经济效益与社会效益分析
8. 风险分析与防控措施
9. 结论与建议

### 第三部分：落地方案（单独成章）
- 分阶段路线图（Gantt式表格）
- 资金使用计划表（分季度）
- 绩效目标与考核指标
- 组织保障与责任分工
- 立即行动清单（本月/下月可执行事项）

**铁律**：
- 所有数据必须使用用户提供的真实信息或合理推算（不得编造）
- 语言正式、规范、符合政府申报口径
- 必须包含量化指标（金额、时间、效益百分比）
- 输出必须是完整 Markdown，可直接复制到 Word 排版提交

现在开始，根据用户提供的信息生成上述完整报告。"""

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
# 从 GitHub 下载所有模板（含政府BP模板）
# =============================================================================
@st.cache_data(show_spinner="正在从 GitHub 下载政府BP模板...")
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
        except Exception as e:
            st.error(f"读取失败 {rel_path}：{str(e)}")
            continue

    if not templates:
        st.error("模板加载失败！请确保 data/ 文件夹内有「政府BP模板.docx」")
        st.stop()

    full_text = "".join(templates)
    # 自动截断防止超限
    if len(full_text) > 25000:
        full_text = full_text[:25000] + "\n\n【模板内容已自动截断以适配模型限制】"
    return full_text

TEMPLATES_TEXT = load_templates()

# =============================================================================
# Streamlit 界面
# =============================================================================
st.set_page_config(page_title="政府项目BP自动生成器", layout="wide", page_icon="📋")
st.title("📋 政府项目BP & 落地方案自动生成器")
st.caption("基于 GitHub 政府BP模板 · 通义千问驱动 · 一键生成可申报文件")

with st.form(key="bp_form"):
    company_name = st.text_input("申报主体名称", placeholder="例：山东固丰体育产业有限公司")
    project_name = st.text_input("项目名称", placeholder="例：智能制造升级改造项目")
    industry = st.text_input("所属行业/领域", placeholder="例：体育产业 / 新能源")
    funding_amount = st.number_input("计划申报资金（万元）", min_value=10, value=500)
    current_status = st.text_area("项目基本情况与需求（必填）", 
                                  placeholder="公司现状、核心优势、面临问题、申报目的等...", height=150)
    additional_file = st.file_uploader("上传补充材料（可选：商业计划草稿、财务数据、专利清单等）", 
                                       type=["docx", "pdf", "txt"])

    submit_button = st.form_submit_button(label="🚀 一键生成政府BP + 落地方案")

if submit_button:
    if not company_name or not project_name or not current_status:
        st.error("请填写申报主体、项目名称和项目基本情况！")
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
所属行业：{industry}
计划申报金额：{funding_amount}万元
项目基本情况：{current_status}
补充材料：{extra_text}
"""

        with st.spinner("正在调用大模型生成专业政府BP（约30-60秒）..."):
            try:
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT + "\n\n以下是政府BP模板全文：\n" + TEMPLATES_TEXT},
                        {"role": "user", "content": f"请为以下项目生成完整政府申报BP和落地方案：\n{user_context}"}
                    ],
                    temperature=0.25,
                    max_tokens=4000,
                    stream=False
                )

                result = response.choices[0].message.content
                st.success("✅ 生成完成！")
                st.markdown(result)

                # 一键下载按钮
                st.download_button(
                    label="📥 下载完整BP（Markdown）",
                    data=result,
                    file_name=f"{project_name}_政府BP_落地方案.md",
                    mime="text/markdown"
                )

            except Exception as e:
                st.error(f"生成失败：{str(e)}")
                if "401" in str(e):
                    st.warning("API Key 无效或未设置")

st.sidebar.success("✅ 已加载政府BP模板")
st.sidebar.info("上传「政府BP模板.docx」到 data/ 目录即可使用")
