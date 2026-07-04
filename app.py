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

# ====================== 修改点：添加免责声明 ======================
SYSTEM_BASE = """你是一位资深政府产业基金投资决策顾问，擅长撰写符合政府招商逻辑的商业计划书结构化提纲。
严格使用 Markdown 格式输出，不要添加多余说明。
语气正式、专业，使用政府常用术语。
所有关键数据使用 [占位符] 标记。

重要免责要求：在输出的最开始位置，必须第一行明确写上以下内容：
**重要提示：本方案/分析仅供参考，不构成任何正式的投资、招商、决策或法律建议。**

现在根据以下项目信息生成内容。"""

USER_PROJECT_INFO_TEMPLATE = """目标地区：{target}
项目名称：{project}
申报主体：{company}
所属产业：{industry}
总投资：{investment} 万元
核心亮点及材料：
{highlights_and_extra}"""

SECTIONS = [
    {"id": "zero", "title": "零、Executive Summary / 项目决策摘要", "model": STRONG_MODEL},
    {"id": "one", "title": "一、项目概述与战略价值", "model": FAST_MODEL},
    {"id": "two", "title": "二、市场分析", "model": FAST_MODEL},
    {"id": "three", "title": "三、技术实力与产品壁垒", "model": FAST_MODEL},
    {"id": "four", "title": "四、产业化落地实施计划", "model": FAST_MODEL},
    {"id": "five", "title": "五、商业模式与财务预测", "model": STRONG_MODEL},
    {"id": "six", "title": "六、产业带动与社会效益", "model": FAST_MODEL},
    {"id": "seven", "title": "七、政策支持诉求与替代方案", "model": FAST_MODEL},
    {"id": "eight", "title": "八、风险分析与防控措施", "model": FAST_MODEL},
    {"id": "nine", "title": "九、投资结论与下一步行动计划", "model": STRONG_MODEL},
]

# ====================== 修改点：预填充“项目基本情况与核心亮点”默认内容 ======================
DEFAULT_CURRENT_STATUS = """# 智星空间公司简介
## 一、企业基本概况
智星空间（核心运营主体为济南智星空间科技有限公司、北京智星空间科技有限公司）成立于2018年5月，是国内聚焦商业合成孔径雷达（SAR）卫星赛道的高新技术企业，同时为国际宇航联会员单位。公司法定代表人为刘丽坤博士，核心团队成员主要来自航天五院、中科院、国防科大等航天科研单位，曾主导天通一号、东方红四号/五号卫星平台、少年星一号等多个国家级首发型号研制任务，具备体制内与民营航天的双重卫星研制及成功发射经验。
公司总部位于山东济南，在北京、西安设有研发运营中心，在东南亚、中东、非洲布局卫星数据分销网络，是国内最早聚焦商业SAR卫星并具备**卫星+SAR载荷星载一体化设计能力**的企业，也是国内首批在国际电联（ITU）报备X波段雷达卫星频率并完成国内协调的商业航天单位。
## 二、核心技术与产品体系
公司掌握低轨SAR卫星制造与运营全链条核心技术，拥有完全自主知识产权，核心产品覆盖星载、机载两大场景：
1. **星载SAR卫星**：具备整星设计、制造、频率申请、发射协调、测控联调的全流程解决方案能力，自研卫星影像最高分辨率优于0.5米，处于国内商业SAR第一梯队；国内首创3D打印结构+星载一体化设计方案，大幅降低整星制造成本与研制周期。
2. **机载MiniSAR载荷**：面向轻小型无人机研发的超小型SAR雷达载荷，成像最高分辨率优于0.1米，支持全天候、实时成像、多极化工作模式，技术指标达到国际领先水平，已实现批量化生产。
## 三、在轨成果与星座规划
截至目前，公司已成功完成4颗卫星的研制与发射，核心在轨节点包括：
- 2020年12月，首发星“智星一号A星”搭载长征八号火箭在文昌发射升空；
- 2022年5月，“智星三号A星”搭载天舟四号货运飞船入轨，是国内首家通过货运飞船发射卫星的民营企业；
- 2024年2月，自研雷达卫星“济高科创号”搭载捷龙三号火箭入轨并投入商业运营，是国内首颗3D打印结构的星载一体化设计雷达卫星。
星座建设层面，公司一期规划部署12颗SAR卫星组成的智能星座，建成后可实现全球任意地点小时级重访、毫米级形变监测能力；后续将扩容至48颗卫星组网，进一步提升全球覆盖时效与数据服务能力。
## 四、商业化应用场景
公司SAR卫星数据已实现多领域商业化落地，核心应用方向包括：
- 自然资源监测：地质形变监测、矿山安全、耕地保护、水体监测；
- 城市与基建安全：城市地面沉降、交通干线巡检、水利工程监测；
- 应急与灾害响应：洪涝、地震、滑坡等灾害的全天候灾情监测与评估；
- 行业定制服务：面向数字黄河、海洋监测、国防军工等领域提供专项数据解决方案。
## 五、融资进度与发展阶段
截至2026年5月，公司已累计完成6轮融资，覆盖种子轮到B+轮全周期，核心投资方包括山东财金、山东铁发资本、同润科投、哈工创投、得厚资本等国资与市场化机构，最新B+轮融资金额超亿元。融资资金主要用于新一代SAR卫星星座建设、MiniSAR载荷量产线搭建及前沿技术研发。
公司当前已实现核心产品商业化落地与盈利，处于商业航天成长期后期，是国内商业SAR赛道中技术闭环完整、商业化验证充分的代表性标的。"""

st.title("企业落地分析")

with st.form("bp_form"):
    company_name = st.text_input("申报主体*", value="济南智星空间科技有限公司", placeholder="例：XX科技有限公司")
    project_name = st.text_input("项目名称*", value="卫星研发智造总部基地项目", placeholder="例：固态电池正极材料产业化项目")
    target_region = st.text_input("目标地区*", value="济南市高新区", placeholder="例：济南高新区")
    industry = st.text_input("所属产业领域", value="商业航天", placeholder="新能源 / 新材料")
  
    total_investment = st.number_input(
        "总投资额（万元）*",
        min_value=100.0,
        value=5000.0,
        step=100.0,
        format="%.0f"
    )
  
    current_status = st.text_area(
        "项目基本情况与核心亮点*",
        value=DEFAULT_CURRENT_STATUS,
        height=180
    )
  
    additional_file = st.file_uploader(
        "上传补充材料（可选）",
        type=["docx", "pdf", "txt"],
        help="请上传项目计划书、技术资料等（不上传也可生成）"
    )
  
    submit = st.form_submit_button("开始生成")

if submit:
    required = [company_name.strip(), project_name.strip(), target_region.strip(), current_status.strip()]
    if not all(required) or total_investment is None:
        st.error("请填写所有带 * 的必填项")
        st.stop()

    extra_text = ""
    if additional_file is not None:
        try:
            content_bytes = additional_file.read()
            file_type = additional_file.type
            if "officedocument.wordprocessingml" in file_type or file_type.endswith("docx"):
                from docx import Document
                doc = Document(BytesIO(content_bytes))
                extra_text = "\n".join(p.text.strip() for p in doc.paragraphs if p.text.strip())
            else:
                extra_text = content_bytes.decode("utf-8", errors="ignore")
            extra_text = extra_text[:2800]
        except Exception as e:
            st.warning(f"文件读取失败：{str(e)[:80]}... 将仅使用文本框内容")
    else:
        extra_text = "（未上传补充材料，仅使用表单填写内容）"

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

    # ================== 生成逻辑 ==================
    full_result_parts = {}
    total_start = time.time()
    progress_bar = st.progress(0)
    status_text = st.empty()

    for idx, section in enumerate(SECTIONS):
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
    
    # ================== 添加醒目免责提示 ==================
    st.warning("**重要提示：本方案/分析仅供参考，不构成任何正式的投资、招商、决策或法律建议。**")

    st.markdown("### 生成结果")
    for section in SECTIONS:
        title = section["title"]
        content = full_result_parts.get(section["id"], "（无内容）")
        if section["id"] == "zero":
            # 表格提取逻辑保持不变
            table_data = []
            lines = content.split("\n")
            current_key = ""
            current_value = ""
            for line in lines:
                line = line.strip()
                if not line: continue
                match = re.match(r"#{2,4}\s*(.+?)(?:\s*/.+?)?\s*$", line)
                if match:
                    if current_key and current_value:
                        table_data.append((current_key, current_value.strip()))
                    current_key = match.group(1).strip()
                    current_value = ""
                else:
                    if current_key:
                        current_value += (" " if current_value else "") + line
            if current_key and current_value:
                table_data.append((current_key, current_value.strip()))
            if table_data:
                table_md = "| 字段名称 | 内容 |\n|----------|------|\n"
                for key, value in table_data:
                    clean_value = re.sub(r'\s+', ' ', value).strip()
                    table_md += f"| {key} | {clean_value} |\n"
                st.markdown(table_md)
            else:
                st.markdown(content)
        else:
            st.markdown(f"## {title}")
            st.markdown(content)
        st.markdown("---")

    # 下载部分保持不变
    full_md_content = ""
    for sec in SECTIONS:
        full_md_content += f"# {sec['title']}\n\n"
        full_md_content += full_result_parts.get(sec["id"], "") + "\n\n---\n\n"

    safe_filename = f"{project_name.replace(' ', '_')}_{target_region.replace(' ', '_') or '未知地区'}_{time.strftime('%Y%m%d')}"

    st.download_button(
        label="下载 Markdown 版",
        data=full_md_content,
        file_name=f"{safe_filename}_企业落地分析.md",
        mime="text/markdown"
    )
    st.download_button(
        label="下载纯文本版",
        data=full_md_content,
        file_name=f"{safe_filename}_纯文本.txt",
        mime="text/plain"
    )
