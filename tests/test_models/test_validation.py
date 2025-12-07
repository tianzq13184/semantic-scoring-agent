"""
测试数据模型验证
"""
import pytest
from pydantic import ValidationError
from api.models import (
    EvaluationRequest, LLMScorePayload, ReviewSaveRequest,
    QuestionCreate, QuestionUpdate, RubricCreate
)


class TestEvaluationRequest:
    """测试评估请求模型"""
    
    def test_valid_request(self):
        """测试有效请求"""
        req = EvaluationRequest(
            question_id="Q2105",
            student_answer="这是一个足够长的答案，用于测试验证功能。"
        )
        assert req.question_id == "Q2105"
        assert len(req.student_answer) >= 10
    
    def test_question_id_required(self):
        """测试 question_id 必填"""
        with pytest.raises(ValidationError):
            EvaluationRequest(
                student_answer="这是一个足够长的答案。"
            )
    
    def test_student_answer_too_short(self):
        """测试答案太短"""
        with pytest.raises(ValidationError):
            EvaluationRequest(
                question_id="Q2105",
                student_answer="短"
            )
    
    def test_student_answer_too_long(self):
        """测试答案太长"""
        with pytest.raises(ValidationError):
            EvaluationRequest(
                question_id="Q2105",
                student_answer="a" * 4001
            )
    
    def test_with_rubric_json(self):
        """测试带评分标准的请求"""
        req = EvaluationRequest(
            question_id="Q2105",
            student_answer="这是一个足够长的答案。",
            rubric_json={"version": "v1", "dimensions": {}}
        )
        assert req.rubric_json is not None


class TestLLMScorePayload:
    """测试 LLM 评分负载模型"""
    
    def test_valid_payload(self):
        """测试有效负载"""
        payload = LLMScorePayload(
            total_score=7.5,
            dimension_breakdown={
                "accuracy": 1.5,
                "structure": 1.8,
                "clarity": 1.6,
                "business": 1.4,
                "language": 1.2
            },
            key_points_evaluation=["point1", "point2"],
            improvement_recommendations=["tip1", "tip2"]
        )
        assert payload.total_score == 7.5
    
    def test_total_score_out_of_range(self):
        """测试总分超出范围"""
        with pytest.raises(ValidationError):
            LLMScorePayload(
                total_score=11.0,
                dimension_breakdown={"accuracy": 1.5},
                key_points_evaluation=[],
                improvement_recommendations=[]
            )
    
    def test_dimension_score_out_of_range(self):
        """测试维度分数超出范围"""
        with pytest.raises(ValidationError):
            LLMScorePayload(
                total_score=7.5,
                dimension_breakdown={"accuracy": 2.5},  # 超出 0-2 范围
                key_points_evaluation=[],
                improvement_recommendations=[]
            )
    
    def test_dimension_score_negative(self):
        """测试维度分数为负数"""
        with pytest.raises(ValidationError):
            LLMScorePayload(
                total_score=7.5,
                dimension_breakdown={"accuracy": -0.5},
                key_points_evaluation=[],
                improvement_recommendations=[]
            )


class TestReviewSaveRequest:
    """测试审核保存请求模型"""
    
    def test_valid_request(self):
        """测试有效请求"""
        req = ReviewSaveRequest(
            evaluation_id=1,
            final_score=8.5,
            review_notes="答案很好",
            reviewer_id="teacher001"
        )
        assert req.evaluation_id == 1
        assert req.final_score == 8.5
    
    def test_final_score_out_of_range(self):
        """测试最终分数超出范围"""
        with pytest.raises(ValidationError):
            ReviewSaveRequest(
                evaluation_id=1,
                final_score=11.0
            )
    
    def test_optional_fields(self):
        """测试可选字段"""
        req = ReviewSaveRequest(
            evaluation_id=1,
            final_score=8.5
        )
        assert req.review_notes is None
        assert req.reviewer_id is None


class TestQuestionCreate:
    """测试题目创建模型"""
    
    def test_valid_question(self):
        """测试有效题目"""
        q = QuestionCreate(
            question_id="Q2106",
            text="测试题目",
            topic="python"
        )
        assert q.question_id == "Q2106"
        assert q.text == "测试题目"
    
    def test_question_id_required(self):
        """测试 question_id 必填"""
        with pytest.raises(ValidationError):
            QuestionCreate(text="测试题目")
    
    def test_text_required(self):
        """测试 text 必填"""
        with pytest.raises(ValidationError):
            QuestionCreate(question_id="Q2106")
    
    def test_topic_optional(self):
        """测试 topic 可选"""
        q = QuestionCreate(
            question_id="Q2106",
            text="测试题目"
        )
        assert q.topic is None


class TestRubricCreate:
    """测试评分标准创建模型"""
    
    def test_valid_rubric(self):
        """测试有效评分标准"""
        rubric = RubricCreate(
            version="v1",
            rubric_json={
                "version": "v1",
                "dimensions": {"accuracy": 1}
            }
        )
        assert rubric.version == "v1"
        assert rubric.is_active is False  # 默认值
    
    def test_version_required(self):
        """测试 version 必填"""
        with pytest.raises(ValidationError):
            RubricCreate(
                rubric_json={"dimensions": {}}
            )
    
    def test_rubric_json_required(self):
        """测试 rubric_json 必填"""
        with pytest.raises(ValidationError):
            RubricCreate(version="v1")
