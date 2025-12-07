"""
测试教师审核接口
"""
import pytest
from fastapi.testclient import TestClient


class TestReviewSave:
    """测试 POST /review/save"""
    
    def test_save_review(self, client, db_session, sample_evaluation, monkeypatch):
        """测试保存审核"""
        import api.main as main_module
        monkeypatch.setattr(main_module, "SessionLocal", lambda: db_session)
        
        response = client.post(
            "/review/save",
            json={
                "evaluation_id": sample_evaluation.id,
                "final_score": 8.5,
                "review_notes": "答案很好",
                "reviewer_id": "teacher001"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["final_score"] == 8.5
        assert data["auto_score"] == sample_evaluation.auto_score
    
    def test_review_nonexistent_evaluation(self, client, db_session, monkeypatch):
        """测试审核不存在的评估"""
        import api.main as main_module
        monkeypatch.setattr(main_module, "SessionLocal", lambda: db_session)
        
        response = client.post(
            "/review/save",
            json={
                "evaluation_id": 99999,
                "final_score": 8.5
            }
        )
        
        assert response.status_code == 404
    
    def test_invalid_score_range(self, client):
        """测试评分超出范围"""
        response = client.post(
            "/review/save",
            json={
                "evaluation_id": 1,
                "final_score": 11.0  # 超出范围
            }
        )
        
        assert response.status_code == 422  # Validation error


class TestListEvaluations:
    """测试 GET /evaluations"""
    
    def test_list_evaluations(self, client, db_session, sample_evaluation, monkeypatch):
        """测试列表查询"""
        import api.main as main_module
        monkeypatch.setattr(main_module, "SessionLocal", lambda: db_session)
        
        response = client.get("/evaluations")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1
    
    def test_filter_by_question_id(self, client, db_session, sample_evaluation, sample_question, monkeypatch):
        """测试按题目ID筛选"""
        import api.main as main_module
        monkeypatch.setattr(main_module, "SessionLocal", lambda: db_session)
        
        response = client.get(f"/evaluations?question_id={sample_question.question_id}")
        
        assert response.status_code == 200
        data = response.json()
        for item in data["items"]:
            assert item["question_id"] == sample_question.question_id
    
    def test_pagination(self, client, db_session, sample_evaluation, monkeypatch):
        """测试分页"""
        import api.main as main_module
        monkeypatch.setattr(main_module, "SessionLocal", lambda: db_session)
        
        response = client.get("/evaluations?limit=1&offset=0")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 1


class TestGetEvaluationDetail:
    """测试 GET /evaluations/{evaluation_id}"""
    
    def test_get_existing_evaluation(self, client, db_session, sample_evaluation, monkeypatch):
        """测试获取存在的评估"""
        import api.main as main_module
        monkeypatch.setattr(main_module, "SessionLocal", lambda: db_session)
        
        response = client.get(f"/evaluations/{sample_evaluation.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_evaluation.id
        assert data["student_answer"] == sample_evaluation.student_answer
    
    def test_get_nonexistent_evaluation(self, client, db_session, monkeypatch):
        """测试获取不存在的评估"""
        import api.main as main_module
        monkeypatch.setattr(main_module, "SessionLocal", lambda: db_session)
        
        response = client.get("/evaluations/99999")
        
        assert response.status_code == 404
