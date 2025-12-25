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
    """Call LLM for scoring"""
    try:
        llm = _make_llm()
        prompt = build_prompt(question_text, rubric, student_answer)
        resp = llm.invoke(prompt)
        text = resp.content.strip()
        
        try:
            result = json.loads(text)
            return result
        except Exception as parse_error:
            logger.warning(f"JSON parse failed, retrying: {parse_error}")
            resp2 = llm.invoke(prompt + "\nReturn JSON only.")
            result = json.loads(resp2.content.strip())
            return result
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        raise
