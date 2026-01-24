# novel_generator/finalization.py
# -*- coding: utf-8 -*-
"""
定稿章节和扩写章节（finalize_chapter、enrich_chapter_text）
[V3.0 分步执行 + 结构化伏笔库版]
"""
import os
import logging
import re
from llm_adapters import create_llm_adapter
from embedding_adapters import create_embedding_adapter
# 确保 prompt_definitions 里包含您最新的 FORESHADOWING_ANALYSIS_PROMPT
from prompt_definitions import summary_prompt, update_character_state_prompt, FORESHADOWING_ANALYSIS_PROMPT
from novel_generator.common import invoke_with_cleaning
from utils import read_file, clear_file_content, save_string_to_txt, append_text_to_file
from novel_generator.vectorstore_utils import update_vector_store

# -----------------------------------------------------------------------------
# 1. 独立功能：更新全局摘要
# -----------------------------------------------------------------------------
def update_global_summary(
    novel_number: int,
    filepath: str,
    api_key: str,
    base_url: str,
    model_name: str,
    interface_format: str,
    temperature: float = 0.5,
    max_tokens: int = 4096,
    timeout: int = 600
):
    logging.info(f"开始单独更新摘要: 第 {novel_number} 章")
    
    chapters_dir = os.path.join(filepath, "chapters")
    chapter_file = os.path.join(chapters_dir, f"chapter_{novel_number}.txt")
    
    if not os.path.exists(chapter_file):
        logging.error(f"找不到章节文件: {chapter_file}")
        return

    chapter_text = read_file(chapter_file)
    global_summary_file = os.path.join(filepath, "global_summary.txt")
    old_summary = read_file(global_summary_file)

    llm_adapter = create_llm_adapter(interface_format, base_url, model_name, api_key, temperature, max_tokens, timeout)
    
    prompt = summary_prompt.format(
        old_summary=old_summary,
        chapter_text=chapter_text
    )

    try:
        new_summary = invoke_with_cleaning(llm_adapter, prompt)
        if new_summary:
            save_string_to_txt(new_summary, global_summary_file)
            logging.info("全局摘要更新完成。")
    except Exception as e:
        logging.error(f"摘要更新失败: {e}")


# -----------------------------------------------------------------------------
# 2. 独立功能：更新角色状态
# -----------------------------------------------------------------------------
def update_character_state(
    novel_number: int,
    filepath: str,
    api_key: str,
    base_url: str,
    model_name: str,
    interface_format: str,
    temperature: float = 0.5,
    max_tokens: int = 4096,
    timeout: int = 600
):
    logging.info(f"开始单独更新角色状态: 第 {novel_number} 章")

    chapters_dir = os.path.join(filepath, "chapters")
    chapter_file = os.path.join(chapters_dir, f"chapter_{novel_number}.txt")
    if not os.path.exists(chapter_file):
        return

    chapter_text = read_file(chapter_file)
    char_state_file = os.path.join(filepath, "character_state.txt")
    old_state = read_file(char_state_file)

    llm_adapter = create_llm_adapter(interface_format, base_url, model_name, api_key, temperature, max_tokens, timeout)

    prompt = update_character_state_prompt.format(
        old_character_state=old_state,
        chapter_text=chapter_text
    )

    try:
        new_state = invoke_with_cleaning(llm_adapter, prompt)
        if new_state:
            save_string_to_txt(new_state, char_state_file)
            logging.info("角色状态表更新完成。")
    except Exception as e:
        logging.error(f"角色状态更新失败: {e}")


# -----------------------------------------------------------------------------
# 3. 独立功能：更新伏笔 (结构化解析版)
# -----------------------------------------------------------------------------

def save_structured_foreshadowing(filepath, novel_number, short_text, long_text):
    """
    辅助函数：将解析出的长短线伏笔插入到文件的对应区域
    """
    record_file = os.path.join(filepath, "foreshadowing_records.txt")
    
    # 1. 准备新内容 (如果为空则不写入该章节头)
    new_short_block = ""
    if short_text and "无" not in short_text and len(short_text) > 5:
        # 去掉大模型可能输出的 "1. xxx" 前面的编号，或者保留均可，这里直接保留原文
        new_short_block = f"第{novel_number}章：\n{short_text}\n"

    new_long_block = ""
    if long_text and "无" not in long_text and len(long_text) > 5:
        new_long_block = f"第{novel_number}章：\n{long_text}\n"

    if not new_short_block and not new_long_block:
        logging.info("本章无有效伏笔，跳过写入。")
        return

    # 2. 读取或初始化文件
    if os.path.exists(record_file):
        content = read_file(record_file)
    else:
        content = ""

    header_long = "=== 【长线伏笔】 ==="
    header_short = "=== 【短线伏笔】 ==="

    # 初始化模板
    if header_long not in content or header_short not in content:
        content = f"{header_long}\n\n\n{header_short}\n\n"

    # 3. 寻找插入点并拼接
    # 逻辑：找到 "=== 【短线伏笔】 ===" 的位置，把它作为分界线
    try:
        split_index = content.find(header_short)
        
        # 长线部分 (在 split_index 之前)
        long_section_raw = content[:split_index].rstrip()
        # 短线部分 (在 split_index 之后)
        short_section_raw = content[split_index:].rstrip()

        # 插入长线
        if new_long_block:
            long_section_raw += f"\n\n{new_long_block}"
        
        # 插入短线
        if new_short_block:
            short_section_raw += f"\n\n{new_short_block}"

        # 合并
        final_content = f"{long_section_raw}\n\n\n{short_section_raw}\n"
        
        save_string_to_txt(final_content, record_file)
        logging.info(f"伏笔库已更新 (结构化存储) - 第{novel_number}章")

    except Exception as e:
        logging.error(f"伏笔文件解析写入错误: {e}")
        # 降级：如果解析坏了，直接追加到末尾防止丢数据
        append_text_to_file(f"\n\n【第{novel_number}章补录】\n{long_text}\n{short_text}", record_file)


def update_foreshadowing_records(
    novel_number: int,
    filepath: str,
    api_key: str,
    base_url: str,
    model_name: str,
    interface_format: str,
    temperature: float = 0.5,
    max_tokens: int = 4096,
    timeout: int = 600
):
    logging.info(f"开始单独分析伏笔: 第 {novel_number} 章")

    chapters_dir = os.path.join(filepath, "chapters")
    chapter_file = os.path.join(chapters_dir, f"chapter_{novel_number}.txt")
    if not os.path.exists(chapter_file):
        return

    chapter_text = read_file(chapter_file)
    
    # 这里的适配器建议使用逻辑较强的模型
    llm_adapter = create_llm_adapter(interface_format, base_url, model_name, api_key, temperature, max_tokens, timeout)

    # 1. 调用 LLM
    prompt = FORESHADOWING_ANALYSIS_PROMPT.format(
        chapter_text=chapter_text,
        novel_number=novel_number
    )

    try:
        result = invoke_with_cleaning(llm_adapter, prompt)
        if not result:
            return

        # 2. 解析文本 (Regex)
        # 您的提示词格式为：
        # 【短线伏笔】：
        # ...
        # 【长线伏笔】：
        # ...
        
        # 提取短线内容
        short_match = re.search(r"【短线伏笔】：\s*(.*?)\s*(?=【长线伏笔】|$)", result, re.DOTALL)
        short_content = short_match.group(1).strip() if short_match else ""

        # 提取长线内容
        long_match = re.search(r"【长线伏笔】：\s*(.*?)\s*(?=---|[-]{3,}|$)", result, re.DOTALL)
        long_content = long_match.group(1).strip() if long_match else ""

        # 3. 结构化保存
        save_structured_foreshadowing(filepath, novel_number, short_content, long_content)

    except Exception as e:
        logging.error(f"伏笔分析失败: {e}")


# -----------------------------------------------------------------------------
# 4. 主入口：章节定稿 (依次调用)
# -----------------------------------------------------------------------------
def finalize_chapter(
    novel_number: int,
    word_number: int,
    api_key: str,
    base_url: str,
    model_name: str,
    temperature: float,
    filepath: str,
    embedding_api_key: str,
    embedding_url: str,
    embedding_interface_format: str,
    embedding_model_name: str,
    interface_format: str,
    max_tokens: int,
    timeout: int = 600
):
    """
    分步定稿：摘要 -> 角色 -> 伏笔 -> 向量库
    """
    # 1. 更新摘要
    update_global_summary(novel_number, filepath, api_key, base_url, model_name, interface_format, temperature, max_tokens, timeout)
    
    # 2. 更新角色
    update_character_state(novel_number, filepath, api_key, base_url, model_name, interface_format, temperature, max_tokens, timeout)
    
    # 3. [修改] 更新伏笔 (支持长短线分类)
    update_foreshadowing_records(novel_number, filepath, api_key, base_url, model_name, interface_format, temperature, max_tokens, timeout)

    # 4. 向量入库
    # 这里需要单独创建一个 embedding adapter
    ingest_chapter_to_vector_store(novel_number, filepath, embedding_api_key, embedding_url, embedding_interface_format, embedding_model_name)

    logging.info(f"Chapter {novel_number} finalization process completed.")


def ingest_chapter_to_vector_store(novel_number, filepath, api_key, base_url, interface_format, model_name):
    """
    辅助函数：向量入库
    """
    try:
        chapters_dir = os.path.join(filepath, "chapters")
        chapter_file = os.path.join(chapters_dir, f"chapter_{novel_number}.txt")
        if not os.path.exists(chapter_file):
            return
        chapter_text = read_file(chapter_file)
        
        logging.info(f"正在将第 {novel_number} 章存入向量库...")
        
        emb_adapter = create_embedding_adapter(interface_format, api_key, base_url, model_name)
        update_vector_store(emb_adapter, chapter_text, filepath)
        
        logging.info("向量库更新完成。")
    except Exception as e:
        logging.error(f"向量入库失败: {e}")


# -----------------------------------------------------------------------------
# 5. 扩写功能
# -----------------------------------------------------------------------------
def enrich_chapter_text(
    chapter_text: str,
    word_number: int,
    api_key: str,
    base_url: str,
    model_name: str,
    temperature: float,
    interface_format: str,
    max_tokens: int,
    timeout: int=600
) -> str:
    llm_adapter = create_llm_adapter(
        interface_format=interface_format,
        base_url=base_url,
        model_name=model_name,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout
    )
    prompt = f"""以下章节文本较短，请在保持剧情连贯的前提下进行扩写，使其更充实，接近 {word_number} 字左右，仅给出最终文本，不要解释任何内容。：
原内容：
{chapter_text}
"""
    enriched_text = invoke_with_cleaning(llm_adapter, prompt)
    return enriched_text if enriched_text else chapter_text