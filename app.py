# ────────────────────────────────────────────────
#  建议放在文件开头或 config 部分
MAX_GENERATION_SECONDS = 90
MAX_TOKENS = 4200          # 根据实际模板长度可调 3800~4800
TEMPERATURE = 0.25         # 更低一点，更遵守格式

# 强烈建议把模板做成常量，或从单独 md 文件读取
# 这里假设你已经有 TEMPLATES_TEXT 变量，完整政府BP模板文本

# ────────────────────────────────────────────────
#  强化版的 SYSTEM_PROMPT（最关键的部分）
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

# 如果你原来的 SYSTEM_PROMPT 还有其他重要内容，可以做如下合并：
FULL_SYSTEM_PROMPT = SYSTEM_PROMPT_STRICT + "\n\n原系统提示补充内容：\n" + SYSTEM_PROMPT

# ────────────────────────────────────────────────
#           主逻辑部分修改
# ────────────────────────────────────────────────

if submit_button:
    if not company_name or not project_name or not target_region or not current_status:
        st.error("请填写带*的必填项！")
        st.stop()

    # 文件读取部分保持不变，但限制长度更严格
    extra_text = ""
    if additional_file:
        try:
            if additional_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                doc = Document(BytesIO(additional_file.read()))
                extra_text = "\n".join(p.text.strip() for p in doc.paragraphs if p.text.strip())[:1200]
            else:
                extra_text = additional_file.read().decode("utf-8", errors="ignore")[:1200]
        except:
            extra_text = ""
            st.warning("补充材料解析失败，仅使用已填写的文字内容")

    user_context = f"""\
申报主体：{company_name}
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
    with st.spinner(f"正在生成完整政府BP及落地方案（预计{MAX_GENERATION_SECONDS}秒内完成）..."):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": FULL_SYSTEM_PROMPT + "\n\n模板内容参考：\n" + TEMPLATES_TEXT},
                    {"role": "user",   "content":  f"请严格按照模板，一字不差输出完整BP（纯文本）：\n\n{user_context}"}
                ],
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS,
                stream=False,
                # 可选：timeout=100 （视 SDK 支持情况）
            )

            result = response.choices[0].message.content.strip()
            elapsed = time.time() - start_time

            if elapsed > MAX_GENERATION_SECONDS - 5:
                st.warning(f"生成时间较长（{elapsed:.1f}秒），内容已尽量完整")

            st.success(f"生成完成！（耗时 {elapsed:.1f} 秒）")

            # 显示时强制用 code block 防止 HTML 转义问题
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
                st.error(f"生成超时（>{MAX_GENERATION_SECONDS}秒），建议：\n1. 缩短“项目基本情况”描述\n2. 移除或简化补充材料\n3. 再试一次")
            else:
                st.error(f"生成失败：{str(e)}\n请检查网络或API密钥后重试")
