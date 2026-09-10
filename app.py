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

# ====================== 免责声明（保持不变） ======================
SYSTEM_BASE = """你是一位资深政府产业基金投资决策顾问，擅长撰写符合政府招商逻辑的商业计划书结构化提纲。
严格使用 Markdown 格式输出，不要添加多余说明。
语气正式、专业，使用政府常用术语。
所有关键数据使用 [占位符] 标记。

重要免责要求：在输出的最开始位置，必须第一行明确写上以下内容：
**重要提示：本方案/分析仅供参考，不构成任何正式的投资、招商、决策或法律建议。**

现在根据以下项目信息生成内容。"""

# ====================== 司法环境与类案法律风险分析专用 System Prompt ======================
# 依据：谭总（律师/同祺股东）需求 —— 建议在企业落地分析中引入"类似企业遇到同类法律问题的
# 判决思路"作为重要参数：地方司法环境/营商环境对外地企业是否友好，是企业能否顺利落地、
# 权益能否得到保障的重要隐性风险点，尤其体现在外地企业与本地主体发生纠纷时，本地法院是否
# 存在地方保护倾向，以及是否存在上级法院/最高法的统一裁判尺度、纠偏机制。
#
# ====== 本次优化：将谭总提供的四大类真实类案库（跨地域裁判冲突 / 行政+司法双重壁垒 /
# 民企产权纠纷不当刑事化 / 信用评价隐性地方保护）整合进方法论参考模板，替换原先仅以
# 房地产行业为例的单一案例池，使其成为覆盖面更广、更贴近谭总研究方向的类案检索基座。
# 生成时模型仍需按申报企业所属产业做类比映射，而非机械套用地产或其他具体行业案例。

LEGAL_RISK_REFERENCE = """
【类案分析方法论参考模板 —— 来自谭总提供的司法案例研究，仅作分析框架与检索方向参考，
不代表目标地区实际情况，实际生成时须结合申报企业所属产业做合理类比】

一、核心分析逻辑
企业跨地域落地时，除产业政策、财税支持外，"目标地区司法环境对外地企业是否友好"是容易被
忽视但影响重大的隐性风险变量。判断逻辑核心是：当外地企业与本地主体（本地企业、本地个人、
本地行政机关）发生法律纠纷时，本地基层/中级法院的裁判倾向是否存在系统性偏向本地一方的现象，
以及一旦出现地方保护倾向，是否存在可预期的上级法院/最高法纠错机制。

二、参考案例类型库（四大类，实际生成时需按申报企业所属产业类比替换为该产业对应的高频
纠纷类型，方法论与风险识别逻辑保持一致，不得照搬案例原文或具体案号冒充目标地区数据）

【类型一】同一事实跨地域裁判冲突 —— 本外地主体裁量不一致
核心特征：同一基础交易事实，在不同法院（尤其原告属地 vs 被告属地）审理时，裁判结果或
案件定性出现显著甚至截然相反的倾向；异地维权周期、举证标准、责任认定均可能因审理地不同
而系统性偏向本地一方。
参考模式：
  - 同一交易纠纷，在外地一方起诉地与本地主体属地法院分别审理，出现民事责任认定/事实定性
    明显不一致的情况（含个别案件中一方在异地胜诉、同期在对方属地被作出不利认定的极端样本，
    是国内研究"同案不同判"与司法地方保护关联性时常引用的类型）。
  - 定制类合同/加工承揽类纠纷中，属地（被告方所在地）一审阶段对外地原告的举证标准明显
    严于对本地被告的责任认定标准，经上诉或二审改判后纠正。
适用产业类推方向：制造业供应链纠纷、定制设备/加工承揽合同纠纷、跨区域经销代理纠纷等。

【类型二】外地企业进入成熟本地产业集群 —— 行政壁垒与司法认同的叠加风险
核心特征：本地已形成成熟产业集群或存量龙头企业时，地方政府或监管部门可能通过隐性资质
门槛、招投标评分倾斜、市场准入备案等行政手段限制外地企业进入；若因此产生商事或行政纠纷，
基层法院在纠纷初期存在认同地方限制性监管、需经二审或上级机关介入才纠正的现象。
参考模式：
  - 行业政策放开跨区域经营限制后，本地监管部门仍依据旧规则对外地企业采取查封、处罚等
    执法行为，基层法院一审支持地方监管行为，二审改判确认执法行为违法/无效。
  - 地方主管部门发文明示扶持本地骨干企业（如资格预审豁免、保证金减半、评标加分等），
    对外地同类企业形成评分或准入层面的结构性劣势，经上级监管机关认定构成滥用行政权力
    排除竞争，责令废止相关政策文件。
  - 外地投资主体与地方政府发生行政协议类纠纷（如土地出让后被收回）时，基层法院以
    "不属受案范围"等程序性理由导致立案受阻，客观上抬高外地主体的维权门槛。
  - 地方通过市场准入备案、从严审查等方式限制外地同类产品/企业进入本地流通市场，形成
    区域性产业闭环，媒体或上级机关介入后才整改。
适用产业类推方向：需属地资质/备案的行业（如原材料流通、建筑与工程招投标、区域特许经营类
业务）、政府采购与PPP类项目、地方国企/龙头企业已形成产业集群的领域。

【类型三】民营企业产权纠纷、经济纠纷不当刑事化风险
核心特征：外来民营投资者与本地合作方发生资产、股权或土地合作类经济纠纷时，存在被基层
办案机关以刑事手段介入处理的风险（即"经济纠纷刑事化"），企业家人身自由、企业资产可能
在纠纷未决期间即受限制；本地关联主体同类经营模式通常未被同等追责，纠错往往需要经过
多年申诉、再审程序才能实现。
参考模式：
  - 采用合规联营/入股模式开展合作开发，因合作方或地方办案机关认定存在瑕疵，被以刑事
    罪名立案，企业家被羁押，一审定罪，历经多年申诉后再审改判无罪。
  - 涉虚报注册资本、职务侵占等罪名的一批再审无罪案例，原审在民商事法律关系与刑事责任
    边界不清晰的情况下，将企业经营不规范问题直接入刑处理。
法律边界提示：民商事纠纷与刑事责任的边界需依法严格区分，只有存在证据不足、程序违法、
罪责认定错误等情形才构成"不当刑事化"；正常的刑事立案与司法程序不属于地方保护范畴，
分析时应保持审慎、避免绝对化结论。
适用产业类推方向：涉及股权合作、联合开发、资产/知识产权权属争议较多的行业，如房地产
合作开发、股权投资类项目、技术合作与知识产权许可类业务。

【类型四】信用评价体系隐性地方保护 —— 招投标及资质认定环节
核心特征：部分地区招投标信用加分体系仅认可本地奖项、本地项目业绩，外地企业因在本地
信用系统中缺乏历史记录而天然处于评分劣势，即便产品或报价具备竞争力也难以中标；由此
衍生的招投标合同纠纷，属地法院在证据采信时亦可能倾向沿用本地化评价规则。
参考模式：多地招投标信用评价制度被监管部门列入地方保护/隐性壁垒整治清单，核心问题
为评价指标体系过度绑定本地业绩与本地荣誉，客观上排斥外地新进入企业。
适用产业类推方向：以政府或国企招投标为主要业务模式的行业（工程建设、系统集成、
政府采购服务类企业）。

三、本模块生成时必须遵循的结构要求
1. 【类案检索方向】：根据申报企业所属产业，从上述四大类型中选取最贴近的1-2类作为主要
   类比方向（不限于示例产业，需结合企业实际业务模式合理类推，如制造业侧重类型一/类型二、
   涉政府项目/工程类侧重类型二/类型四、涉合作开发或股权合作类侧重类型三）。
2. 【地方保护风险初步研判】：基于公开可查的类案信息和一般司法实践规律，客观分析目标地区
   在该类纠纷中是否存在需要关注的地方保护倾向迹象（无法获得目标地区具体司法数据时，应
   明确标注为"[需实地核实/建议委托当地律师尽调]"，不得凭空捏造具体案号或数据，不得将
   本方法论中的参考案例直接嫁接为目标地区的真实案例）。
3. 【上级纠错机制评估】：说明若发生纠纷，是否存在可预期的省高院/最高法层面的救济与统一
   裁判尺度机制，或市场监管总局等部门的行政层面纠偏渠道，作为判断该地区司法环境
   "可救济性"的重要依据。
4. 【结论与防控建议】：给出目标地区法治化营商环境的风险分级建议（如：低风险/中等风险/
   需重点关注），并提出可落地的防控建议（如：合同争议解决条款设计——约定仲裁或异地管辖、
   选择信誉良好的本地合作方、引入第三方履约担保机制、聘请本地及外部双重法律顾问、
   提前核实当地招投标信用评价规则对外地企业的适用情况等）。

四、强制免责与合规要求
- 本模块所有案例类型、案例特征均为方法论参考模板，严禁将参考案例中的具体案号、当事人
  名称、金额等信息移植为目标地区的真实数据，严禁编造目标地区不存在的具体案号或虚构
  司法数据冒充真实检索结果。
- 涉及目标地区具体司法倾向的结论性表述，必须使用"根据公开类案规律初步研判""建议委托
  当地律师进一步核实"等审慎措辞，不得作绝对化断言。
- 输出第一行必须明确写上：
  **重要提示：本方案/分析仅供参考，不构成任何正式的投资、招商、决策或法律建议，具体司法
  环境判断请以属地专业律师尽调意见为准。**
"""

SYSTEM_LEGAL_RISK = f"""你是一位同时具备政府产业招商顾问视角与执业律师专业背景的复合型顾问，
擅长从"类案检索 + 司法裁判倾向研判"角度，评估企业跨地域落地目标地区的法律环境风险。
严格使用 Markdown 格式输出，不要添加多余说明。语气正式、专业、审慎，避免绝对化断言。
所有关键数据、无法核实的具体案例信息使用 [占位符] 或 [需实地核实] 标记。

{LEGAL_RISK_REFERENCE}

现在请依据上述方法论框架，结合以下项目信息，生成对应章节内容。"""

USER_PROJECT_INFO_TEMPLATE = """目标地区：{target}
项目名称：{project}
申报主体：{company}
所属产业：{industry}
总投资：{investment} 万元
核心亮点及材料：
{highlights_and_extra}"""

# ====================== SECTIONS：与原版保持一致，仅第十章沿用上方优化后的 System Prompt ======================
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
    {
        "id": "ten_legal",
        "title": "十、目标地区司法环境与类案法律风险专项分析",
        "model": STRONG_MODEL,
        "system": SYSTEM_LEGAL_RISK,  # 使用专属 system prompt，其余章节继续使用 SYSTEM_BASE
    },
]

# ====================== 预填充"项目基本情况与核心亮点"默认内容（保持不变） ======================
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
- 2020年12月，首发星"智星一号A星"搭载长征八号火箭在文昌发射升空；
- 2022年5月，"智星三号A星"搭载天舟四号货运飞船入轨，是国内首家通过货运飞船发射卫星的民营企业；
- 2024年2月，自研雷达卫星"济高科创号"搭载捷龙三号火箭入轨并投入商业运营，是国内首颗3D打印结构的星载一体化设计雷达卫星。
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

    # ================== 生成逻辑（保持不变：system prompt 按章节动态取用） ==================
    full_result_parts = {}
    total_start = time.time()
    progress_bar = st.progress(0)
    status_text = st.empty()

    for idx, section in enumerate(SECTIONS):
        status_text.text(f"正在生成第 {idx+1} / {len(SECTIONS)} 部分（预计总耗时 60-140 秒）")
        try:
            section_system_prompt = section.get("system", SYSTEM_BASE)
            response = client.chat.completions.create(
                model=section.get("model", FAST_MODEL),
                messages=[
                    {"role": "system", "content": section_system_prompt},
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

    # ================== 醒目免责提示（保持不变） ==================
    st.warning("**重要提示：本方案/分析仅供参考，不构成任何正式的投资、招商、决策或法律建议。**")

    st.markdown("### 生成结果")
    for section in SECTIONS:
        title = section["title"]
        content = full_result_parts.get(section["id"], "（无内容）")
        if section["id"] == "zero":
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
            if section["id"] == "ten_legal":
                st.caption("注：本章方法论参考自类案检索框架，具体案例信息以属地律师尽调结论为准。")
        st.markdown("---")

    full_md_content = ""
    for sec in SECTIONS:
        full_md_content += f"# {sec['title']}\n\n"
        full_md_content += full_result_parts.get(sec["id"], "") + "\n\n---\n\n"

    safe_filename = f"{project_name.replace(' ', '_')}_{target_region.replace(' ', '_') or '未知地区'}_{time.strftime('%Y%m%d')}"

    st.download_button(
        label="下载纯文本版",
        data=full_md_content,
        file_name=f"{safe_filename}_纯文本.txt",
        mime="text/plain"
    )
