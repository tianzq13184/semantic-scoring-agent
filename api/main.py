import os
import logging
import time
from fastapi import FastAPI, HTTPException, Query, Depends
from dotenv import load_dotenv
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import desc
from typing import Optional, List

logger = logging.getLogger(__name__)
from .models import (
    EvaluationRequest, EvaluationResult, LLMScorePayload,
    ReviewSaveRequest, ReviewSaveResponse,
    EvaluationListResponse, EvaluationListItem, EvaluationDetail,
    QuestionCreate, QuestionUpdate, QuestionItem, QuestionDetail, QuestionListResponse,
    RubricCreate, RubricUpdate, RubricItem, RubricDetail, RubricListResponse, RubricActivateResponse,
    UserCreate, UserItem
)
from .rubric_service import get_rubric
from .llm_client import call_llm
from .db import init_db, SessionLocal, AnswerEvaluation, Question, QuestionRubric, User
from .auth import require_teacher, require_student, require_any, get_current_user, UserRole

load_dotenv()
app = FastAPI(title="Answer Evaluation API")

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
    if os.getenv("AUTO_MIGRATE", "false").lower() == "true":
        from .migrations import run_migrations
        run_migrations()

def _get_question(question_id: str) -> dict:
    """Get question information from database"""
    sess = SessionLocal()
    try:
        question = sess.query(Question).filter(Question.question_id == question_id).first()
        if not question:
            return None
        return {
            "text": question.text,
            "topic": question.topic
        }
    except Exception as e:
        logger.error(f"Query failed: question_id={question_id}, error={e}", exc_info=True)
        raise
    finally:
        sess.close()

@app.post("/evaluate/short-answer", response_model=EvaluationResult)
def evaluate(req: EvaluationRequest, current_user: dict = Depends(require_any)):
    """
    Evaluate student answer (student answering question)
    - Students: can answer questions, system automatically records student_id
    - Teachers: can also use this endpoint (for testing or answering on behalf)
    """
    q = _get_question(req.question_id)
    if not q:
        raise HTTPException(404, "question_id not found")
    
    rubric, rubric_version = get_rubric(
        req.question_id, 
        q["topic"], 
        req.rubric_json,
        question_text=q["text"]
    )
    
    try:
        llm_json = call_llm(q["text"], rubric, req.student_answer)
    except Exception as exc:
        logger.error(f"LLM call failed: {exc}")
        raise HTTPException(status_code=502, detail=f"LLM call failed: {exc}") from exc

    try:
        llm_payload = LLMScorePayload(**llm_json)
    except ValidationError as exc:
        logger.error(f"LLM response validation failed: {exc.errors()}")
        raise HTTPException(status_code=502, detail=f"LLM returned invalid payload: {exc.errors()}") from exc

    provider, model_id, model_version = _model_metadata()

    result = EvaluationResult(
        question_id=req.question_id,
        rubric_version=rubric_version,
        provider=provider,
        model_id=model_id,
        model_version=model_version,
        raw_llm_output=llm_json,
        **llm_payload.model_dump()
    )

    sess = SessionLocal()
    try:
        student_id = current_user["id"] if current_user["role"] == "student" else None
        
        ae = AnswerEvaluation(
            question_id=req.question_id,
            student_id=student_id,
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


@app.post("/review/save", response_model=ReviewSaveResponse)
def save_review(req: ReviewSaveRequest, current_user: dict = Depends(require_teacher)):
    """
    Review assignment (manual scoring based on AI answer)
    - Teachers: can override AI score, enter final score and comments
    """
    sess = SessionLocal()
    try:
        evaluation = sess.query(AnswerEvaluation).filter(
            AnswerEvaluation.id == req.evaluation_id
        ).first()
        
        if not evaluation:
            raise HTTPException(404, f"Evaluation {req.evaluation_id} not found")
        
        evaluation.final_score = req.final_score
        evaluation.reviewer_id = current_user["id"]
        evaluation.review_notes = req.review_notes
        
        sess.commit()
        
        return ReviewSaveResponse(
            success=True,
            message="Review saved successfully",
            evaluation_id=evaluation.id,
            auto_score=evaluation.auto_score,
            final_score=evaluation.final_score
        )
    except HTTPException:
        raise
    except Exception as exc:
        sess.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save review: {exc}") from exc
    finally:
        sess.close()


@app.get("/evaluations", response_model=EvaluationListResponse)
def list_evaluations(
    question_id: Optional[str] = Query(None, description="Filter by question ID"),
    student_id: Optional[str] = Query(None, description="Filter by student ID"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: dict = Depends(require_any)
):
    """
    Browse evaluation list (auto-generated/teacher reviewed)
    - Students: can only view their own evaluation results
    - Teachers: can view all students' evaluation results
    """
    sess = SessionLocal()
    try:
        query = sess.query(AnswerEvaluation)
        
        if current_user["role"] == "student":
            query = query.filter(AnswerEvaluation.student_id == current_user["id"])
        
        if question_id:
            query = query.filter(AnswerEvaluation.question_id == question_id)
        if student_id:
            if current_user["role"] == "teacher":
                query = query.filter(AnswerEvaluation.student_id == student_id)
        
        total = query.count()
        items = query.order_by(desc(AnswerEvaluation.created_at)).offset(offset).limit(limit).all()
        evaluation_items = [
            EvaluationListItem(
                id=item.id,
                question_id=item.question_id,
                student_id=item.student_id,
                auto_score=item.auto_score,
                final_score=item.final_score,
                created_at=item.created_at,
                updated_at=item.updated_at,
                reviewer_id=item.reviewer_id
            )
            for item in items
        ]
        
        return EvaluationListResponse(
            total=total,
            items=evaluation_items
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to query evaluations: {exc}") from exc
    finally:
        sess.close()


@app.get("/evaluations/{evaluation_id}", response_model=EvaluationDetail)
def get_evaluation_detail(evaluation_id: int, current_user: dict = Depends(require_any)):
    """
    Browse final result (view evaluation details)
    - Students: can only view their own evaluation details (including AI score and teacher review)
    - Teachers: can view all students' evaluation details
    """
    sess = SessionLocal()
    try:
        evaluation = sess.query(AnswerEvaluation).filter(
            AnswerEvaluation.id == evaluation_id
        ).first()
        
        if not evaluation:
            raise HTTPException(404, f"Evaluation {evaluation_id} not found")
        
        if current_user["role"] == "student":
            if evaluation.student_id != current_user["id"]:
                raise HTTPException(403, "No permission to access this evaluation result")
        
        return EvaluationDetail(
            id=evaluation.id,
            question_id=evaluation.question_id,
            student_id=evaluation.student_id,
            student_answer=evaluation.student_answer,
            auto_score=evaluation.auto_score,
            final_score=evaluation.final_score,
            dimension_scores_json=evaluation.dimension_scores_json,
            model_version=evaluation.model_version,
            rubric_version=evaluation.rubric_version,
            review_notes=evaluation.review_notes,
            reviewer_id=evaluation.reviewer_id,
            raw_llm_output=evaluation.raw_llm_output,
            created_at=evaluation.created_at,
            updated_at=evaluation.updated_at
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to get evaluation: {exc}") from exc
    finally:
        sess.close()


# ==================== Question Management Endpoints ====================

@app.get("/questions", response_model=QuestionListResponse)
def list_questions(
    topic: Optional[str] = Query(None, description="Filter by topic"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: dict = Depends(require_any)
):
    """
    Query question list
    - Students: can view question list (for selecting questions to answer)
    - Teachers: can view question list (for management)
    """
    sess = SessionLocal()
    try:
        query = sess.query(Question)
        
        # Apply filter conditions
        if topic:
            query = query.filter(Question.topic == topic)
        
        # Get total count
        total = query.count()
        
        # Sort and paginate
        items = query.order_by(Question.created_at.desc()).offset(offset).limit(limit).all()
        
        # Convert to response model
        question_items = [
            QuestionItem(
                id=q.id,
                question_id=q.question_id,
                text=q.text,
                topic=q.topic,
                created_at=q.created_at,
                updated_at=q.updated_at
            )
            for q in items
        ]
        
        return QuestionListResponse(
            total=total,
            items=question_items
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to query questions: {exc}") from exc
    finally:
        sess.close()


@app.get("/questions/{question_id}", response_model=QuestionDetail)
def get_question(question_id: str, current_user: dict = Depends(require_any)):
    """
    Get question details
    - Students: can view question details (for answering)
    - Teachers: can view question details (for management)
    """
    sess = SessionLocal()
    try:
        question = sess.query(Question).filter(Question.question_id == question_id).first()
        
        if not question:
            raise HTTPException(404, f"Question {question_id} not found")
        
        rubrics_count = sess.query(QuestionRubric).filter(
            QuestionRubric.question_id == question_id
        ).count()
        
        evaluations_count = sess.query(AnswerEvaluation).filter(
            AnswerEvaluation.question_id == question_id
        ).count()
        
        return QuestionDetail(
            id=question.id,
            question_id=question.question_id,
            text=question.text,
            topic=question.topic,
            created_at=question.created_at,
            updated_at=question.updated_at,
            rubrics_count=rubrics_count,
            evaluations_count=evaluations_count
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to get question: {exc}") from exc
    finally:
        sess.close()


@app.post("/questions", response_model=QuestionItem, status_code=201)
def create_question(req: QuestionCreate, current_user: dict = Depends(require_teacher)):
    """
    Create question (Teacher)
    - Teachers: can create new questions
    """
    sess = SessionLocal()
    try:
        existing = sess.query(Question).filter(Question.question_id == req.question_id).first()
        if existing:
            raise HTTPException(400, f"Question {req.question_id} already exists")
        question = Question(
            question_id=req.question_id,
            text=req.text,
            topic=req.topic
        )
        sess.add(question)
        sess.commit()
        sess.refresh(question)
        
        return QuestionItem(
            id=question.id,
            question_id=question.question_id,
            text=question.text,
            topic=question.topic,
            created_at=question.created_at,
            updated_at=question.updated_at
        )
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        sess.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create question: {exc}") from exc
    finally:
        sess.close()


@app.put("/questions/{question_id}", response_model=QuestionItem)
def update_question(question_id: str, req: QuestionUpdate, current_user: dict = Depends(require_teacher)):
    """
    Update question (Teacher)
    - Teachers: can update questions
    """
    sess = SessionLocal()
    try:
        question = sess.query(Question).filter(Question.question_id == question_id).first()
        
        if not question:
            raise HTTPException(404, f"Question {question_id} not found")
        
        # Update fields
        if req.text is not None:
            question.text = req.text
        if req.topic is not None:
            question.topic = req.topic
        
        sess.commit()
        sess.refresh(question)
        
        return QuestionItem(
            id=question.id,
            question_id=question.question_id,
            text=question.text,
            topic=question.topic,
            created_at=question.created_at,
            updated_at=question.updated_at
        )
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        sess.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update question: {exc}") from exc
    finally:
        sess.close()


@app.delete("/questions/{question_id}", status_code=204)
def delete_question(question_id: str, current_user: dict = Depends(require_teacher)):
    """
    Delete question (Teacher)
    - Teachers: can delete questions
    """
    """
    Delete question
    Only teachers can use this
    """
    sess = SessionLocal()
    try:
        question = sess.query(Question).filter(Question.question_id == question_id).first()
        
        if not question:
            raise HTTPException(404, f"Question {question_id} not found")
        
        sess.delete(question)
        sess.commit()
        
        return None
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        sess.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete question: {exc}") from exc
    finally:
        sess.close()


# ==================== Rubric Management Endpoints ====================

@app.get("/questions/{question_id}/rubrics", response_model=RubricListResponse)
def list_rubrics(question_id: str, current_user: dict = Depends(require_any)):
    """
    Query rubric list for a question
    Both students and teachers can view (to understand scoring criteria)
    """
    sess = SessionLocal()
    try:
        question = sess.query(Question).filter(Question.question_id == question_id).first()
        if not question:
            raise HTTPException(404, f"Question {question_id} not found")
        rubrics = sess.query(QuestionRubric).filter(
            QuestionRubric.question_id == question_id
        ).order_by(QuestionRubric.created_at.desc()).all()
        
        rubric_items = [
            RubricItem(
                id=r.id,
                question_id=r.question_id,
                version=r.version,
                is_active=r.is_active,
                created_by=r.created_by,
                created_at=r.created_at
            )
            for r in rubrics
        ]
        
        return RubricListResponse(
            total=len(rubric_items),
            items=rubric_items
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to query rubrics: {exc}") from exc
    finally:
        sess.close()


@app.post("/questions/{question_id}/rubrics", response_model=RubricDetail, status_code=201)
def create_rubric(question_id: str, req: RubricCreate, current_user: dict = Depends(require_teacher)):
    """
    Create rubric (Teacher)
    - Teachers: can create rubrics for questions
    """
    sess = SessionLocal()
    try:
        question = sess.query(Question).filter(Question.question_id == question_id).first()
        if not question:
            raise HTTPException(404, f"Question {question_id} not found")
        
        existing = sess.query(QuestionRubric).filter(
            QuestionRubric.question_id == question_id,
            QuestionRubric.version == req.version
        ).first()
        if existing:
            raise HTTPException(400, f"Rubric version {req.version} already exists for question {question_id}")
        
        if req.is_active:
            sess.query(QuestionRubric).filter(
                QuestionRubric.question_id == question_id,
                QuestionRubric.is_active == True
            ).update({"is_active": False})
        
        rubric = QuestionRubric(
            question_id=question_id,
            version=req.version,
            rubric_json=req.rubric_json,
            is_active=req.is_active,
            created_by=current_user["id"]
        )
        sess.add(rubric)
        sess.commit()
        sess.refresh(rubric)
        
        return RubricDetail(
            id=rubric.id,
            question_id=rubric.question_id,
            version=rubric.version,
            rubric_json=rubric.rubric_json,
            is_active=rubric.is_active,
            created_by=rubric.created_by,
            created_at=rubric.created_at
        )
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        sess.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create rubric: {exc}") from exc
    finally:
        sess.close()


@app.put("/rubrics/{rubric_id}", response_model=RubricDetail)
def update_rubric(rubric_id: int, req: RubricUpdate, current_user: dict = Depends(require_teacher)):
    """
    Update rubric (Teacher)
    - Teachers: can update rubrics
    """
    sess = SessionLocal()
    try:
        rubric = sess.query(QuestionRubric).filter(QuestionRubric.id == rubric_id).first()
        
        if not rubric:
            raise HTTPException(404, f"Rubric {rubric_id} not found")
        
        if req.rubric_json is not None:
            rubric.rubric_json = req.rubric_json
        
        if req.is_active is not None:
            if req.is_active:
                sess.query(QuestionRubric).filter(
                    QuestionRubric.question_id == rubric.question_id,
                    QuestionRubric.id != rubric_id,
                    QuestionRubric.is_active == True
                ).update({"is_active": False})
            rubric.is_active = req.is_active
        
        sess.commit()
        sess.refresh(rubric)
        
        return RubricDetail(
            id=rubric.id,
            question_id=rubric.question_id,
            version=rubric.version,
            rubric_json=rubric.rubric_json,
            is_active=rubric.is_active,
            created_by=rubric.created_by,
            created_at=rubric.created_at
        )
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        sess.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update rubric: {exc}") from exc
    finally:
        sess.close()


@app.post("/rubrics/{rubric_id}/activate", response_model=RubricActivateResponse)
def activate_rubric(rubric_id: int, current_user: dict = Depends(require_teacher)):
    """
    Activate rubric (Teacher)
    - Teachers: can activate rubrics (while deactivating other active rubrics for the same question)
    """
    sess = SessionLocal()
    try:
        rubric = sess.query(QuestionRubric).filter(QuestionRubric.id == rubric_id).first()
        
        if not rubric:
            raise HTTPException(404, f"Rubric {rubric_id} not found")
        
        sess.query(QuestionRubric).filter(
            QuestionRubric.question_id == rubric.question_id,
            QuestionRubric.id != rubric_id,
            QuestionRubric.is_active == True
        ).update({"is_active": False})
        
        rubric.is_active = True
        sess.commit()
        
        return RubricActivateResponse(
            success=True,
            message=f"Rubric {rubric.version} activated successfully",
            rubric_id=rubric.id,
            question_id=rubric.question_id,
            version=rubric.version
        )
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        sess.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to activate rubric: {exc}") from exc
    finally:
        sess.close()


@app.get("/rubrics/{rubric_id}", response_model=RubricDetail)
def get_rubric_detail(rubric_id: int, current_user: dict = Depends(require_any)):
    """
    Get rubric details
    - Students: can view rubric details (to understand scoring criteria)
    - Teachers: can view rubric details (for management)
    """
    sess = SessionLocal()
    try:
        rubric = sess.query(QuestionRubric).filter(QuestionRubric.id == rubric_id).first()
        
        if not rubric:
            raise HTTPException(404, f"Rubric {rubric_id} not found")
        
        return RubricDetail(
            id=rubric.id,
            question_id=rubric.question_id,
            version=rubric.version,
            rubric_json=rubric.rubric_json,
            is_active=rubric.is_active,
            created_by=rubric.created_by,
            created_at=rubric.created_at
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to get rubric: {exc}") from exc
    finally:
        sess.close()


# User Management Endpoints
@app.post("/users", response_model=UserItem, status_code=201)
def create_user(req: UserCreate, current_user: dict = Depends(require_teacher)):
    """Create user (Teachers only)"""
    sess = SessionLocal()
    try:
        existing = sess.query(User).filter(User.id == req.id).first()
        if existing:
            raise HTTPException(400, f"User {req.id} already exists")
        if req.role not in ["student", "teacher"]:
            raise HTTPException(400, "Role must be 'student' or 'teacher'")
        user = User(id=req.id, username=req.username, role=req.role)
        sess.add(user)
        sess.commit()
        sess.refresh(user)
        return UserItem(id=user.id, username=user.username, role=user.role, created_at=user.created_at)
    except HTTPException:
        raise
    except Exception as exc:
        sess.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create user: {exc}") from exc
    finally:
        sess.close()

@app.get("/users", response_model=List[UserItem])
def list_users(current_user: dict = Depends(require_teacher)):
    """Get user list (Teachers only)"""
    sess = SessionLocal()
    try:
        users = sess.query(User).order_by(User.created_at.desc()).all()
        return [UserItem(id=u.id, username=u.username, role=u.role, created_at=u.created_at) for u in users]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to list users: {exc}") from exc
    finally:
        sess.close()

@app.get("/users/{user_id}", response_model=UserItem)
def get_user(user_id: str, current_user: dict = Depends(require_teacher)):
    """Get user details (Teachers only)"""
    sess = SessionLocal()
    try:
        user = sess.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(404, f"User {user_id} not found")
        return UserItem(id=user.id, username=user.username, role=user.role, created_at=user.created_at)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to get user: {exc}") from exc
    finally:
        sess.close()
