# -*- coding: utf-8 -*-
import streamlit as st
import os
import re
from io import BytesIO
import time
from openai import OpenAI

api_key = os.getenv("DASHSCOPE_API_KEY")
if not api_key:
    st.error("未找到环境变量 DASHSCOPE_API_KEY，请在 Streamlit Cloud Secrets 中设置")
    st.stop()

client = OpenAI(
    api_key=api_key,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

FAST_MODEL = "qwen-plus"
STRONG_MODEL = "qwen-max"
MAX_TOKENS_PER_CALL = 5500
TEMPERATURE = 0.10

SYSTEM_BASE = """你是一位资深政府产业基金投资决策顾问，擅长撰写符合政府招商逻辑的商业计划书结构化提纲。
严格使用 Markdown 格式输出，不要添加多余说明。
语气正式、专业，使用政府常用术语。
所有关键数据使用 [占位符] 标记。
现在根据以下项目信息生成内容。"""

USER_PROJECT_INFO_TEMPLATE = """目标地区：{target}
项目名称：{project}
申报主体：{company}
所属产业：{industry}
总投资：{investment} 万元
核心亮点及材料：
{highlights_and_extra}"""

SECTIONS = [
    {"id": "zero",  "title": "零、Executive Summary / 项目决策摘要", "model": STRONG_MODEL},
    {"id": "one",   "title": "一、项目概述与战略价值", "model": FAST_MODEL},
    {"id": "two",   "title": "二、市场分析", "model": FAST_MODEL},
    {"id": "three", "title": "三、技术实力与产品壁垒", "model": FAST_MODEL},
    {"id": "four",  "title": "四、产业化落地实施计划", "model": FAST_MODEL},
    {"id": "five",  "title": "五、商业模式与财务预测", "model": STRONG_MODEL},
    {"id": "six",   "title": "六、产业带动与社会效益", "model": FAST_MODEL},
    {"id": "seven", "title": "七、政策支持诉求与替代方案", "model": FAST_MODEL},
    {"id": "eight", "title": "八、风险分析与防控措施", "model": FAST_MODEL},
    {"id": "nine",  "title": "九、投资结论与下一步行动计划", "model": STRONG_MODEL},
]

st.title("政府BP结构化提纲生成工具")

with st.form("bp_form"):
    company_name = st.text_input("申报主体*", placeholder="例：XX科技有限公司")
    project_name = st.text_input("项目名称*", placeholder="例：固态电池正极材料产业化项目")
    target_region = st.text_input("目标地区*", placeholder="例：济南高新区")
    industry = st.text_input("所属产业领域", placeholder="新能源 / 新材料")
    
    total_investment = st.number_input(
        "总投资额（万元）*",
        min_value=100.0,
        value=None,
        step=100.0,
        format="%.0f"
    )
    
    current_status = st.text_area("项目基本情况与核心亮点*", height=180)
    
    additional_file = st.file_uploader(
        "上传补充材料*",
        type=["docx", "pdf", "txt"],
        help="请上传项目计划书、技术资料等核心文件"
    )
    
    submit = st.form_submit_button("开始生成")

if submit:
    required = [company_name.strip(), project_name.strip(), target_region.strip(), current_status.strip(), additional_file]
    if not all(required) or total_investment is None:
        st.error("请填写所有带 * 的必填项")
        st.stop()

    # 读取上传文件
    extra_text = ""
    try:
        content_bytes = additional_file.read()
        file_type = additional_file.type

        if "officedocument.wordprocessingml" in file_type or file_type.endswith("docx"):
            from docx import Document
            doc = Document(BytesIO(content_bytes))
            extra_text = "\n".join(p.text.strip() for p in doc.paragraphs if p.text.strip())
        else:
            try:
                extra_text = content_bytes.decode("utf-8", errors="ignore")
            except:
                extra_text = "[文件内容无法解码，仅支持文本类文件]"

        extra_text = extra_text[:2800]
    except Exception as e:
        st.warning(f"文件读取失败：{str(e)[:80]}... 将仅使用文本框内容")

    investment_str = f"{total_investment:,.0f}" if total_investment is not None else "未填写"

    highlights_and_extra = current_status.strip() + "\n\n补充材料（关键摘录）：\n" + extra_text

    user_base = USER_PROJECT_INFO_TEMPLATE.format(
        target=target_region,
        project=project_name,
        company=company_name,
        industry=industry,
        investment=investment_str,
        highlights_and_extra=highlights_and_extra
    )

    full_result_parts = {}
    total_start = time.time()

    progress_bar = st.progress(0)
    status_text = st.empty()

    for idx, section in enumerate(SECTIONS):
        # 中性进度提示，不暴露具体章节名
        status_text.text(f"正在生成第 {idx+1} / {len(SECTIONS)} 部分（预计总耗时 60-120 秒）")
        
        try:
            response = client.chat.completions.create(
                model=section.get("model", FAST_MODEL),
                messages=[
                    {"role": "system", "content": SYSTEM_BASE},
                    {"role": "user", "content": user_base + f"\n\n请严格只输出以下章节的完整 Markdown 内容，不要输出其他任何文字：\n**{section['title']}**"}
                ],
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS_PER_CALL,
                stream=False
            )
            content = response.choices[0].message.content.strip()
            full_result_parts[section["id"]] = content
        except Exception as e:
            full_result_parts[section["id"]] = f"【本节生成失败】{str(e)[:120]}"

        progress_bar.progress((idx + 1) / len(SECTIONS))

    total_time = time.time() - total_start

    status_text.empty()
    st.success(f"生成完成，总耗时 {total_time:.1f} 秒")

    st.markdown("### 生成结果")

    for section in SECTIONS:
        title = section["title"]
        content = full_result_parts.get(section["id"], "（无内容）")

        if section["id"] == "zero":
            st.markdown(f"## {title}")
            # 尝试提取摘要中的关键字段并转为表格
            table_data = []
            lines = content.split("\n")
            current_key = ""
            current_value = ""

            for line in lines:
                line = line.strip()
                if not line:
                    continue
                # 匹配常见的键值对格式，如 ## 项目名称 / ### 项目名称
                match = re.match(r"#{2,3}\s*(.+?)(?:\s*/.+?)?\s*$", line)
                if match:
                    if current_key and current_value:
                        table_data.append((current_key, current_value.strip()))
                    current_key = match.group(1).strip()
                    current_value = ""
                else:
                    if current_key:
                        current_value += " " + line

            if current_key and current_value:
                table_data.append((current_key, current_value.strip()))

            if table_data:
                st.markdown("#### 项目决策摘要")
                st.table(table_data)  # 或 st.markdown 用表格语法更美观
            else:
                # 如果提取失败，就直接显示原文
                st.markdown(content)
        else:
            st.markdown(f"## {title}")
            st.markdown(content)

        st.markdown("---")

    # 下载部分
    full_md_content = ""
    for sec in SECTIONS:
        full_md_content += f"# {sec['title']}\n\n"
        full_md_content += full_result_parts.get(sec["id"], "") + "\n\n---\n\n"

    safe_filename = f"{project_name.replace(' ', '_')}_{target_region.replace(' ', '_') or '未知地区'}_{time.strftime('%Y%m%d')}"

    st.download_button(
        label="下载 Markdown 版",
        data=full_md_content,
        file_name=f"{safe_filename}_政府BP提纲.md",
        mime="text/markdown"
    )

    st.download_button(
        label="下载纯文本版",
        data=full_md_content,
        file_name=f"{safe_filename}_纯文本.txt",
        mime="text/plain"
    )
