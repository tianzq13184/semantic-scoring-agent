"""
测试数据库模型
"""
import pytest
from datetime import datetime
from api.db import Question, QuestionRubric, AnswerEvaluation


class TestQuestionModel:
    """测试 Question 模型"""
    
    def test_create_question(self, db_session):
        """测试创建题目"""
        question = Question(
            question_id="TEST_Q1",
            text="测试题目",
            topic="python"
        )
        db_session.add(question)
        db_session.commit()
        
        assert question.id is not None
        assert question.question_id == "TEST_Q1"
        assert question.created_at is not None
    
    def test_question_unique_constraint(self, db_session):
        """测试题目唯一性约束"""
        # 使用唯一的 question_id，避免与 sample_question fixture 冲突
        import uuid
        unique_id = f"UNIQUE_TEST_{uuid.uuid4().hex[:8]}"
        
        question1 = Question(
            question_id=unique_id,
            text="题目1",
            topic="python"
        )
        db_session.add(question1)
        db_session.commit()
        
        question2 = Question(
            question_id=unique_id,  # 重复的 question_id
            text="题目2",
            topic="python"
        )
        db_session.add(question2)
        
        with pytest.raises(Exception):  # 应该抛出唯一性约束错误
            db_session.commit()
        
        # 捕获异常后需要 rollback
        db_session.rollback()


class TestQuestionRubricModel:
    """测试 QuestionRubric 模型"""
    
    def test_create_rubric(self, db_session, sample_question):
        """测试创建评分标准"""
        rubric = QuestionRubric(
            question_id=sample_question.question_id,
            version="v1",
            rubric_json={"version": "v1", "dimensions": {}},
            is_active=True,
            created_by="test"
        )
        db_session.add(rubric)
        db_session.commit()
        
        assert rubric.id is not None
        assert rubric.question_id == sample_question.question_id
        assert rubric.is_active is True
    
    def test_rubric_foreign_key(self, db_session):
        """测试外键约束"""
        rubric = QuestionRubric(
            question_id="NON_EXISTENT",  # 不存在的题目
            version="v1",
            rubric_json={"version": "v1"}
        )
        db_session.add(rubric)
        
        # MySQL 会立即检查外键约束，应该抛出异常
        with pytest.raises(Exception):  # 应该抛出外键约束错误
            db_session.commit()
        
        # 捕获异常后需要 rollback
        db_session.rollback()


class TestAnswerEvaluationModel:
    """测试 AnswerEvaluation 模型"""
    
    def test_create_evaluation(self, db_session, sample_question):
        """测试创建评估结果"""
        # 先创建学生用户，满足外键约束
        from api.db import User
        student = User(id="student001", username="测试学生", role="student")
        db_session.add(student)
        db_session.commit()
        
        evaluation = AnswerEvaluation(
            question_id=sample_question.question_id,
            student_id="student001",
            student_answer="测试答案",
            auto_score=7.5,
            dimension_scores_json={"accuracy": 1.5},
            model_version="test-model",
            rubric_version="test-v1",
            raw_llm_output={"test": "data"}
        )
        db_session.add(evaluation)
        db_session.commit()
        
        assert evaluation.id is not None
        assert evaluation.auto_score == 7.5
        assert evaluation.created_at is not None
    
    def test_evaluation_optional_fields(self, db_session, sample_question):
        """测试可选字段"""
        evaluation = AnswerEvaluation(
            question_id=sample_question.question_id,
            student_answer="测试答案",
            auto_score=7.5,
            dimension_scores_json={},
            model_version="test",
            rubric_version="test"
        )
        db_session.add(evaluation)
        db_session.commit()
        
        assert evaluation.student_id is None
        assert evaluation.final_score is None
        assert evaluation.reviewer_id is None


class TestModelRelationships:
    """测试模型关系"""
    
    def test_question_rubrics_relationship(self, db_session, sample_question, sample_rubric):
        """测试题目和评分标准的关系"""
        db_session.refresh(sample_question)
        
        assert len(sample_question.rubrics) == 1
        assert sample_question.rubrics[0].id == sample_rubric.id
    
    def test_question_evaluations_relationship(self, db_session, sample_question, sample_evaluation):
        """测试题目和评估结果的关系"""
        db_session.refresh(sample_question)
        
        assert len(sample_question.evaluations) == 1
        assert sample_question.evaluations[0].id == sample_evaluation.id
    
    def test_cascade_delete_rubrics(self, db_session, sample_question, sample_rubric):
        """测试级联删除评分标准"""
        rubric_id = sample_rubric.id
        
        db_session.delete(sample_question)
        db_session.commit()
        
        # 检查评分标准是否被删除
        deleted_rubric = db_session.query(QuestionRubric).filter(
            QuestionRubric.id == rubric_id
        ).first()
        assert deleted_rubric is None
    
    def test_set_null_on_delete_question(self, db_session, sample_question, sample_evaluation):
        """测试删除题目时评估结果的 question_id 设为 NULL"""
        evaluation_id = sample_evaluation.id
        
        db_session.delete(sample_question)
        db_session.commit()
        
        # 检查评估结果的 question_id 是否被设为 NULL
        evaluation = db_session.query(AnswerEvaluation).filter(
            AnswerEvaluation.id == evaluation_id
        ).first()
        assert evaluation.question_id is None
