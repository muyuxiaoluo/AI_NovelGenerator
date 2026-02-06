# consistency_checker.py
# -*- coding: utf-8 -*-
from llm_adapters import create_llm_adapter

# ============== 增强版一致性检查提示词 ==============
CONSISTENCY_PROMPT = """\
请作为专业文学逻辑分析师，使用以下系统化框架检查新章节与已有摘要和实体属性的一致性：

### 【第一阶段：基础事实核对】
1. **关键实体状态检查**：
   - 人物生理/心理状态是否一致（伤势、情绪、能力水平）
   - 物品属性/归属是否一致（谁拥有、在哪、状态如何）
   - 环境/地点特征是否一致（已被摧毁、完好、特定布局）

2. **实体属性一致性检查（重点）**：
   - **颜色属性**：光罩、法术、特效的颜色是否一致？（如：淡黄色不能变成淡蓝色）
   - **身份/职位**：人物的身份、职位是否一致？（如：杨尘是术研院主事，不能变成城防军队长）
   - **状态属性**：阵法、道具的状态是否一致？（如：阵法完好不能说成需要修复）
   - **位置属性**：人物、物品的位置是否合理变化？

3. **时间线硬性冲突检查**：
   - 事件发生的绝对时间点是否冲突（如"三天前"vs"昨天"）
   - 持续时间是否合理（任务完成时间、恢复时间）
   - 时序关系是否颠倒（A在B之前发生）

### 【第二阶段：因果逻辑深度分析】
4. **明确因果关系验证**：
   - 当章节中出现"因为A所以B"表述时：
     a) 检查摘要中是否已确立此因果关系
     b) 若无，这是否为新信息？若是，是否与已有事实冲突？
     c) 若是角色主观认为，是否标记为"角色观点"而非事实？

5. **角色动机一致性检查**：
   - 角色的行为动机是否与摘要中揭示的性格、目标一致？
   - 角色新产生的动机是否有合理触发事件？
   - 特别注意"为某人做某事"类表述，需验证：
     * 受益方是否确实需要此行动？
     * 行动者是否有能力/意图执行？
     * 摘要中是否暗示过此动机？

6. **未解之谜处理规则**：
   - 摘要中标记为"未解之谜"的内容，章节中是否给出了明确答案？
   - 若给出答案，是否与已有线索矛盾？
   - 若添加新线索，是否破坏了谜题的公平性？

### 【第三阶段：主观认知与客观现实对照】
7. **角色内心活动真实性检查**：
   - 角色的回忆/反思内容是否与已知事实匹配？
   - 角色对他人行为的解读是否有事实依据？
   - 角色自我归因（如"都是我的错"）是否基于已发生事件？

8. **对话信息准确性检查**：
   - 角色陈述的"事实"是否与其所知信息一致？
   - 角色是否有途径获得所述信息？
   - 对话中的谣言/误解是否与叙述者提供的事实区分明确？

### 【第四阶段：设定与规则连续性】
9. **能力/力量体系一致性**：
   - 角色能力使用是否遵循已建立的规则？
   - 新展示的能力是否在之前有伏笔或解释？
   - 能力消耗/代价是否与之前描述一致？

10. **社会关系动态检查**：
    - 角色间的关系状态是否与摘要一致（敌对、友好、未知）？
    - 新出现的互动是否基于已有关系合理发展？
    - 群体态度（如全镇对主角的看法）变化是否有触发事件？

### 【输出格式要求】

**【发现的确切逻辑错误】**
（按严重程度排序）

错误编号：[序号]
- **错误类型**：[事实冲突/因果矛盾/时间线错误/属性不一致]
- **问题位置**：[章节中的具体引用]
- **冲突摘要**：[摘要中的相关描述]
- **错误分析**：[详细解释为何矛盾]
- **修正方案**：[提供1-3种修改建议，标明推荐度]

**【潜在风险点】**
（虽未直接冲突但可能引发后续问题）

风险编号：[序号]
- **风险描述**：
- **可能后果**：
- **预防建议**：

【前文摘要】：
{global_summary}

【角色状态档案】：
{character_state}

【已记录的未解决冲突或剧情要点】：
{plot_arcs}

【章节正文】：
{chapter_text}

请列出你发现的所有严重逻辑漏洞和建议。如果没有明显漏洞，请直接回复"无明显冲突"。
格式要求：
1. [错误类型] 具体描述...
2. [错误类型] 具体描述...
"""

def check_consistency(
    character_state: str,
    global_summary: str,
    chapter_text: str,
    api_key: str,
    base_url: str,
    model_name: str,
    temperature: float = 0.3,
    plot_arcs: str = "",
    interface_format: str = "OpenAI",
    max_tokens: int = 2048,
    timeout: int = 600
) -> str:
    """
    调用模型做一致性检查，重点关注实体属性一致性。
    新增: 会额外检查对"未解决冲突或剧情要点"（plot_arcs）的衔接情况。
    
    Args:
        character_state: 角色状态档案
        global_summary: 前文摘要
        chapter_text: 章节正文
        api_key: API密钥
        base_url: API基础URL
        model_name: 模型名称
        temperature: 温度参数
        plot_arcs: 未解决冲突或剧情要点
        interface_format: 接口格式
        max_tokens: 最大token数
        timeout: 超时时间
    
    Returns:
        一致性检查结果
    """
    prompt = CONSISTENCY_PROMPT.format(
        character_state=character_state,
        global_summary=global_summary,
        plot_arcs=plot_arcs,
        chapter_text=chapter_text
    )

    llm_adapter = create_llm_adapter(
        interface_format=interface_format,
        base_url=base_url,
        model_name=model_name,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout
    )

    # 调试日志
    print("\n[ConsistencyChecker] Prompt >>>", prompt)

    response = llm_adapter.invoke(prompt)
    if not response:
        return "审校Agent无回复"
    
    # 调试日志
    print("[ConsistencyChecker] Response <<<", response)

    return response
