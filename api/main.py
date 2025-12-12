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
    # 可选：自动运行迁移（仅在开发环境）
    # 生产环境建议手动运行迁移脚本
    if os.getenv("AUTO_MIGRATE", "false").lower() == "true":
        from .migrations import run_migrations
        run_migrations()

def _get_question(question_id: str) -> dict:
    """从数据库获取题目信息"""
    logger.debug(f"[_get_question] 开始查询题目: question_id={question_id}")
    start_time = time.time()
    logger.debug(f"[_get_question] 创建SessionLocal: {SessionLocal}")
    sess = SessionLocal()
    logger.debug(f"[_get_question] Session创建完成, bind={sess.bind}")
    try:
        logger.debug(f"[_get_question] 开始执行查询")
        question = sess.query(Question).filter(Question.question_id == question_id).first()
        elapsed = time.time() - start_time
        logger.debug(f"[_get_question] 查询执行完成, 耗时={elapsed:.3f}s")
        if not question:
            logger.debug(f"[_get_question] 题目不存在: question_id={question_id}, 耗时={elapsed:.3f}s")
            return None
        logger.debug(f"[_get_question] 查询成功: question_id={question_id}, topic={question.topic}, 耗时={elapsed:.3f}s")
        return {
            "text": question.text,
            "topic": question.topic
        }
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"[_get_question] 查询失败: question_id={question_id}, 错误={e}, 耗时={elapsed:.3f}s", exc_info=True)
        raise
    finally:
        sess.close()

@app.post("/evaluate/short-answer", response_model=EvaluationResult)
def evaluate(req: EvaluationRequest, current_user: dict = Depends(require_any)):
    """
    评估学生答案（学生作答题目）
    - 学生：可以作答题目，系统自动记录 student_id
    - 老师：也可以使用此接口（用于测试或代答）
    """
    request_start = time.time()
    logger.info(f"[evaluate] 请求开始: question_id={req.question_id}, user_id={current_user.get('id')}, role={current_user.get('role')}")
    
    # 步骤1: 获取题目
    logger.debug(f"[evaluate] 步骤1: 开始获取题目信息")
    q = _get_question(req.question_id)
    if not q:
        logger.warning(f"[evaluate] 题目不存在: question_id={req.question_id}")
        raise HTTPException(404, "question_id not found")
    logger.debug(f"[evaluate] 步骤1完成: 题目信息获取成功, topic={q.get('topic')}")
    
    # 步骤2: 获取评分标准
    logger.debug(f"[evaluate] 步骤2: 开始获取评分标准")
    rubric_start = time.time()
    rubric, rubric_version = get_rubric(
        req.question_id, 
        q["topic"], 
        req.rubric_json,
        question_text=q["text"]
    )
    logger.debug(f"[evaluate] 步骤2完成: 评分标准获取成功, version={rubric_version}, 耗时={time.time()-rubric_start:.3f}s")
    
    # 步骤3: 调用 LLM
    logger.debug(f"[evaluate] 步骤3: 开始调用 LLM (如果看到此日志但后续没有LLM日志，说明mock生效)")
    llm_start = time.time()
    try:
        llm_json = call_llm(q["text"], rubric, req.student_answer)
        logger.debug(f"[evaluate] 步骤3完成: LLM调用成功, 耗时={time.time()-llm_start:.3f}s")
    except Exception as exc:
        logger.error(f"[evaluate] 步骤3失败: LLM调用异常, 错误={exc}, 耗时={time.time()-llm_start:.3f}s")
        raise HTTPException(status_code=502, detail=f"LLM call failed: {exc}") from exc

    # 步骤4: 验证 LLM 响应
    logger.debug(f"[evaluate] 步骤4: 开始验证LLM响应")
    try:
        llm_payload = LLMScorePayload(**llm_json)
        logger.debug(f"[evaluate] 步骤4完成: LLM响应验证成功, total_score={llm_payload.total_score}")
    except ValidationError as exc:
        logger.error(f"[evaluate] 步骤4失败: LLM响应验证失败, 错误={exc.errors()}")
        raise HTTPException(status_code=502, detail=f"LLM returned invalid payload: {exc.errors()}") from exc

    provider, model_id, model_version = _model_metadata()

    # 步骤5: 组装结果
    logger.debug(f"[evaluate] 步骤5: 开始组装结果")
    result = EvaluationResult(
        question_id=req.question_id,
        rubric_version=rubric_version,
        provider=provider,
        model_id=model_id,
        model_version=model_version,
        raw_llm_output=llm_json,
        **llm_payload.model_dump()
    )
    logger.debug(f"[evaluate] 步骤5完成: 结果组装成功")

    # 步骤6: 保存到数据库
    logger.debug(f"[evaluate] 步骤6: 开始保存到数据库")
    db_start = time.time()
    sess = SessionLocal()
    try:
        # 如果是学生，记录 student_id；如果是老师，student_id 为 None（老师可以代答）
        student_id = current_user["id"] if current_user["role"] == "student" else None
        logger.debug(f"[evaluate] 准备保存评估结果: student_id={student_id}")
        
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
        logger.debug(f"[evaluate] 步骤6完成: 数据库保存成功, evaluation_id={ae.id}, 耗时={time.time()-db_start:.3f}s")
    except SQLAlchemyError as exc:
        logger.error(f"[evaluate] 步骤6失败: 数据库保存异常, 错误={exc}, 耗时={time.time()-db_start:.3f}s")
        sess.rollback()
        raise HTTPException(status_code=500, detail="Failed to persist evaluation result") from exc
    finally:
        sess.close()

    total_time = time.time() - request_start
    logger.info(f"[evaluate] 请求完成: question_id={req.question_id}, total_score={result.total_score}, 总耗时={total_time:.3f}s")
    return result


@app.post("/review/save", response_model=ReviewSaveResponse)
def save_review(req: ReviewSaveRequest, current_user: dict = Depends(require_teacher)):
    """
    批改作业（在AI答案的基础上进行人工评分）
    - 教师：可以覆盖AI评分，录入最终分数和评语
    """
    sess = SessionLocal()
    try:
        # 查找评估记录
        evaluation = sess.query(AnswerEvaluation).filter(
            AnswerEvaluation.id == req.evaluation_id
        ).first()
        
        if not evaluation:
            raise HTTPException(404, f"Evaluation {req.evaluation_id} not found")
        
        # 更新评分，使用当前登录的老师ID
        evaluation.final_score = req.final_score
        evaluation.reviewer_id = current_user["id"]  # 使用当前登录用户ID
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
    浏览评价列表（自动生成/老师批改）
    - 学生：只能查看自己的评价结果
    - 教师：可以查看所有学生的评价结果
    """
    sess = SessionLocal()
    try:
        query = sess.query(AnswerEvaluation)
        
        # 权限控制：学生只能查看自己的结果
        if current_user["role"] == "student":
            query = query.filter(AnswerEvaluation.student_id == current_user["id"])
        # 老师可以查看所有结果，但如果指定了 student_id，则按指定筛选
        
        # 应用筛选条件
        if question_id:
            query = query.filter(AnswerEvaluation.question_id == question_id)
        if student_id:
            # 老师可以按 student_id 筛选，学生只能看自己的（已在上面处理）
            if current_user["role"] == "teacher":
                query = query.filter(AnswerEvaluation.student_id == student_id)
        
        # 获取总数
        total = query.count()
        
        # 排序和分页
        items = query.order_by(desc(AnswerEvaluation.created_at)).offset(offset).limit(limit).all()
        
        # 转换为响应模型
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
    浏览最终结果（查看评价详情）
    - 学生：只能查看自己的评价详情（包括AI评分和教师批改）
    - 教师：可以查看所有学生的评价详情
    """
    sess = SessionLocal()
    try:
        evaluation = sess.query(AnswerEvaluation).filter(
            AnswerEvaluation.id == evaluation_id
        ).first()
        
        if not evaluation:
            raise HTTPException(404, f"Evaluation {evaluation_id} not found")
        
        # 权限控制：学生只能查看自己的结果
        if current_user["role"] == "student":
            if evaluation.student_id != current_user["id"]:
                raise HTTPException(403, "无权访问此评估结果")
        
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


# ==================== 题目管理接口 ====================

@app.get("/questions", response_model=QuestionListResponse)
def list_questions(
    topic: Optional[str] = Query(None, description="Filter by topic"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: dict = Depends(require_any)
):
    """
    查询题目列表
    - 学生：可以查看题目列表（用于选择题目作答）
    - 教师：可以查看题目列表（用于管理）
    """
    sess = SessionLocal()
    try:
        query = sess.query(Question)
        
        # 应用筛选条件
        if topic:
            query = query.filter(Question.topic == topic)
        
        # 获取总数
        total = query.count()
        
        # 排序和分页
        items = query.order_by(Question.created_at.desc()).offset(offset).limit(limit).all()
        
        # 转换为响应模型
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
    获取题目详情
    - 学生：可以查看题目详情（用于作答）
    - 教师：可以查看题目详情（用于管理）
    """
    sess = SessionLocal()
    try:
        question = sess.query(Question).filter(Question.question_id == question_id).first()
        
        if not question:
            raise HTTPException(404, f"Question {question_id} not found")
        
        # 统计关联数据
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
    录入题目（教师）
    - 教师：可以创建新题目
    """
    sess = SessionLocal()
    try:
        # 检查是否已存在
        existing = sess.query(Question).filter(Question.question_id == req.question_id).first()
        if existing:
            raise HTTPException(400, f"Question {req.question_id} already exists")
        
        # 创建新题目
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
    更新题目（教师）
    - 教师：可以更新题目
    """
    sess = SessionLocal()
    try:
        question = sess.query(Question).filter(Question.question_id == question_id).first()
        
        if not question:
            raise HTTPException(404, f"Question {question_id} not found")
        
        # 更新字段
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
    删除题目（教师）
    - 教师：可以删除题目
    """
    """
    删除题目
    仅老师可以使用
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


# ==================== 评分标准管理接口 ====================

@app.get("/questions/{question_id}/rubrics", response_model=RubricListResponse)
def list_rubrics(question_id: str, current_user: dict = Depends(require_any)):
    """
    查询题目的评分标准列表
    学生和老师都可以查看（用于了解评分标准）
    """
    sess = SessionLocal()
    try:
        # 检查题目是否存在
        question = sess.query(Question).filter(Question.question_id == question_id).first()
        if not question:
            raise HTTPException(404, f"Question {question_id} not found")
        
        # 查询评分标准
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
    录入评分标准（教师）
    - 教师：可以为题目创建评分标准
    """
    sess = SessionLocal()
    try:
        # 检查题目是否存在
        question = sess.query(Question).filter(Question.question_id == question_id).first()
        if not question:
            raise HTTPException(404, f"Question {question_id} not found")
        
        # 检查版本是否已存在
        existing = sess.query(QuestionRubric).filter(
            QuestionRubric.question_id == question_id,
            QuestionRubric.version == req.version
        ).first()
        if existing:
            raise HTTPException(400, f"Rubric version {req.version} already exists for question {question_id}")
        
        # 如果设置为激活，先取消其他激活的评分标准
        if req.is_active:
            sess.query(QuestionRubric).filter(
                QuestionRubric.question_id == question_id,
                QuestionRubric.is_active == True
            ).update({"is_active": False})
        
        # 创建新评分标准，使用当前登录用户ID
        rubric = QuestionRubric(
            question_id=question_id,
            version=req.version,
            rubric_json=req.rubric_json,
            is_active=req.is_active,
            created_by=current_user["id"]  # 使用当前登录用户ID
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
    更新评分标准（教师）
    - 教师：可以更新评分标准
    """
    sess = SessionLocal()
    try:
        rubric = sess.query(QuestionRubric).filter(QuestionRubric.id == rubric_id).first()
        
        if not rubric:
            raise HTTPException(404, f"Rubric {rubric_id} not found")
        
        # 更新字段
        if req.rubric_json is not None:
            rubric.rubric_json = req.rubric_json
        
        if req.is_active is not None:
            # 如果设置为激活，先取消同题目的其他激活评分标准
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
    激活评分标准（教师）
    - 教师：可以激活评分标准（同时取消同题目的其他激活评分标准）
    """
    sess = SessionLocal()
    try:
        rubric = sess.query(QuestionRubric).filter(QuestionRubric.id == rubric_id).first()
        
        if not rubric:
            raise HTTPException(404, f"Rubric {rubric_id} not found")
        
        # 取消同题目的其他激活评分标准
        sess.query(QuestionRubric).filter(
            QuestionRubric.question_id == rubric.question_id,
            QuestionRubric.id != rubric_id,
            QuestionRubric.is_active == True
        ).update({"is_active": False})
        
        # 激活当前评分标准
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
    获取评分标准详情
    - 学生：可以查看评分标准详情（用于了解评分标准）
    - 教师：可以查看评分标准详情（用于管理）
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


# 用户管理接口（仅老师）
@app.post("/users", response_model=UserItem, status_code=201)
def create_user(req: UserCreate, current_user: dict = Depends(require_teacher)):
    """创建用户（仅老师）"""
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
    """获取用户列表（仅老师）"""
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
    """获取用户详情（仅老师）"""
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
