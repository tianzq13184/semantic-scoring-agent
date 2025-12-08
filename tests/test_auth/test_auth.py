"""
测试权限系统
"""
import pytest
from fastapi.testclient import TestClient
from api.db import User, SessionLocal


class TestUserModel:
    """测试用户模型"""
    
    def test_create_user(self, db_session):
        """测试创建用户"""
        user = User(
            id="test_user_001",
            username="测试用户",
            role="student"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        assert user.id == "test_user_001"
        assert user.username == "测试用户"
        assert user.role == "student"
    
    def test_user_roles(self, db_session):
        """测试不同角色的用户"""
        teacher = User(id="t1", username="老师1", role="teacher")
        student = User(id="s1", username="学生1", role="student")
        
        db_session.add(teacher)
        db_session.add(student)
        db_session.commit()
        
        assert teacher.role == "teacher"
        assert student.role == "student"


class TestAuthMiddleware:
    """测试权限检查中间件"""
    
    def test_get_current_user_with_token(self, db_session, monkeypatch):
        """测试通过token获取用户"""
        from api.auth import get_current_user
        
        # 创建测试用户
        user = User(id="test_user", username="测试", role="student")
        db_session.add(user)
        db_session.commit()
        
        # Mock 请求头
        class MockRequest:
            headers = {"x-user-token": "test_user"}
        
        # 测试获取用户
        monkeypatch.setattr("api.auth.SessionLocal", lambda: db_session)
        result = get_current_user(token="test_user")
        
        assert result is not None
        assert result["id"] == "test_user"
        assert result["role"] == "student"
    
    def test_get_current_user_without_token(self):
        """测试没有token时返回None"""
        from api.auth import get_current_user
        
        result = get_current_user(token=None)
        assert result is None
    
    def test_get_current_user_invalid_token(self, db_session, monkeypatch):
        """测试无效token"""
        from api.auth import get_current_user
        
        monkeypatch.setattr("api.auth.SessionLocal", lambda: db_session)
        result = get_current_user(token="invalid_user")
        
        assert result is None


class TestAPIAuth:
    """测试API接口的权限控制"""
    
    def test_evaluate_requires_auth(self, client, db_session, sample_question):
        """测试评估接口需要认证"""
        # 不提供认证头，应该返回401
        response = client.post(
            "/evaluate/short-answer",
            json={
                "question_id": sample_question.question_id,
                "student_answer": "这是一个足够长的答案，用于测试评估功能。"
            }
        )
        
        assert response.status_code == 401
    
    def test_evaluate_with_student_token(self, client, db_session, sample_question):
        """测试学生可以答题"""
        # 创建学生用户
        student = User(id="test_student", username="测试学生", role="student")
        db_session.add(student)
        db_session.commit()
        
        # Mock LLM 调用
        from unittest.mock import patch
        with patch('api.main.call_llm') as mock_llm:
            mock_llm.return_value = {
                "total_score": 7.5,
                "dimension_breakdown": {"accuracy": 1.5, "structure": 1.8, "clarity": 1.6, "business": 1.4, "language": 1.2},
                "key_points_evaluation": [],
                "improvement_recommendations": []
            }
            
            response = client.post(
                "/evaluate/short-answer",
                json={
                    "question_id": sample_question.question_id,
                    "student_answer": "这是一个足够长的答案，用于测试评估功能。"
                },
                headers={"X-User-Token": "test_student"}
            )
            
            assert response.status_code == 200
            assert response.json()["total_score"] == 7.5
    
    def test_review_requires_teacher(self, client, db_session, sample_evaluation):
        """测试判分接口需要老师权限"""
        # 创建学生用户
        student = User(id="test_student", username="测试学生", role="student")
        db_session.add(student)
        db_session.commit()
        
        # 学生尝试判分，应该被拒绝
        response = client.post(
            "/review/save",
            json={
                "evaluation_id": sample_evaluation.id,
                "final_score": 8.5
            },
            headers={"X-User-Token": "test_student"}
        )
        
        assert response.status_code == 403
    
    def test_review_with_teacher_token(self, client, db_session, sample_evaluation):
        """测试老师可以判分"""
        # 创建老师用户
        teacher = User(id="test_teacher", username="测试老师", role="teacher")
        db_session.add(teacher)
        db_session.commit()
        
        response = client.post(
            "/review/save",
            json={
                "evaluation_id": sample_evaluation.id,
                "final_score": 8.5,
                "review_notes": "很好"
            },
            headers={"X-User-Token": "test_teacher"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["final_score"] == 8.5
    
    def test_student_can_only_see_own_evaluations(self, client, db_session, sample_question):
        """测试学生只能看到自己的评估结果"""
        # 创建两个学生
        student1 = User(id="student1", username="学生1", role="student")
        student2 = User(id="student2", username="学生2", role="student")
        db_session.add(student1)
        db_session.add(student2)
        db_session.commit()
        
        # 创建两个评估（分别属于两个学生）
        from api.db import AnswerEvaluation
        eval1 = AnswerEvaluation(
            question_id=sample_question.question_id,
            student_id="student1",
            student_answer="答案1",
            auto_score=7.0
        )
        eval2 = AnswerEvaluation(
            question_id=sample_question.question_id,
            student_id="student2",
            student_answer="答案2",
            auto_score=8.0
        )
        db_session.add(eval1)
        db_session.add(eval2)
        db_session.commit()
        
        # student1 只能看到自己的结果
        response = client.get(
            "/evaluations",
            headers={"X-User-Token": "student1"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["student_id"] == "student1"
    
    def test_teacher_can_see_all_evaluations(self, client, db_session, sample_question):
        """测试老师可以看到所有评估结果"""
        # 创建老师和学生
        teacher = User(id="teacher1", username="老师1", role="teacher")
        student1 = User(id="student1", username="学生1", role="student")
        student2 = User(id="student2", username="学生2", role="student")
        db_session.add(teacher)
        db_session.add(student1)
        db_session.add(student2)
        db_session.commit()
        
        # 创建两个评估
        from api.db import AnswerEvaluation
        eval1 = AnswerEvaluation(
            question_id=sample_question.question_id,
            student_id="student1",
            student_answer="答案1",
            auto_score=7.0
        )
        eval2 = AnswerEvaluation(
            question_id=sample_question.question_id,
            student_id="student2",
            student_answer="答案2",
            auto_score=8.0
        )
        db_session.add(eval1)
        db_session.add(eval2)
        db_session.commit()
        
        # 老师可以看到所有结果
        response = client.get(
            "/evaluations",
            headers={"X-User-Token": "teacher1"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 2
    
    def test_question_management_requires_teacher(self, client, db_session):
        """测试题目管理需要老师权限"""
        # 创建学生
        student = User(id="student1", username="学生1", role="student")
        db_session.add(student)
        db_session.commit()
        
        # 学生尝试创建题目，应该被拒绝
        response = client.post(
            "/questions",
            json={
                "question_id": "NEW_Q",
                "text": "新题目",
                "topic": "test"
            },
            headers={"X-User-Token": "student1"}
        )
        
        assert response.status_code == 403
    
    def test_user_management_requires_teacher(self, client, db_session):
        """测试用户管理需要老师权限"""
        # 创建老师
        teacher = User(id="teacher1", username="老师1", role="teacher")
        db_session.add(teacher)
        db_session.commit()
        
        # 老师可以创建用户
        response = client.post(
            "/users",
            json={
                "id": "new_student",
                "username": "新学生",
                "role": "student"
            },
            headers={"X-User-Token": "teacher1"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "new_student"
        assert data["role"] == "student"

