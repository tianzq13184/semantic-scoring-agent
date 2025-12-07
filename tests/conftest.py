"""
Pytest configuration and shared fixtures
"""
import pytest
import os
import sys

# 设置测试环境变量（必须在导入之前）
os.environ["DB_URL"] = "sqlite:///:memory:"
os.environ["OPENAI_API_KEY"] = "test-key"  # Mock key for testing

# 延迟导入，避免在测试时加载 langchain_openai
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.db import Base, Question, QuestionRubric, AnswerEvaluation


@pytest.fixture(scope="function")
def db_session():
    """创建测试数据库会话"""
    # 使用内存数据库
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def client(db_session):
    """创建测试客户端，使用测试数据库"""
    # 延迟导入，避免在导入时加载 langchain
    # 只有在实际需要时才导入
    try:
        from fastapi.testclient import TestClient
        from api.main import app
        
        # 创建测试客户端
        test_client = TestClient(app)
        yield test_client
    except ImportError as e:
        # 如果 langchain_openai 未安装，跳过需要 client 的测试
        pytest.skip(f"需要 langchain_openai 模块: {e}")


@pytest.fixture
def sample_question(db_session):
    """创建示例题目"""
    question = Question(
        question_id="TEST_Q1",
        text="测试题目：请简述 Python 的基本数据类型。",
        topic="python"
    )
    db_session.add(question)
    db_session.commit()
    db_session.refresh(question)
    return question


@pytest.fixture
def sample_rubric(db_session, sample_question):
    """创建示例评分标准"""
    rubric = QuestionRubric(
        question_id=sample_question.question_id,
        version="test-v1",
        rubric_json={
            "version": "test-v1",
            "dimensions": {
                "accuracy": 1,
                "structure": 1,
                "clarity": 1,
                "business": 1,
                "language": 1
            },
            "key_points": ["数据类型", "使用场景"],
            "common_mistakes": ["概念混淆"]
        },
        is_active=True,
        created_by="test"
    )
    db_session.add(rubric)
    db_session.commit()
    db_session.refresh(rubric)
    return rubric


@pytest.fixture
def sample_evaluation(db_session, sample_question):
    """创建示例评估结果"""
    evaluation = AnswerEvaluation(
        question_id=sample_question.question_id,
        student_id="student001",
        student_answer="Python 的基本数据类型包括整数、浮点数、字符串等。",
        auto_score=7.5,
        final_score=None,
        dimension_scores_json={
            "accuracy": 1.5,
            "structure": 1.8,
            "clarity": 1.6,
            "business": 1.4,
            "language": 1.2
        },
        model_version="test-model-v1",
        rubric_version="test-v1",
        raw_llm_output={"test": "data"}
    )
    db_session.add(evaluation)
    db_session.commit()
    db_session.refresh(evaluation)
    return evaluation


@pytest.fixture
def mock_llm_response():
    """Mock LLM 响应数据"""
    return {
        "total_score": 7.5,
        "dimension_breakdown": {
            "accuracy": 1.5,
            "structure": 1.8,
            "clarity": 1.6,
            "business": 1.4,
            "language": 1.2
        },
        "key_points_evaluation": [
            "数据类型 -> covered",
            "使用场景 -> partially covered"
        ],
        "improvement_recommendations": [
            "可以补充更多数据类型示例",
            "建议说明各类型的应用场景"
        ]
    }
