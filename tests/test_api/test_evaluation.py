"""
测试评估接口
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


class TestEvaluateShortAnswer:
    """测试 POST /evaluate/short-answer"""
    
    @patch('api.main.call_llm')
    def test_successful_evaluation(self, mock_call_llm, client, sample_question, auth_headers_student):
        """测试成功评估"""
        print("\n" + "="*80)
        print("开始测试: test_successful_evaluation")
        print(f"Mock对象: {mock_call_llm}")
        print(f"Mock是否已设置: {hasattr(mock_call_llm, 'return_value')}")
        print("="*80)
        
        # Mock LLM 响应
        mock_call_llm.return_value = {
            "total_score": 7.5,
            "dimension_breakdown": {
                "accuracy": 1.5,
                "structure": 1.8,
                "clarity": 1.6,
                "business": 1.4,
                "language": 1.2
            },
            "key_points_evaluation": ["point1 -> covered"],
            "improvement_recommendations": ["tip1"]
        }
        
        print(f"\n发送请求: question_id={sample_question.question_id}")
        print(f"Mock return_value已设置: {mock_call_llm.return_value is not None}")
        
        response = client.post(
            "/evaluate/short-answer",
            json={
                "question_id": sample_question.question_id,
                "student_answer": "这是一个足够长的答案，用于测试评估功能。"
            },
            headers=auth_headers_student
        )
        
        print(f"\n收到响应: status_code={response.status_code}")
        print(f"Mock是否被调用: {mock_call_llm.called}")
        if mock_call_llm.called:
            print(f"Mock调用次数: {mock_call_llm.call_count}")
            print(f"Mock调用参数: {mock_call_llm.call_args}")
        print("="*80 + "\n")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_score"] == 7.5
        assert "dimension_breakdown" in data
        assert data["question_id"] == sample_question.question_id
    
    def test_question_not_found(self, client, auth_headers_student):
        """测试题目不存在"""
        response = client.post(
            "/evaluate/short-answer",
            json={
                "question_id": "NON_EXISTENT",
                "student_answer": "这是一个足够长的答案。"
            },
            headers=auth_headers_student
        )
        
        assert response.status_code == 404
    
    def test_invalid_answer_length(self, client, auth_headers_student):
        """测试答案长度验证"""
        response = client.post(
            "/evaluate/short-answer",
            json={
                "question_id": "Q2105",
                "student_answer": "短"  # 太短
            },
            headers=auth_headers_student
        )
        
        assert response.status_code == 422  # Validation error
    
    @patch('api.main.call_llm')
    def test_llm_call_failure(self, mock_call_llm, client, sample_question, auth_headers_student):
        """测试 LLM 调用失败"""
        mock_call_llm.side_effect = Exception("LLM API error")
        
        response = client.post(
            "/evaluate/short-answer",
            json={
                "question_id": sample_question.question_id,
                "student_answer": "这是一个足够长的答案。"
            },
            headers=auth_headers_student
        )
        
        assert response.status_code == 502
        assert "LLM call failed" in response.json()["detail"]
    
    @patch('api.main.call_llm')
    def test_custom_rubric(self, mock_call_llm, client, sample_question, auth_headers_student):
        """测试使用自定义评分标准"""
        mock_call_llm.return_value = {
            "total_score": 8.0,
            "dimension_breakdown": {"accuracy": 1.6},
            "key_points_evaluation": [],
            "improvement_recommendations": []
        }
        
        response = client.post(
            "/evaluate/short-answer",
            json={
                "question_id": sample_question.question_id,
                "student_answer": "这是一个足够长的答案。",
                "rubric_json": {
                    "version": "custom-v1",
                    "dimensions": {"accuracy": 1}
                }
            },
            headers=auth_headers_student
        )
        
        assert response.status_code == 200
        # 验证使用了自定义评分标准
        assert mock_call_llm.called

