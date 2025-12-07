"""
测试题目管理接口
"""
import pytest
from fastapi.testclient import TestClient


class TestListQuestions:
    """测试 GET /questions"""
    
    def test_list_questions(self, client, db_session, sample_question, monkeypatch):
        """测试列表查询"""
        import api.main as main_module
        monkeypatch.setattr(main_module, "SessionLocal", lambda: db_session)
        
        response = client.get("/questions")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert len(data["items"]) >= 1
    
    def test_filter_by_topic(self, client, db_session, sample_question, monkeypatch):
        """测试按主题筛选"""
        import api.main as main_module
        monkeypatch.setattr(main_module, "SessionLocal", lambda: db_session)
        
        response = client.get("/questions?topic=python")
        
        assert response.status_code == 200
        data = response.json()
        # 所有结果应该都是 python 主题
        for item in data["items"]:
            assert item["topic"] == "python"
    
    def test_pagination(self, client, db_session, monkeypatch):
        """测试分页"""
        import api.main as main_module
        monkeypatch.setattr(main_module, "SessionLocal", lambda: db_session)
        
        # 创建多个题目
        from api.db import Question
        for i in range(5):
            question = db_session.query(Question).filter(
                Question.question_id == f"TEST_Q{i}"
            ).first()
            if not question:
                q = Question(
                    question_id=f"TEST_Q{i}",
                    text=f"题目{i}",
                    topic="test"
                )
                db_session.add(q)
        db_session.commit()
        
        response = client.get("/questions?limit=2&offset=0")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 2


class TestGetQuestion:
    """测试 GET /questions/{question_id}"""
    
    def test_get_existing_question(self, client, db_session, sample_question, monkeypatch):
        """测试获取存在的题目"""
        import api.main as main_module
        monkeypatch.setattr(main_module, "SessionLocal", lambda: db_session)
        
        response = client.get(f"/questions/{sample_question.question_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["question_id"] == sample_question.question_id
        assert "rubrics_count" in data
        assert "evaluations_count" in data
    
    def test_get_nonexistent_question(self, client, db_session, monkeypatch):
        """测试获取不存在的题目"""
        import api.main as main_module
        monkeypatch.setattr(main_module, "SessionLocal", lambda: db_session)
        
        response = client.get("/questions/NON_EXISTENT")
        
        assert response.status_code == 404


class TestCreateQuestion:
    """测试 POST /questions"""
    
    def test_create_question(self, client, db_session, monkeypatch):
        """测试创建题目"""
        import api.main as main_module
        monkeypatch.setattr(main_module, "SessionLocal", lambda: db_session)
        
        response = client.post(
            "/questions",
            json={
                "question_id": "NEW_Q1",
                "text": "新题目",
                "topic": "python"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["question_id"] == "NEW_Q1"
        assert data["text"] == "新题目"
    
    def test_create_duplicate_question(self, client, db_session, sample_question, monkeypatch):
        """测试创建重复题目"""
        import api.main as main_module
        monkeypatch.setattr(main_module, "SessionLocal", lambda: db_session)
        
        response = client.post(
            "/questions",
            json={
                "question_id": sample_question.question_id,  # 重复
                "text": "新题目",
                "topic": "python"
            }
        )
        
        assert response.status_code == 400


class TestUpdateQuestion:
    """测试 PUT /questions/{question_id}"""
    
    def test_update_question(self, client, db_session, sample_question, monkeypatch):
        """测试更新题目"""
        import api.main as main_module
        monkeypatch.setattr(main_module, "SessionLocal", lambda: db_session)
        
        response = client.put(
            f"/questions/{sample_question.question_id}",
            json={
                "text": "更新后的题目",
                "topic": "updated-topic"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["text"] == "更新后的题目"
        assert data["topic"] == "updated-topic"
    
    def test_partial_update(self, client, db_session, sample_question, monkeypatch):
        """测试部分更新"""
        import api.main as main_module
        monkeypatch.setattr(main_module, "SessionLocal", lambda: db_session)
        
        response = client.put(
            f"/questions/{sample_question.question_id}",
            json={
                "text": "只更新文本"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["text"] == "只更新文本"
        # topic 应该保持不变


class TestDeleteQuestion:
    """测试 DELETE /questions/{question_id}"""
    
    def test_delete_question(self, client, db_session, sample_question, monkeypatch):
        """测试删除题目"""
        import api.main as main_module
        monkeypatch.setattr(main_module, "SessionLocal", lambda: db_session)
        
        question_id = sample_question.question_id
        
        response = client.delete(f"/questions/{question_id}")
        
        assert response.status_code == 204
        
        # 验证题目已删除
        from api.db import Question
        deleted = db_session.query(Question).filter(
            Question.question_id == question_id
        ).first()
        assert deleted is None
    
    def test_delete_nonexistent_question(self, client, db_session, monkeypatch):
        """测试删除不存在的题目"""
        import api.main as main_module
        monkeypatch.setattr(main_module, "SessionLocal", lambda: db_session)
        
        response = client.delete("/questions/NON_EXISTENT")
        
        assert response.status_code == 404
