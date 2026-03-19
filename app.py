# -*- coding: utf-8 -*-
import streamlit as st
import os
from io import BytesIO
import time
from openai import OpenAI

# 初始化 通义千问 client
api_key = os.getenv("DASHSCOPE_API_KEY")
if not api_key:
    st.error("未找到环境变量 DASHSCOPE_API_KEY，请在 Streamlit Cloud Secrets 中设置")
    st.stop()

client = OpenAI(
    api_key=api_key,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

MODEL_NAME = "qwen-turbo"
MAX_GENERATION_SECONDS = 90
MAX_TOKENS = 4200
TEMPERATURE = 0.25

SYSTEM_PROMPT_STRICT = """你是一位非常专业的政府项目申报BP撰写专家，专精产业招商、落地政策分析、政府汇报材料。
你的任务是：严格按照下面提供的【政府BP标准模板】结构和顺序，一字不差地输出完整文档。
禁止添加额外标题、禁止省略任何章节、禁止改变章节顺序、禁止使用Markdown标题符号、禁止输出```包围块。
【政府BP标准模板】必须包含以下所有一级标题（顺序不可变）：
1. 项目基本信息
2. 项目背景与意义
3. 项目建设内容
4. 投资估算与资金来源
5. 经济效益分析
6. 社会效益与生态影响
7. 落地方案与政策需求
   - 7.1 首选落地区域及理由
   - 7.2 用地需求
   - 7.3 用电/用水/气需求
   - 7.4 政策及资金支持诉求（越具体越好）
   - 7.5 落地实施初步计划
8. 风险分析与应对措施
9. 结论与建议
输出要求：
- 全部使用纯文本，不要出现任何 markdown 语法（#、*、- 等）
- 每个一级标题后空一行
- 二级标题前空一行，标题后空一行
- 每段文字控制在 6–12 行之间，避免超长段落
- “项目基本信息”部分要用表格形式文本表示（用 | 分隔）
- 数字一律使用中文表示（如：伍仟万元、叁年）
- 语气正式、客观、数据导向、突出“符合国家/地方战略”
- 总长度控制在3800–4500字之间
现在根据用户提供的信息，严格按照上述模板顺序输出完整BP及落地方案。
不要写任何前言、总结、道歉、说明，直接从第一个标题「项目基本信息」开始输出。
"""

FULL_SYSTEM_PROMPT = SYSTEM_PROMPT_STRICT
TEMPLATES_TEXT = ""

st.title("政府BP 落地方案生成工具")

with st.form("project_form"):
    company_name = st.text_input("申报主体*", placeholder="例：***科技有限公司")
    
    project_name = st.text_input("项目名称*", placeholder="例：***项目")
    
    # 修改：目標地區初始空白
    target_region = st.text_input(
        "目标地区*",
        value="",                     # 明確設為空 → 顯示空白
        placeholder="请输入目标地区，例如：济南"
    )
    
    # 修改：所屬產業領域初始空白
    industry = st.text_input(
        "所属产业领域",
        value="",                     # 明確設為空 → 顯示空白
        placeholder="请输入所属产业，例如：新能源"
    )
    
    total_investment = st.number_input(
        "总投资额（万元）",
        min_value=100.0,
        value=None,                   # 保持空白
        step=100.0,
        format="%.0f",
        placeholder="请输入金额"
    )
    
    current_status = st.text_area(
        "项目基本情况与核心亮点*",
        height=180,
        value=""
    )
    
    additional_file = st.file_uploader("上传补充材料（可选）", type=["docx", "pdf", "txt"])
    
    submit_button = st.form_submit_button("生成BP & 落地方案")

if submit_button:
    # 加強驗證：目標地區和產業領域也要求填寫（視需求可調整）
    required_fields = {
        "申报主体": company_name,
        "项目名称": project_name,
        "目标地区": target_region.strip(),
        "项目基本情况与核心亮点": current_status.strip()
    }
    
    missing = [k for k, v in required_fields.items() if not v]
    if missing or total_investment is None:
        error_msg = "请填写以下必填项：\n" + "\n".join(missing)
        if total_investment is None:
            error_msg += "\n- 总投资额（万元）"
        st.error(error_msg)
        st.stop()

    extra_text = ""
    if additional_file is not None:
        try:
            file_type = additional_file.type
            if "officedocument.wordprocessingml" in file_type:
                from docx import Document
                doc = Document(BytesIO(additional_file.read()))
                extra_text = "\n".join(
                    p.text.strip() for p in doc.paragraphs if p.text.strip()
                )[:1500]
            else:
                extra_text = additional_file.read().decode("utf-8", errors="ignore")[:1500]
        except Exception as e:
            st.warning(f"文件解析失败：{str(e)}，仅使用表单文字内容")
            extra_text = ""

    user_context = f"""\
申报主体：{company_name}
项目名称：{project_name}
目标地区：{target_region}
所属产业：{industry}
总投资额：{total_investment:,.0f if total_investment is not None else '未填'}万元
项目基本情况与核心亮点：
{current_status}
补充材料（已截断至约1500字）：
{extra_text}
"""

    start_time = time.time()
    with st.spinner(f"正在生成完整政府BP及落地方案（预计 {MAX_GENERATION_SECONDS} 秒内完成）..."):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": FULL_SYSTEM_PROMPT + "\n\n模板内容参考：\n" + TEMPLATES_TEXT},
                    {"role": "user", "content": f"请严格按照模板，一字不差输出完整BP（纯文本）：\n\n{user_context}"}
                ],
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS,
                stream=False
            )

            result = response.choices[0].message.content.strip()
            elapsed = time.time() - start_time

            if elapsed > MAX_GENERATION_SECONDS - 5:
                st.warning(f"生成耗时较长（{elapsed:.1f}秒），内容已尽量完整")

            st.success(f"生成完成！（耗时 {elapsed:.1f} 秒）")
            st.markdown("### 生成结果")

            bold_fields = ["项目名称", "目标地区", "项目愿景", "项目愿景："]
            processed = result
            for field in bold_fields:
                processed = processed.replace(
                    f"{field} |", f"{field} | **"
                ).replace(
                    f"| {field} |", f"| **{field}** |"
                ).replace(
                    f"{field}：", f"**{field}**："
                )

            if "2. 项目背景与意义" in processed:
                processed = processed.replace(
                    "2. 项目背景与意义",
                    '<div style="border-left: 4px solid #3b82f6; padding-left: 1.2em; margin: 1.8em 0; line-height: 1.85; font-size: 15.2px;">'
                    '**2. 项目背景与意义**'
                )
                next_section = "3. 项目建设内容"
                if next_section in processed:
                    pos = processed.find(next_section)
                    processed = processed[:pos] + "</div>\n\n" + processed[pos:]
                else:
                    processed += "</div>"

            st.markdown(processed, unsafe_allow_html=True)

            safe_filename = project_name.replace(" ", "_").replace("/", "_")[:50]
            st.download_button(
                label="下载完整报告（.txt）",
                data=result,
                file_name=f"{safe_filename}_{target_region or '未知地区'}_{time.strftime('%Y%m%d')}.txt",
                mime="text/plain"
            )

        except Exception as e:
            elapsed = time.time() - start_time
            err_str = str(e).lower()
            if "timeout" in err_str or elapsed > MAX_GENERATION_SECONDS - 3:
                st.error(f"生成超时或网络问题（耗时 {elapsed:.1f}秒）\n建议：\n1. 缩短描述文字\n2. 移除或缩减附件\n3. 稍后重试")
            elif any(x in err_str for x in ["invalid api key", "authentication", "unauthorized"]):
                st.error("API Key 验证失败，请确认 Secrets 中的 DASHSCOPE_API_KEY 是否正确")
            else:
                st.error(f"生成失败：{str(e)}\n请检查模型名称、API Key 或网络连线")

