# novel_generator/qa.py
# -*- coding: utf-8 -*-
import logging
import traceback
from llm_adapters import create_llm_adapter
from embedding_adapters import create_embedding_adapter
from novel_generator.common import invoke_with_cleaning
from novel_generator.vectorstore_utils import load_vector_store

# 问答专用提示词
QA_PROMPT_TEMPLATE = """\
你是一名熟悉这部小说的助手。请严格根据下方的【相关原文片段】来回答用户的提问。

【相关原文片段】：
{context}

【用户提问】：
{question}

【回答要求】：
1. 答案必须基于原文片段。如果原文片段中没有相关信息，请直接回答“根据现有章节内容，暂时无法找到相关信息”。
2. 语言通顺，逻辑清晰。
3. 不要编造原文中不存在的情节。

请回答：
"""

def answer_novel_question(
    filepath: str,
    question: str,
    # LLM 配置
    llm_api_key: str, llm_base_url: str, llm_model_name: str, interface_format: str,
    # Embedding 配置 (用于检索)
    emb_api_key: str, emb_base_url: str, emb_model_name: str, emb_interface_format: str,
    top_k: int = 5
) -> str:
    """
    全书问答核心逻辑
    """
    # 1. 加载向量库
    try:
        embedding_adapter = create_embedding_adapter(
            emb_interface_format, emb_api_key, emb_base_url, emb_model_name
        )
        
        # === 【核心修复】参数顺序对调：先传 Adapter，再传路径 ===
        vector_store = load_vector_store(embedding_adapter, filepath)
        
        if not vector_store:
            return "错误：无法加载向量库。请确保您已经对至少一个章节进行了【定稿 (Finalize)】操作，且向量库文件存在。"
            
    except Exception as e:
        logging.error(f"加载向量库失败: {traceback.format_exc()}")
        return f"加载知识库失败: {str(e)}"

    # 2. 检索相关内容 (Search)
    try:
        # 搜索最相关的 K 个片段
        docs = vector_store.similarity_search(question, k=top_k)
        if not docs:
            return "未在知识库中检索到相关内容。"
            
        # 拼接上下文
        context_text = "\n\n".join([f"---片段---\n{d.page_content}" for d in docs])
        
    except Exception as e:
        logging.error(f"检索失败: {traceback.format_exc()}")
        return f"检索失败: {str(e)}"

    # 3. 调用大模型回答 (Generation)
    try:
        llm_adapter = create_llm_adapter(
            interface_format=interface_format,
            base_url=llm_base_url,
            model_name=llm_model_name,
            api_key=llm_api_key,
            temperature=0.3, # 问答需要准确，温度调低
            max_tokens=2048,
            timeout=600
        )
        
        prompt = QA_PROMPT_TEMPLATE.format(
            context=context_text,
            question=question
        )
        
        response = invoke_with_cleaning(llm_adapter, prompt)
        return response

    except Exception as e:
        logging.error(f"生成答案失败: {traceback.format_exc()}")
        return f"生成答案失败: {str(e)}"