from pydantic import BaseModel, Field, constr, model_validator
from typing import Dict, List, Optional

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
