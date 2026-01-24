# utils.py
# -*- coding: utf-8 -*-
import os
import json
import re

def read_file(filename: str) -> str:
    """读取文件的全部内容，若文件不存在或异常则返回空字符串。"""
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            content = file.read()
        return content
    except FileNotFoundError:
        return ""
    except Exception as e:
        print(f"[read_file] 读取文件时发生错误: {e}")
        return ""

def append_text_to_file(text_to_append: str, file_path: str):
    """在文件末尾追加文本(带换行)。若文本非空且无换行，则自动加换行。"""
    if text_to_append and not text_to_append.startswith('\n'):
        text_to_append = '\n' + text_to_append

    try:
        with open(file_path, 'a', encoding='utf-8') as file:
            file.write(text_to_append)
    except IOError as e:
        print(f"[append_text_to_file] 发生错误：{e}")

def clear_file_content(filename: str):
    """清空指定文件内容。"""
    try:
        with open(filename, 'w', encoding='utf-8') as file:
            pass
    except IOError as e:
        print(f"[clear_file_content] 无法清空文件 '{filename}' 的内容：{e}")

def save_string_to_txt(content: str, filename: str):
    """将字符串保存为 txt 文件（覆盖写）。"""
    try:
        with open(filename, 'w', encoding='utf-8') as file:
            file.write(content)
    except Exception as e:
        print(f"[save_string_to_txt] 保存文件时发生错误: {e}")

def save_data_to_json(data: dict, file_path: str) -> bool:
    """将数据保存到 JSON 文件。"""
    try:
        with open(file_path, 'w', encoding='utf-8') as json_file:
            json.dump(data, json_file, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"[save_data_to_json] 保存数据到JSON文件时出错: {e}")
        return False

def extract_relevant_segments(full_text: str, query_keywords: str, window_size: int = 800, step: int = 200) -> str:
    """
    [V2.0 智能版] 基于关键词密度的滑窗截取算法
    优势：容忍语义差异。只要实体词（人名/物名）由于，就能精准定位，不再需要逐字匹配。
    """
    if not full_text or len(full_text) < window_size:
        return full_text

    # 1. 预处理搜索词
    # 将 "百草堂·内部陈设" 拆分为 ["百草堂", "内部", "陈设"]
    # 过滤掉单字，只保留有意义的双字以上词汇
    keywords = [k.strip() for k in re.split(r'[·\s\-_]+', query_keywords) if len(k.strip()) > 1]
    
    if not keywords:
        return full_text[:window_size]  # 降级：返回头部

    # 2. 滑动窗口扫描
    # 我们不求全匹配，只求“得分最高”的窗口
    max_score = -1
    best_window = full_text[:window_size]
    
    # 简单的打分函数：统计窗口内包含多少个关键词
    text_len = len(full_text)
    for start in range(0, text_len, step):
        end = min(start + window_size, text_len)
        window_text = full_text[start:end]
        
        score = 0
        for kw in keywords:
            # 模糊匹配逻辑：
            # 1. 如果关键词直接存在，+10分
            if kw in window_text:
                score += 10
            # 2. (可选) 如果关键词没找到，但它的子序列存在(针对长词)，+3分
            # 比如搜"爆裂火灵果"，原文是"火灵果"，也能加分
            elif len(kw) >= 3 and kw[1:] in window_text:
                score += 3
        
        # 记录最高分的窗口
        if score > max_score:
            max_score = score
            best_window = window_text
            
        # 优化：如果窗口得分极高（命中了一半以上关键词），直接提前返回，节省时间
        if score >= len(keywords) * 10 * 0.8:
            break

    # 3. 结果优化：前后加省略号
    return f"...{best_window}..."