# -*- coding: utf-8 -*-
import streamlit as st
import os
from io import BytesIO
import time
from openai import OpenAI

api_key = os.getenv("DASHSCOPE_API_KEY")
if not api_key:
    st.error("未找到 DASHSCOPE_API_KEY")
    st.stop()

client = OpenAI(api_key=api_key, base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")

# 建议模型组合：大部分用 plus，关键部分用 max
FAST_MODEL = "qwen-plus"          # 或 "qwen-turbo" 更快
STRONG_MODEL = "qwen-max"         # 只用于摘要/财务/对赌等高质量需求
MAX_TOKENS_PER_CALL = 5500        # 保守设置，避免截断
TEMPERATURE = 0.1
TIMEOUT_WARNING_SEC = 100         # 超过此值才给轻提示

# 把原长提示词拆分成公共部分 + 各章节要求（这里只示例，实际你要拆分模板）
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
{highlights_and_extra}
"""

# 章节列表（可调整顺序/拆分粒度）
SECTIONS = [
    {"id": "zero", "title": "零、Executive Summary / 项目决策摘要", "model": STRONG_MODEL, "prompt_suffix": "先生成完整摘要部分，包括（一）（二）（三）（四），字数控制在1500-2000字。"},
    {"id": "one",  "title": "一、项目概述与战略价值", "model": FAST_MODEL, "prompt_suffix": "生成此章节完整内容，包括（一）基本信息表、（二）5大卖点、（三）战略契合。"},
    {"id": "two",  "title": "二、市场分析", "model": FAST_MODEL},
    {"id": "three","title": "三、技术实力与产品壁垒", "model": FAST_MODEL},
    {"id": "four", "title": "四、产业化落地实施计划", "model": FAST_MODEL, "prompt_suffix": "重点详细生成时间表（Markdown表格），包含需政府配合事项。"},
    {"id": "five", "title": "五、商业模式与财务预测", "model": STRONG_MODEL, "prompt_suffix": "重点生成财务预测表、对赌条款清单，保守估算。"},
    {"id": "six",  "title": "六、产业带动与社会效益", "model": FAST_MODEL},
    {"id": "seven","title": "七、政策支持诉求与替代方案", "model": FAST_MODEL, "prompt_suffix": "详细列出资金、用地、订单、人才支持及Plan B方案。"},
    {"id": "eight","title": "八、风险分析与防控措施", "model": FAST_MODEL},
    {"id": "nine", "title": "九、投资结论与下一步行动计划", "model": STRONG_MODEL},
]

st.title("政府BP结构化提纲生成工具（分段防截断版）")

with st.form("bp_form"):
    company_name = st.text_input("申报主体*", placeholder="例：XX科技有限公司")
    project_name = st.text_input("项目名称*", placeholder="例：XX固态电池项目")
    target_region = st.text_input("目标地区*", placeholder="例：济南高新区")
    industry = st.text_input("所属产业领域", placeholder="新能源 / 新材料")
    total_investment = st.number_input("总投资额（万元）", min_value=100.0, value=None, step=100.0, format="%.0f")
    current_status = st.text_area("项目基本情况与核心亮点*", height=180)
    additional_file = st.file_uploader("上传补充材料*", type=["docx", "pdf", "txt"])
    submit = st.form_submit_button("开始生成（分段生成，更稳定）")

if submit:
    # 验证略（同原代码）

    # 读取文件 → extra_text （同原代码，省略）

    investment_str = f"{total_investment:,.0f}" if total_investment else "未填"

    user_base = USER_PROJECT_INFO_TEMPLATE.format(
        target=target_region,
        project=project_name,
        company=company_name,
        industry=industry,
        investment=investment_str,
        highlights_and_extra=current_status + "\n\n补充材料：\n" + extra_text[:2800]
    )

    full_result_parts = {}
    total_start = time.time()

    progress = st.progress(0)
    status_text = st.empty()

    for idx, sec in enumerate(SECTIONS):
        status_text.text(f"正在生成：{sec['title']} ({idx+1}/{len(SECTIONS)})")
        
        section_start = time.time()
        
        try:
            resp = client.chat.completions.create(
                model=sec.get("model", FAST_MODEL),
                messages=[
                    {"role": "system", "content": SYSTEM_BASE + "\n" + sec.get("prompt_suffix", "")},
                    {"role": "user", "content": user_base + f"\n\n请只输出 **{sec['title']}** 这一章节的完整 Markdown 内容，不要输出其他章节。"}
                ],
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS_PER_CALL,
                stream=False,
                timeout=150  # 单次调用超时控制
            )
            
            content = resp.choices[0].message.content.strip()
            full_result_parts[sec["id"]] = content
            
            sec_time = time.time() - section_start
            if sec_time > 60:
                status_text.text(f"{sec['title']} 生成完成（耗时 {sec_time:.1f}秒）")
        
        except Exception as e:
            st.error(f"{sec['title']} 生成失败：{str(e)}")
            # 可选择跳过或重试，这里简单记录错误
            full_result_parts[sec["id"]] = f"【生成失败】{str(e)}"

        progress.progress((idx + 1) / len(SECTIONS))

    total_elapsed = time.time() - total_start

    st.success(f"全部分段生成完成！总耗时 {total_elapsed:.1f} 秒")

    # 拼接显示
    st.markdown("### 生成结果（已分段拼接）")
    st.markdown("---")

    for sec in SECTIONS:
        st.markdown(f"## {sec['title']}")
        content = full_result_parts.get(sec["id"], "（无内容）")
        st.markdown(content)
        st.markdown("---")

    # 下载完整拼接版
    full_md = "\n\n".join([f"# {sec['title']}\n{content}" for sec, content in zip(SECTIONS, full_result_parts.values())])
    
    safe_name = f"{project_name.replace(' ','_')}_{target_region or '未知'}_{time.strftime('%Y%m%d')}"
    
    st.download_button("下载完整 Markdown", full_md, f"{safe_name}_政府BP提纲.md", "text/markdown")
    st.download_button("下载纯文本", full_md, f"{safe_name}_纯文本.txt", "text/plain")
