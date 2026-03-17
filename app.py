import streamlit as st
from io import BytesIO
from docx import Document
import time

# ────────────────────────────────────────────────
#  常數設定
# ────────────────────────────────────────────────
MAX_GENERATION_SECONDS = 90
MAX_TOKENS = 4200
TEMPERATURE = 0.25

# ────────────────────────────────────────────────
#  強化版系統提示（最關鍵部分）
# ────────────────────────────────────────────────
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
   - 6.1 首选落地区域及理由
   - 6.2 用地需求
   - 6.3 用电/用水/气需求
   - 6.4 政策及资金支持诉求（越具体越好）
   - 6.5 落地实施初步计划
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

# ────────────────────────────────────────────────
#  這裡選擇最簡單穩定的方式：直接使用強化版，不拼接不存在的變數
# ────────────────────────────────────────────────
FULL_SYSTEM_PROMPT = SYSTEM_PROMPT_STRICT

# 如果你未來有其他提示內容想加，可以改成下面這種形式（但現在先保持簡單）
# FULL_SYSTEM_PROMPT = SYSTEM_PROMPT_STRICT + "\n\n額外要求：請務必使用正式公文語氣"

# 假設你有這個變數（如果沒有就註解掉或定義一個空字串）
try:
    TEMPLATES_TEXT
except NameError:
    TEMPLATES_TEXT = ""   # 如果沒有模板全文，就給空字串

# ────────────────────────────────────────────────
#               Streamlit 主程式
# ────────────────────────────────────────────────

st.title("政府BP & 落地方案生成工具")

with st.form("project_form"):
    company_name = st.text_input("申报主体*", placeholder="例：XX新能源科技有限公司")
    project_name = st.text_input("项目名称*", placeholder="例：年产10GWh固态电池生产基地")
    target_region = st.text_input("目标地区*", placeholder="例：四川省成都市")
    industry = st.text_input("所属产业领域", placeholder="例：新能源")
    total_investment = st.number_input("总投资额（万元）", min_value=100, value=5000)
    current_status = st.text_area("项目基本情况与核心亮点*", height=140)
    additional_file = st.file_uploader("上传补充材料（可选）", type=["docx", "pdf", "txt"])

    submit_button = st.form_submit_button("生成BP & 落地方案")

if submit_button:
    if not company_name or not project_name or not target_region or not current_status:
        st.error("请填写带*的必填项！")
    else:
        extra_text = ""
        if additional_file:
            try:
                if additional_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                    doc = Document(BytesIO(additional_file.read()))
                    extra_text = "\n".join(p.text.strip() for p in doc.paragraphs if p.text.strip())[:1200]
                else:
                    # pdf 或 txt 簡單處理（實際上 pdf 需要額外套件，這裡只示範 txt）
                    extra_text = additional_file.read().decode("utf-8", errors="ignore")[:1200]
            except Exception as e:
                st.warning("文件解析失败，仅使用文字描述")
                extra_text = ""

        user_context = f"""申报主体：{company_name}
项目名称：{project_name}
目标地区：{target_region}
所属产业：{industry}
总投资额：{total_investment:,}万元
项目基本情况与核心亮点：
{current_status}

补充材料（已截断）：
{extra_text}
"""

        start_time = time.time()
        with st.spinner(f"正在生成完整政府BP及落地方案（预计 {MAX_GENERATION_SECONDS} 秒内完成）..."):
            try:
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {
                            "role": "system",
                            "content": FULL_SYSTEM_PROMPT + "\n\n模板内容参考：\n" + TEMPLATES_TEXT
                        },
                        {
                            "role": "user",
                            "content": f"请严格按照模板，一字不差输出完整BP（纯文本）：\n\n{user_context}"
                        }
                    ],
                    temperature=TEMPERATURE,
                    max_tokens=MAX_TOKENS,
                    stream=False
                )

                result = response.choices[0].message.content.strip()
                elapsed = time.time() - start_time

                if elapsed > MAX_GENERATION_SECONDS - 5:
                    st.warning(f"生成时间较长（{elapsed:.1f}秒），内容已尽量完整")

                st.success(f"生成完成！（耗时 {elapsed:.1f} 秒）")
                st.markdown(f"```text\n{result}\n```")

                st.download_button(
                    label="下载完整报告（.txt）",
                    data=result,
                    file_name=f"{project_name}_政府BP_落地方案_{time.strftime('%Y%m%d')}.txt",
                    mime="text/plain"
                )

            except Exception as e:
                elapsed = time.time() - start_time
                if elapsed > MAX_GENERATION_SECONDS - 2:
                    st.error(
                        f"生成超时（>{MAX_GENERATION_SECONDS}秒），建议：\n"
                        "1. 缩短“项目基本情况”描述\n"
                        "2. 移除或简化补充材料\n"
                        "3. 再试一次"
                    )
                else:
                    st.error(f"生成失败：{str(e)}")
