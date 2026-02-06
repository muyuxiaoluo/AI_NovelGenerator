#novel_generator/common.py
# -*- coding: utf-8 -*-
"""
通用重试、清洗、日志工具
"""
import logging
import re
import time
import traceback
logging.basicConfig(
    filename='app.log',      # 日志文件名
    filemode='a',            # 追加模式（'w' 会覆盖）
    level=logging.INFO,      # 记录 INFO 及以上级别的日志
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
def call_with_retry(func, max_retries=3, sleep_time=2, fallback_return=None, **kwargs):
    """
    通用的重试机制封装。
    :param func: 要执行的函数
    :param max_retries: 最大重试次数
    :param sleep_time: 重试前的等待秒数
    :param fallback_return: 如果多次重试仍失败时的返回值
    :param kwargs: 传给func的命名参数
    :return: func的结果，若失败则返回 fallback_return
    """
    for attempt in range(1, max_retries + 1):
        try:
            return func(**kwargs)
        except Exception as e:
            error_str = str(e)
            logging.warning(f"[call_with_retry] Attempt {attempt} failed with error: {e}")
            traceback.print_exc()
            
            if attempt < max_retries:
                if "500" in error_str or "Internal Server Error" in error_str:
                    wait_time = sleep_time * 2
                    logging.info(f"Server error detected, waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                else:
                    time.sleep(sleep_time)
            else:
                logging.error("Max retries reached, returning fallback_return.")
                return fallback_return

def remove_think_tags(text: str) -> str:
    """移除 <think>...</think> 包裹的内容"""
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)

def debug_log(prompt: str, response_content: str):
    logging.info(
        f"\n[#########################################  Prompt  #########################################]\n{prompt}\n"
    )
    logging.info(
        f"\n[######################################### Response #########################################]\n{response_content}\n"
    )

def _is_connection_error(exc: Exception) -> bool:
    """判断是否为网络/SSL 连接类错误，这类错误适合重试"""
    err_str = str(exc).lower()
    err_type = type(exc).__name__
    connection_indicators = [
        "ssl", "connection", "connect", "eof", "protocol",
        "timeout", "unreachable", "refused", "proxy"
    ]
    return (
        "connection" in err_type.lower()
        or "ssl" in err_str
        or "connect" in err_str
        or "eof" in err_str
        or any(ind in err_str for ind in connection_indicators)
    )


def invoke_with_cleaning(llm_adapter, prompt: str, max_retries: int = 3) -> str:
    """调用 LLM 并清理返回结果，对网络/SSL 错误进行指数退避重试"""
    print("\n" + "="*50)
    print("发送到 LLM 的提示词:")
    print("-"*50)
    print(prompt)
    print("="*50 + "\n")

    result = ""
    retry_count = 0
    # 网络/SSL 错误时增加重试次数和等待
    effective_retries = max_retries

    while retry_count < effective_retries:
        try:
            result = llm_adapter.invoke(prompt)
            print("\n" + "="*50)
            print("LLM 返回的内容:")
            print("-"*50)
            print(result)
            print("="*50 + "\n")

            result = result.replace("```", "").strip()
            if result:
                return result
            retry_count += 1
        except Exception as e:
            is_conn = _is_connection_error(e)
            if is_conn:
                effective_retries = max(5, max_retries + 2)  # 连接错误多试几次
                wait = min(60, 3 * (2 ** retry_count))  # 指数退避：3, 6, 12, 24, 48 秒
                print(f"网络/SSL 连接失败 ({retry_count + 1}/{effective_retries})，{wait} 秒后重试...")
                if retry_count + 1 < effective_retries:
                    time.sleep(wait)
            else:
                print(f"调用失败 ({retry_count + 1}/{effective_retries}): {str(e)}")

            retry_count += 1
            if retry_count >= effective_retries:
                if is_conn:
                    raise ConnectionError(
                        f"多次连接失败: {e}\n\n"
                        "可能原因：代理/防火墙、SSL 证书、网络不稳定。\n"
                        "建议：检查代理设置、关闭 VPN 后重试，或稍后再试。"
                    ) from e
                raise e

    return result

