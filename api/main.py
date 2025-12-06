import os
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from .models import EvaluationRequest, EvaluationResult, LLMScorePayload
from .rubric_service import get_rubric
from .llm_client import call_llm
from .db import init_db, SessionLocal, AnswerEvaluation

load_dotenv()
app = FastAPI(title="Answer Evaluation API")

QUESTION_BANK = {
    "Q2105": {"text": "简述如何在 Airflow 中实现可靠的依赖管理与失败恢复。", "topic":"airflow"}
}

def _model_metadata():
    provider = os.getenv("LLM_PROVIDER")
    if not provider:
        base_url = os.getenv("OPENAI_BASE_URL", "")
        provider = "openrouter" if "openrouter" in base_url.lower() else "openai"
    model_id = os.getenv("MODEL_ID") or os.getenv("MODEL_NAME", "gpt-4o-mini")
    model_version = os.getenv("MODEL_VERSION") or f"{provider}:{model_id}"
    return provider, model_id, model_version

@app.on_event("startup")
def on_startup():
    init_db()

@app.post("/evaluate/short-answer", response_model=EvaluationResult)
def evaluate(req: EvaluationRequest):
    q = QUESTION_BANK.get(req.question_id)
    if not q:
        raise HTTPException(404, "question_id not found")
    rubric, rubric_version = get_rubric(req.question_id, q["topic"], req.rubric_json)
    try:
        llm_json = call_llm(q["text"], rubric, req.student_answer)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM call failed: {exc}") from exc

    try:
        llm_payload = LLMScorePayload(**llm_json)
    except ValidationError as exc:
        raise HTTPException(status_code=502, detail=f"LLM returned invalid payload: {exc.errors()}") from exc

    provider, model_id, model_version = _model_metadata()

    # 组装结果
    result = EvaluationResult(
        question_id=req.question_id,
        rubric_version=rubric_version,
        provider=provider,
        model_id=model_id,
        model_version=model_version,
        raw_llm_output=llm_json,
        **llm_payload.model_dump()
    )

    # 落库
    sess = SessionLocal()
    try:
        ae = AnswerEvaluation(
            question_id=req.question_id,
            student_answer=req.student_answer,
            auto_score=result.total_score,
            final_score=None,
            dimension_scores_json=result.dimension_breakdown,
            model_version=result.model_version,
            rubric_version=result.rubric_version,
            raw_llm_output=result.raw_llm_output
        )
        sess.add(ae)
        sess.commit()
    except SQLAlchemyError as exc:
        sess.rollback()
        raise HTTPException(status_code=500, detail="Failed to persist evaluation result") from exc
    finally:
        sess.close()

    return result
