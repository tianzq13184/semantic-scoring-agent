import os, json
import logging
import time
from typing import Dict, Any, Optional
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

def _get_env(*names: str, default: Optional[str] = None) -> Optional[str]:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return default

def _build_headers_for_openrouter() -> dict:
    headers = {}
    referer = _get_env("OPENROUTER_REFERER", "OR_HTTP_REFERER")
    if referer:
        headers["HTTP-Referer"] = referer
    title = _get_env("OPENROUTER_TITLE", "OR_X_TITLE")
    if title:
        headers["X-Title"] = title
    return headers

def _detect_provider() -> str:
    provider = os.getenv("LLM_PROVIDER")
    if provider:
        return provider.lower()
    base_url = os.getenv("OPENAI_BASE_URL", "")
    if "openrouter" in base_url.lower():
        return "openrouter"
    return "openai"

def _make_llm():
    provider = _detect_provider()
    model = _get_env("MODEL_ID", "MODEL_NAME", default="gpt-4o-mini")
    api_key = _get_env("OPENAI_API_KEY", "OPENROUTER_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")

    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY; please configure your LLM credentials.")

    common_kwargs = dict(model=model, api_key=api_key, temperature=0, max_retries=2)

    if provider == "openrouter":
        return ChatOpenAI(
            base_url=base_url or "https://openrouter.ai/api/v1",
            default_headers=_build_headers_for_openrouter(),
            **common_kwargs,
        )

    if base_url:
        common_kwargs["base_url"] = base_url
    return ChatOpenAI(**common_kwargs)

def build_prompt(question_text:str, rubric:dict, student_answer:str) -> str:
    return f"""You are an experienced data interview evaluator.
Score on multiple dimensions in one pass and OUTPUT JSON ONLY.

QUESTION
{question_text}

RUBRIC
{json.dumps(rubric, ensure_ascii=False)}

CANDIDATE ANSWER
{student_answer}

OUTPUT FORMAT (JSON):
{{
  "total_score": float (0-10),
  "dimension_breakdown": {{
    "accuracy": float (0-2),
    "structure": float (0-2),
    "clarity": float (0-2),
    "business": float (0-2),
    "language": float (0-2)
  }},
  "key_points_evaluation": ["point -> ok/missing/..."],
  "improvement_recommendations": ["concrete action 1", "concrete action 2"]
}}
Only return valid JSON, no extra text.
"""

def call_llm(question_text:str, rubric:dict, student_answer:str) -> Dict[str, Any]:
    """
    调用 LLM 进行评分
    
    注意：如果看到此函数的日志，说明 mock 可能没有生效！
    """
    logger.warning("[call_llm] ⚠️ LLM调用开始 - 如果这是测试，说明mock可能失效！")
    call_start = time.time()
    
    try:
        logger.debug("[call_llm] 步骤1: 创建LLM实例")
        llm_start = time.time()
        llm = _make_llm()
        logger.debug(f"[call_llm] LLM实例创建完成, 耗时={time.time()-llm_start:.3f}s")
        
        logger.debug("[call_llm] 步骤2: 构建prompt")
        prompt = build_prompt(question_text, rubric, student_answer)
        logger.debug(f"[call_llm] Prompt构建完成, 长度={len(prompt)}")
        
        logger.debug("[call_llm] 步骤3: 调用LLM invoke")
        invoke_start = time.time()
        resp = llm.invoke(prompt)
        invoke_time = time.time() - invoke_start
        logger.debug(f"[call_llm] LLM invoke完成, 耗时={invoke_time:.3f}s")
        
        text = resp.content.strip()
        logger.debug(f"[call_llm] 步骤4: 解析JSON响应, 响应长度={len(text)}")
        
        try:
            result = json.loads(text)
            logger.debug(f"[call_llm] JSON解析成功, total_score={result.get('total_score', 'N/A')}")
            logger.warning(f"[call_llm] ⚠️ LLM调用完成 - 总耗时={time.time()-call_start:.3f}s")
            return result
        except Exception as parse_error:
            logger.warning(f"[call_llm] 第一次JSON解析失败, 尝试重新调用: {parse_error}")
            resp2 = llm.invoke(prompt + "\nReturn JSON only.")
            result = json.loads(resp2.content.strip())
            logger.debug(f"[call_llm] 第二次JSON解析成功")
            logger.warning(f"[call_llm] ⚠️ LLM调用完成 - 总耗时={time.time()-call_start:.3f}s")
            return result
    except Exception as e:
        logger.error(f"[call_llm] LLM调用异常: {e}, 耗时={time.time()-call_start:.3f}s")
        raise
