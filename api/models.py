from pydantic import BaseModel, Field, constr, model_validator
from typing import Dict, List, Optional
from datetime import datetime

NonEmptyStr = constr(strip_whitespace=True, min_length=1)
AnswerStr = constr(strip_whitespace=True, min_length=10, max_length=4000)

class EvaluationRequest(BaseModel):
    question_id: NonEmptyStr
    student_answer: AnswerStr
    with_rubric: Optional[bool] = False
    rubric_json: Optional[dict] = None  # 前端可直接传入rubric（可选）

class LLMScorePayload(BaseModel):
    total_score: float = Field(ge=0, le=10)
    dimension_breakdown: Dict[str, float]
    key_points_evaluation: List[str]
    improvement_recommendations: List[str]

    @model_validator(mode="after")
    def validate_dimensions(self):
        for name, score in self.dimension_breakdown.items():
            if not 0 <= float(score) <= 2:
                raise ValueError(f"Dimension '{name}' must be within [0,2], got {score}")
        return self

class EvaluationResult(LLMScorePayload):
    question_id: str
    rubric_version: str
    provider: str
    model_id: str
    model_version: str
    raw_llm_output: dict  # 原始JSON

class ReviewSaveRequest(BaseModel):
    evaluation_id: int
    final_score: float = Field(ge=0, le=10)
    review_notes: Optional[str] = None
    reviewer_id: Optional[str] = None

class ReviewSaveResponse(BaseModel):
    success: bool
    message: str
    evaluation_id: int
    auto_score: Optional[float]
    final_score: float

class EvaluationListItem(BaseModel):
    id: int
    question_id: str
    student_id: Optional[str]
    auto_score: Optional[float]
    final_score: Optional[float]
    created_at: datetime
    updated_at: Optional[datetime]
    reviewer_id: Optional[str]

class EvaluationDetail(EvaluationListItem):
    student_answer: str
    dimension_scores_json: Optional[Dict[str, float]]
    model_version: Optional[str]
    rubric_version: Optional[str]
    review_notes: Optional[str]
    raw_llm_output: Optional[dict]

class EvaluationListResponse(BaseModel):
    total: int
    items: List[EvaluationListItem]


# 题目管理相关模型
class QuestionCreate(BaseModel):
    question_id: NonEmptyStr
    text: str = Field(..., min_length=1)
    topic: Optional[str] = None

class QuestionUpdate(BaseModel):
    text: Optional[str] = Field(None, min_length=1)
    topic: Optional[str] = None

class QuestionItem(BaseModel):
    id: int
    question_id: str
    text: str
    topic: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

class QuestionDetail(QuestionItem):
    rubrics_count: Optional[int] = 0
    evaluations_count: Optional[int] = 0

class QuestionListResponse(BaseModel):
    total: int
    items: List[QuestionItem]


# 评分标准管理相关模型
class RubricCreate(BaseModel):
    version: NonEmptyStr
    rubric_json: dict
    is_active: Optional[bool] = False
    created_by: Optional[str] = None

class RubricUpdate(BaseModel):
    rubric_json: Optional[dict] = None
    is_active: Optional[bool] = None

class RubricItem(BaseModel):
    id: int
    question_id: str
    version: str
    is_active: bool
    created_by: Optional[str]
    created_at: datetime

class RubricDetail(RubricItem):
    rubric_json: dict

class RubricListResponse(BaseModel):
    total: int
    items: List[RubricItem]

class RubricActivateResponse(BaseModel):
    success: bool
    message: str
    rubric_id: int
    question_id: str
    version: str
