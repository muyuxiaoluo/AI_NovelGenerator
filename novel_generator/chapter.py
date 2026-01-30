# novel_generator/chapter.py
# -*- coding: utf-8 -*-
"""
章节草稿生成及获取历史章节文本、当前章节摘要等
"""
import os
import logging
from llm_adapters import create_llm_adapter
from prompt_definitions import (
    first_chapter_draft_prompt, 
    next_chapter_draft_prompt, 
    summarize_recent_chapters_prompt,
    knowledge_filter_prompt,
    knowledge_search_prompt,
    LOGIC_CHECK_PROMPT,
    REWRITE_WITH_FEEDBACK_PROMPT,
    REFINE_DIRECTORY_PROMPT,
)
from chapter_directory_parser import get_chapter_info_from_blueprint
from novel_generator.common import invoke_with_cleaning
from utils import extract_relevant_segments, read_file, clear_file_content, save_string_to_txt
from novel_generator.vectorstore_utils import (
    get_relevant_context_from_vector_store,
    load_vector_store  # 添加导入
)
logging.basicConfig(
    filename='app.log',      # 日志文件名
    filemode='a',            # 追加模式（'w' 会覆盖）
    level=logging.INFO,      # 记录 INFO 及以上级别的日志
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def extract_character_relationships(character_state_text: str) -> str:
    """
    从角色状态文本中提取角色之间的关系网。
    解析格式：
    角色名：
    【当前状态】
    ├──关系: 角色1（关系描述）、角色2（关系描述）
    """
    if not character_state_text:
        return "（暂无角色关系网信息）"
    
    relationships_dict = {}
    current_char = None
    lines = character_state_text.split('\n')
    
    try:
        for i, line in enumerate(lines):
            # 识别活跃区/潜伏区的角色名（以 "角色名：" 结尾，不包含特殊符号）
            if line.endswith('：') and not line.startswith('├') and not line.startswith('│') and not line.startswith('='):
                potential_char = line.replace('：', '').strip()
                # 排除非角色的标题行
                if potential_char and potential_char not in ['【核心人设】', '【当前状态】']:
                    current_char = potential_char
                    relationships_dict[current_char] = []
            
            # 提取关系行（格式：├──关系: ...）
            if current_char and '├──关系:' in line:
                # 提取冒号后的内容
                rel_part = line.split('├──关系:')[1].strip()
                if rel_part:
                    relationships_dict[current_char].append(rel_part)
    except Exception as e:
        logging.warning(f"解析角色关系网失败: {e}")
        return "（角色关系网解析失败）"
    
    # 过滤空关系
    relationships_dict = {k: v for k, v in relationships_dict.items() if v}
    
    if not relationships_dict:
        return "（暂无角色关系网信息）"
    
    # 格式化输出为易读的关系网
    result_lines = ["【人物关系网概览】"]
    for char_name, relations in relationships_dict.items():
        result_lines.append(f"\n{char_name}：")
        for rel in relations:
            result_lines.append(f"  ├─ {rel}")
    
    return "\n".join(result_lines)

def get_last_n_chapters_text(chapters_dir: str, current_chapter_num: int, n: int = 3) -> list:
    """
    从目录 chapters_dir 中获取最近 n 章的文本内容，返回文本列表。
    """
    texts = []
    start_chap = max(1, current_chapter_num - n)
    for c in range(start_chap, current_chapter_num):
        chap_file = os.path.join(chapters_dir, f"chapter_{c}.txt")
        if os.path.exists(chap_file):
            text = read_file(chap_file).strip()
            texts.append(text)
        else:
            texts.append("")
    return texts

def summarize_recent_chapters(
    interface_format: str,
    api_key: str,
    base_url: str,
    model_name: str,
    temperature: float,
    max_tokens: int,
    chapters_text_list: list,
    novel_number: int,            # 新增参数
    chapter_info: dict,           # 新增参数
    next_chapter_info: dict,      # 新增参数
    filepath: str | None = None,  # 【修复类型注解】添加|None允许可选参数
    global_summary: str = "",    # 新增：传入全局摘要以匹配 prompt 占位符
    character_relationships: str = "",  # 新增：角色关系网
    previous_chapter_excerpt: str = "", # 新增：上一章结尾内容
    timeout: int = 600
) -> str:  # 修改返回值类型为 str，不再是 tuple
    """
    根据前三章内容生成当前章节的精准摘要。(支持伏笔注入)
    如果解析失败，则返回空字符串。
    """
    try:
        combined_text = "\n".join(chapters_text_list).strip()
        if not combined_text and not global_summary:
            return ""
            
        # 限制组合文本长度
        max_combined_length = 4000
        if len(combined_text) > max_combined_length:
            combined_text = combined_text[-max_combined_length:]

        # === 【新增逻辑】读取伏笔库内容 ===
        foreshadowing_text = "（暂无伏笔记录）"
        if filepath:
            try:
                record_file = os.path.join(filepath, "foreshadowing_records.txt")
                if os.path.exists(record_file):
                    content = read_file(record_file).strip()
                    if content:
                        # 截取最后 3000 字符防止 Token 溢出，或者根据模型窗口决定
                        foreshadowing_text = content[-3000:] if len(content) > 3000 else content
            except Exception as e:
                logging.warning(f"摘要生成时读取伏笔库失败: {e}")
            
        llm_adapter = create_llm_adapter(
            interface_format=interface_format,
            base_url=base_url,
            model_name=model_name,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout
        )
        
        # 确保所有参数都有默认值
        chapter_info = chapter_info or {}
        next_chapter_info = next_chapter_info or {}
        
        # 使用安全的 dict 来格式化 prompt，避免因为 prompt 占位符变动导致 KeyError
        class _SafeDict(dict):
            def __missing__(self, key):
                return ""

        # 【关键修复】为 summarize_recent_chapters_prompt 创建专用的 prompt_values
        # 仅包含当前章节的必要信息，不包含下一章信息，以防止 LLM 混淆
        summarize_prompt_values = {
            "global_summary": global_summary,
            "previous_chapter_excerpt": previous_chapter_excerpt,
            "novel_number": novel_number,
            "chapter_title": chapter_info.get("chapter_title", "未命名"),
            "chapter_role": chapter_info.get("chapter_role", "常规章节"),
            "chapter_purpose": chapter_info.get("chapter_purpose", "内容推进"),
            "suspense_level": chapter_info.get("suspense_level", "中等"),
            "foreshadowing": chapter_info.get("foreshadowing", "无"),
            "plot_twist_level": chapter_info.get("plot_twist_level", "★☆☆☆☆"),
            "chapter_summary": chapter_info.get("chapter_summary", ""),
            "foreshadowing_records": foreshadowing_text,
            "character_relationships": character_relationships,  # 新增关系网
            # 下一章信息（仅用于逻辑检查，不混入生成过程）
            "next_chapter_number": novel_number + 1,
            "next_chapter_title": next_chapter_info.get("chapter_title", "（未命名）"),
            "next_chapter_role": next_chapter_info.get("chapter_role", "过渡章节"),
        }
        
        # 完整的 prompt_values（用于其他 prompt）
        prompt_values = {
            "global_summary": global_summary,
            "previous_chapter_excerpt": previous_chapter_excerpt,
            "novel_number": novel_number,
            "chapter_title": chapter_info.get("chapter_title", "未命名"),
            "chapter_role": chapter_info.get("chapter_role", "常规章节"),
            "chapter_purpose": chapter_info.get("chapter_purpose", "内容推进"),
            "suspense_level": chapter_info.get("suspense_level", "中等"),
            "foreshadowing": chapter_info.get("foreshadowing", "无"),
            "plot_twist_level": chapter_info.get("plot_twist_level", "★☆☆☆☆"),
            "chapter_summary": chapter_info.get("chapter_summary", ""),
            "foreshadowing_records": foreshadowing_text,
            "character_relationships": character_relationships,
            # 下一章信息
            "next_chapter_number": novel_number + 1,
            "next_chapter_title": next_chapter_info.get("chapter_title", "（未命名）"),
            "next_chapter_role": next_chapter_info.get("chapter_role", "过渡章节"),
            "next_chapter_purpose": next_chapter_info.get("chapter_purpose", "承上启下"),
            "next_chapter_summary": next_chapter_info.get("chapter_summary", "衔接过渡内容"),
            "next_chapter_suspense_level": next_chapter_info.get("suspense_level", "中等"),
            "next_chapter_foreshadowing": next_chapter_info.get("foreshadowing", "无特殊伏笔"),
            "next_chapter_plot_twist_level": next_chapter_info.get("plot_twist_level", "★☆☆☆☆")
        }

        # 【关键修复】使用 summarize_prompt_values 而不是 prompt_values
        # 这样可以防止下一章的信息泄露到 summarize_recent_chapters_prompt 中
        prompt = summarize_recent_chapters_prompt.format_map(_SafeDict(summarize_prompt_values))
        
        response_text = invoke_with_cleaning(llm_adapter, prompt)
        
        # 如果您有 extract_summary_from_response 函数，可以使用它
        # 如果没有，直接使用 response_text 也是安全的，因为 Prompt 已经要求直接输出了
        if 'extract_summary_from_response' in globals():
            summary = extract_summary_from_response(response_text)
        else:
            summary = response_text
        
        if not summary:
            logging.warning("Failed to extract summary, using full response")
            return response_text[:2000]  # 限制长度
            
        return summary[:2000]  # 限制摘要长度
        
    except Exception as e:
        logging.error(f"Error in summarize_recent_chapters: {str(e)}")
        return ""

def extract_summary_from_response(response_text: str) -> str:
    """从响应文本中提取摘要部分"""
    if not response_text:
        return ""
        
    # 查找摘要标记
    summary_markers = [
        "当前章节摘要:", 
        "章节摘要:",
        "摘要:",
        "本章摘要:"
    ]
    
    for marker in summary_markers:
        if (marker in response_text):
            parts = response_text.split(marker, 1)
            if len(parts) > 1:
                return parts[1].strip()
    
    return response_text.strip()

def format_chapter_info(chapter_info: dict) -> str:
    """将章节信息字典格式化为文本"""
    template = """
章节编号：第{number}章
章节标题：《{title}》
章节定位：{role}
核心作用：{purpose}
主要人物：{characters}
关键道具：{items}
场景地点：{location}
伏笔设计：{foreshadow}
悬念密度：{suspense}
转折程度：{twist}
章节简述：{summary}
"""
    return template.format(
        number=chapter_info.get('chapter_number', '未知'),
        title=chapter_info.get('chapter_title', '未知'),
        role=chapter_info.get('chapter_role', '未知'),
        purpose=chapter_info.get('chapter_purpose', '未知'),
        characters=chapter_info.get('characters_involved', '未指定'),
        items=chapter_info.get('key_items', '未指定'),
        location=chapter_info.get('scene_location', '未指定'),
        foreshadow=chapter_info.get('foreshadowing', '无'),
        suspense=chapter_info.get('suspense_level', '一般'),
        twist=chapter_info.get('plot_twist_level', '★☆☆☆☆'),
        summary=chapter_info.get('chapter_summary', '未提供')
    )

def parse_search_keywords(response_text: str) -> list:
    """解析新版关键词格式（示例输入：'科技公司·数据泄露\n地下实验室·基因编辑'）"""
    return [
        line.strip().replace('·', ' ')
        for line in response_text.strip().split('\n')
        if '·' in line
    ][:5]  # 最多取5组

def apply_content_rules(texts: list, novel_number: int) -> list:
    """
    [修改版] 移除硬编码的跳过逻辑。
    保留原始内容，只做简单的去重或标记，把判断交给 LLM。
    """
    processed = []
    seen_hashes = set()
    
    for text in texts:
        # 1. 简单去重
        clean_text = text.strip()
        text_hash = hash(clean_text)
        if text_hash in seen_hashes:
            continue
        seen_hashes.add(text_hash)
        
        # 2. 移除所有 [SKIP] / [MOD] 标记逻辑
        # 只要检索到了，就说明向量认为它相关，直接透传给 LLM
        processed.append(clean_text)
            
    return processed

def apply_knowledge_rules(contexts: list, chapter_num: int) -> list:
    """
    [修改版] 废弃基于章节距离的过滤。
    只要是检索出来的，说明向量相似度高，都应该保留给 Prompt 处理。
    """
    # 直接返回，不做任何删减
    return contexts

def get_filtered_knowledge_context(
    api_key: str,
    base_url: str,
    model_name: str,
    interface_format: str,
    embedding_adapter,
    filepath: str,
    chapter_info: dict,
    retrieved_texts: list,
    max_tokens: int = 2048,
    timeout: int = 600
) -> str:
    """优化后的知识过滤处理"""
    # 1. 如果没有检索到内容，直接返回
    if not retrieved_texts:
        return "（无相关知识库内容，请基于前文设定创作）"

    try:
        # 2. 调用修改后的规则（现在只是简单的去重和标记）
        # 注意：这里不再传入 chapter_num，因为新版函数不需要它
        processed_texts = apply_content_rules(retrieved_texts, chapter_info.get('chapter_number', 0))

        llm_adapter = create_llm_adapter(
            interface_format=interface_format,
            base_url=base_url,
            model_name=model_name,
            api_key=api_key,
            temperature=0.1, # 再次降低温度，强制其“死板”
            max_tokens=max_tokens,
            timeout=timeout
        )
        
        # 3. 格式化检索文本：保留更多长度，不要随意截断
        # 只有当总长度极大时才进行截断
        formatted_texts = []
        for i, text in enumerate(processed_texts, 1):
            # 允许单条检索内容更长，以便保留环境描写的全貌
            clean_text = text.strip()
            formatted_texts.append(f"--- 片段 {i} ---\n{clean_text}")

        all_retrieved_text = "\n".join(formatted_texts)

        # 4. 构造 Prompt
        formatted_chapter_info = (
            f"章节：第{chapter_info.get('chapter_number')}章 {chapter_info.get('chapter_title')}\n"
            f"场景：{chapter_info.get('scene_location', '未知')}\n"
            f"涉及人物：{chapter_info.get('characters_involved', '未知')}\n"
            f"关键道具：{chapter_info.get('key_items', '无')}"
        )

        prompt = knowledge_filter_prompt.format(
            chapter_info=formatted_chapter_info,
            retrieved_texts=all_retrieved_text
        )
        
        filtered_content = invoke_with_cleaning(llm_adapter, prompt)
        return filtered_content if filtered_content else "（知识内容过滤后为空）"
        
    except Exception as e:
        logging.error(f"Error in knowledge filtering: {str(e)}")
        # 降级策略：如果过滤失败，直接返回前2条原始检索结果，保证至少有东西可用
        fallback = "\n".join(retrieved_texts[:2])
        return f"[过滤失败，显示原始检索]:\n{fallback}"

def build_chapter_prompt(
    api_key: str,
    base_url: str,
    model_name: str,
    filepath: str,
    novel_number: int,
    word_number: int,
    temperature: float,
    user_guidance: str,
    characters_involved: str,
    key_items: str,
    scene_location: str,
    time_constraint: str,
    embedding_api_key: str,
    embedding_url: str,
    embedding_interface_format: str,
    embedding_model_name: str,
    embedding_retrieval_k: int = 2,
    interface_format: str = "openai",
    max_tokens: int = 2048,
    timeout: int = 600
) -> str:
    """
    构造当前章节的请求提示词（完整实现版）
    修改重点：
    1. 优化知识库检索流程
    2. 新增内容重复检测机制
    3. 集成提示词应用规则
    """
    # 读取基础文件
    arch_file = os.path.join(filepath, "Novel_architecture.txt")
    novel_architecture_text = read_file(arch_file)
    directory_file = os.path.join(filepath, "Novel_directory.txt")
    blueprint_text = read_file(directory_file)
    global_summary_file = os.path.join(filepath, "global_summary.txt")
    global_summary_text = read_file(global_summary_file)
    character_state_file = os.path.join(filepath, "character_state.txt")
    character_state_text = read_file(character_state_file)
    
    # 获取章节信息
    chapter_info = get_chapter_info_from_blueprint(blueprint_text, novel_number)
    chapter_title = chapter_info["chapter_title"]
    chapter_role = chapter_info["chapter_role"]
    chapter_purpose = chapter_info["chapter_purpose"]
    suspense_level = chapter_info["suspense_level"]
    foreshadowing = chapter_info["foreshadowing"]
    plot_twist_level = chapter_info["plot_twist_level"]
    chapter_summary = chapter_info["chapter_summary"]

    # 获取下一章节信息
    next_chapter_number = novel_number + 1
    next_chapter_info = get_chapter_info_from_blueprint(blueprint_text, next_chapter_number)
    next_chapter_title = next_chapter_info.get("chapter_title", "（未命名）")
    next_chapter_role = next_chapter_info.get("chapter_role", "过渡章节")
    next_chapter_purpose = next_chapter_info.get("chapter_purpose", "承上启下")
    next_chapter_suspense = next_chapter_info.get("suspense_level", "中等")
    next_chapter_foreshadow = next_chapter_info.get("foreshadowing", "无特殊伏笔")
    next_chapter_twist = next_chapter_info.get("plot_twist_level", "★☆☆☆☆")
    next_chapter_summary = next_chapter_info.get("chapter_summary", "衔接过渡内容")

    # 创建章节目录
    chapters_dir = os.path.join(filepath, "chapters")
    os.makedirs(chapters_dir, exist_ok=True)

    # 第一章特殊处理
    if novel_number == 1:
        return first_chapter_draft_prompt.format(
            novel_number=novel_number,
            word_number=word_number,
            chapter_title=chapter_title,
            chapter_role=chapter_role,
            chapter_purpose=chapter_purpose,
            suspense_level=suspense_level,
            foreshadowing=foreshadowing,
            plot_twist_level=plot_twist_level,
            chapter_summary=chapter_summary,
            characters_involved=characters_involved,
            key_items=key_items,
            scene_location=scene_location,
            time_constraint=time_constraint,
            user_guidance=user_guidance,
            novel_setting=novel_architecture_text
        )

    # 获取前文内容和摘要
    recent_texts = get_last_n_chapters_text(chapters_dir, novel_number, n=3)
    
    # 获取前一章结尾
    previous_excerpt = ""
    for text in reversed(recent_texts):
        if text.strip():
            previous_excerpt = text[-800:] if len(text) > 800 else text
            break
    
    # 提取角色关系网
    character_relationships_summary = extract_character_relationships(character_state_text)
    
    try:
        logging.info("Attempting to generate summary")
        short_summary = summarize_recent_chapters(
            interface_format=interface_format,
            api_key=api_key,
            base_url=base_url,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            chapters_text_list=recent_texts,
            novel_number=novel_number,
            chapter_info=chapter_info,
            next_chapter_info=next_chapter_info,
            filepath=filepath,  # 【修复】添加filepath参数以支持伏笔库注入
            global_summary=global_summary_text,
            character_relationships=character_relationships_summary,  # 新增关系网参数
            previous_chapter_excerpt=previous_excerpt,  # 新增参数：上一章结尾内容
            timeout=timeout
        )
        logging.info("Summary generated successfully")
    except Exception as e:
        logging.error(f"Error in summarize_recent_chapters: {str(e)}")
        short_summary = "（摘要生成失败）"

    # 知识库检索和处理
    try:
        # 生成检索关键词
        llm_adapter = create_llm_adapter(
            interface_format=interface_format,
            base_url=base_url,
            model_name=model_name,
            api_key=api_key,
            temperature=0.3,
            max_tokens=max_tokens,
            timeout=timeout
        )
        
        search_prompt = knowledge_search_prompt.format(
            chapter_number=novel_number,
            chapter_title=chapter_title,
            characters_involved=characters_involved,
            key_items=key_items,
            scene_location=scene_location,
            chapter_role=chapter_role,
            chapter_purpose=chapter_purpose,
            foreshadowing=foreshadowing,
            short_summary=short_summary,
            user_guidance=user_guidance,
            time_constraint=time_constraint
        )
        
        search_response = invoke_with_cleaning(llm_adapter, search_prompt)
        keyword_groups = parse_search_keywords(search_response)

        # 执行向量检索
        all_contexts = []
        from embedding_adapters import create_embedding_adapter
        embedding_adapter = create_embedding_adapter(
            embedding_interface_format,
            embedding_api_key,
            embedding_url,
            embedding_model_name
        )
        
        store = load_vector_store(embedding_adapter, filepath)
        if store:
            collection_size = store._collection.count()
            actual_k = min(embedding_retrieval_k, max(1, collection_size))
            
            for group in keyword_groups:
                # 1. 获取原始长文本 (可能是整章)
                raw_context = get_relevant_context_from_vector_store(
                    embedding_adapter=embedding_adapter,
                    query=group,
                    filepath=filepath,
                    k=actual_k
                )
                
                if raw_context:
                    # 2. [关键修改] 执行智能截取
                    # 将 query (如 "百草堂·内部陈设") 传进去，精准定位片段
                    precise_context = extract_relevant_segments(raw_context, group, window_size=800)
                    
                    # 3. 添加标签 (保持原有逻辑)
                    if any(kw in group.lower() for kw in ["技法", "手法", "模板"]):
                        all_contexts.append(f"[TECHNIQUE] {precise_context}")
                    elif any(kw in group.lower() for kw in ["设定", "技术", "世界观"]):
                        all_contexts.append(f"[SETTING] {precise_context}")
                    else:
                        all_contexts.append(f"[GENERAL] {precise_context}")

        # 应用内容规则 (下文保持不变)
        processed_contexts = apply_content_rules(all_contexts, novel_number)
        
        # 执行知识过滤
        chapter_info_for_filter = {
            "chapter_number": novel_number,
            "chapter_title": chapter_title,
            "chapter_role": chapter_role,
            "chapter_purpose": chapter_purpose,
            "characters_involved": characters_involved,
            "key_items": key_items,
            "scene_location": scene_location,
            "foreshadowing": foreshadowing,  # 修复拼写错误
            "suspense_level": suspense_level,
            "plot_twist_level": plot_twist_level,
            "chapter_summary": chapter_summary,
            "time_constraint": time_constraint
        }
        
        filtered_context = get_filtered_knowledge_context(
            api_key=api_key,
            base_url=base_url,
            model_name=model_name,
            interface_format=interface_format,
            embedding_adapter=embedding_adapter,
            filepath=filepath,
            chapter_info=chapter_info_for_filter,
            retrieved_texts=processed_contexts,
            max_tokens=max_tokens,
            timeout=timeout
        )
        
    except Exception as e:
        logging.error(f"知识处理流程异常：{str(e)}")
        filtered_context = "（知识库处理失败）"

    # 返回最终提示词
    return next_chapter_draft_prompt.format(
        user_guidance=user_guidance if user_guidance else "无特殊指导",
        global_summary=global_summary_text,
        previous_chapter_excerpt=previous_excerpt,
        character_state=character_state_text,
        short_summary=short_summary,
        novel_number=novel_number,
        chapter_title=chapter_title,
        chapter_role=chapter_role,
        chapter_purpose=chapter_purpose,
        suspense_level=suspense_level,
        foreshadowing=foreshadowing,
        plot_twist_level=plot_twist_level,
        chapter_summary=chapter_summary,
        word_number=word_number,
        characters_involved=characters_involved,
        key_items=key_items,
        scene_location=scene_location,
        time_constraint=time_constraint,
        next_chapter_number=next_chapter_number,
        next_chapter_title=next_chapter_title,
        next_chapter_role=next_chapter_role,
        next_chapter_purpose=next_chapter_purpose,
        next_chapter_suspense_level=next_chapter_suspense,
        next_chapter_foreshadowing=next_chapter_foreshadow,
        next_chapter_plot_twist_level=next_chapter_twist,
        next_chapter_summary=next_chapter_summary,
        filtered_context=filtered_context
    )

def generate_chapter_draft(
    api_key: str,
    base_url: str,
    model_name: str, 
    filepath: str,
    novel_number: int,
    word_number: int,
    temperature: float,
    user_guidance: str,
    characters_involved: str,
    key_items: str,
    scene_location: str,
    time_constraint: str,
    embedding_api_key: str,
    embedding_url: str,
    embedding_interface_format: str,
    embedding_model_name: str,
    embedding_retrieval_k: int = 2,
    interface_format: str = "openai",
    max_tokens: int = 2048,
    timeout: int = 600,
    custom_prompt_text: str | None = None
) -> str:
    """
    生成章节草稿，支持自定义提示词
    """
    if custom_prompt_text is None:
        prompt_text = build_chapter_prompt(
            api_key=api_key,
            base_url=base_url,
            model_name=model_name,
            filepath=filepath,
            novel_number=novel_number,
            word_number=word_number,
            temperature=temperature,
            user_guidance=user_guidance,
            characters_involved=characters_involved,
            key_items=key_items,
            scene_location=scene_location,
            time_constraint=time_constraint,
            embedding_api_key=embedding_api_key,
            embedding_url=embedding_url,
            embedding_interface_format=embedding_interface_format,
            embedding_model_name=embedding_model_name,
            embedding_retrieval_k=embedding_retrieval_k,
            interface_format=interface_format,
            max_tokens=max_tokens,
            timeout=timeout
        )
    else:
        prompt_text = custom_prompt_text

    chapters_dir = os.path.join(filepath, "chapters")
    os.makedirs(chapters_dir, exist_ok=True)

    llm_adapter = create_llm_adapter(
        interface_format=interface_format,
        base_url=base_url,
        model_name=model_name,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout
    )

    chapter_content = invoke_with_cleaning(llm_adapter, prompt_text)
    if not chapter_content.strip():
        logging.warning("Generated chapter draft is empty.")
    chapter_file = os.path.join(chapters_dir, f"chapter_{novel_number}.txt")
    clear_file_content(chapter_file)
    save_string_to_txt(chapter_content, chapter_file)
    logging.info(f"[Draft] Chapter {novel_number} generated as a draft.")
    return chapter_content


def analyze_chapter_logic(
    interface_format: str,
    api_key: str,
    base_url: str,
    model_name: str,
    chapter_content: str,
    filepath: str,
    novel_number: int = 0,
    temperature: float = 0.1,  # 逻辑检查需要低温度
    max_tokens: int = 2048,
    timeout: int = 600
) -> str:
    """
    调用大模型对生成的章节进行逻辑自检
    """
    try:
        global_summary = read_file(os.path.join(filepath, "global_summary.txt"))
        character_state = read_file(os.path.join(filepath, "character_state.txt"))
        # 尝试读取章节大纲以获取下一章概要，若不存在则传空字符串
        directory_file = os.path.join(filepath, "Novel_directory.txt")
        next_chapter_outline = "（无后续目录信息）"
        try:
            if os.path.exists(directory_file):
                blueprint_text = read_file(directory_file)
                # 若传入了 novel_number，则取下一章信息
                if novel_number and novel_number > 0:
                    next_info = get_chapter_info_from_blueprint(blueprint_text, novel_number + 1)
                    if next_info:
                        next_chapter_outline = f"第{novel_number+1}章《{next_info.get('chapter_title','（未命名）')}》：定位：{next_info.get('chapter_role','')}; 简述：{next_info.get('chapter_summary','') }"
                else:
                    # 若未传入章节号，尽量摘取前几行作为概要
                    lines = blueprint_text.splitlines()
                    next_chapter_outline = '\n'.join(lines[:10]) if lines else next_chapter_outline
        except Exception:
            next_chapter_outline = "（读取目录失败）"

        prompt = LOGIC_CHECK_PROMPT.format(
            global_summary=global_summary,
            character_state=character_state,
            next_chapter_outline=next_chapter_outline,
            chapter_content=chapter_content
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
        
        logging.info(f"开始逻辑自检，interface={interface_format}, model={model_name}")
        analysis_result = invoke_with_cleaning(llm_adapter, prompt)
        return analysis_result

    except Exception as e:
        logging.error(f"逻辑自检失败: {str(e)}")
        return f"逻辑自检发生错误: {str(e)}"

def rewrite_chapter_with_feedback(
    interface_format: str,
    api_key: str,
    base_url: str,
    model_name: str,
    original_content: str,
    feedback: str,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    timeout: int = 600
) -> str:
    """
    根据反馈意见重写章节
    """
    try:
        prompt = REWRITE_WITH_FEEDBACK_PROMPT.format(
            original_content=original_content,
            feedback=feedback
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

        logging.info(f"开始根据反馈重写章节，interface={interface_format}, model={model_name}")
        new_content = invoke_with_cleaning(llm_adapter, prompt)
        return new_content

    except Exception as e:
        logging.error(f"重写失败: {str(e)}")
        return ""
    

def refine_chapter_detail(
    interface_format: str,
    api_key: str,
    base_url: str,
    model_name: str,
    chapter_range: str,         # 修改：传入范围描述，如 "第5-7章"
    novel_architecture: str,
    global_summary: str,
    current_outline: str,
    user_instruction: str,
    temperature: float = 0.7,
    max_tokens: int = 4096,     # 增加 token 限制，因为多章节内容较多
    timeout: int = 600
) -> str:
    """
    根据用户意见微调章节大纲 (支持多章节)
    """
    try:
        llm_adapter = create_llm_adapter(
            interface_format=interface_format,
            base_url=base_url,
            model_name=model_name,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout
        )
        
        prompt = REFINE_DIRECTORY_PROMPT.format(
            chapter_range=chapter_range,
            novel_architecture=novel_architecture if novel_architecture else "（暂无架构信息）",
            global_summary=global_summary if global_summary else "（暂无剧情摘要）",
            current_outline=current_outline,
            user_instruction=user_instruction
        )
        
        logging.info(f"正在微调大纲范围: {chapter_range} ...")
        refined_content = invoke_with_cleaning(llm_adapter, prompt)
        return refined_content
    except Exception as e:
        logging.error(f"微调章节大纲失败: {str(e)}")
        return ""
    