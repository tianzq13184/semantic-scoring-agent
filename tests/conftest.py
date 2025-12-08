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

from api.db import Base, Question, QuestionRubric, AnswerEvaluation, User


@pytest.fixture(scope="function")
def db_session():
    """创建测试数据库会话"""
    # 使用内存数据库，支持多线程访问
    engine = create_engine("sqlite:///:memory:", echo=False, connect_args={"check_same_thread": False})
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
        from fastapi import Header
        from typing import Optional
        from sqlalchemy.orm import sessionmaker
        from api.main import app
        from api.db import User, Base
        from api.auth import get_current_user as original_get_current_user
        
        # 获取测试数据库的 engine
        test_engine = db_session.bind
        # 确保表已创建
        Base.metadata.create_all(test_engine)
        TestSessionLocal = sessionmaker(bind=test_engine, expire_on_commit=False)
        
        # 创建一个使用测试数据库的 get_current_user
        def get_test_current_user(token: Optional[str] = Header(None, alias="X-User-Token")) -> Optional[dict]:
            """使用测试数据库的 get_current_user"""
            if not token:
                return None
            
            # 创建新的会话（从测试数据库的 engine）
            sess = TestSessionLocal()
            try:
                user = sess.query(User).filter(User.id == token).first()
                if user:
                    return {
                        "id": user.id,
                        "username": user.username,
                        "role": user.role
                    }
                return None
            finally:
                sess.close()
        
        # 覆盖 api.main 和 api.auth 中的 SessionLocal
        import api.db as db_module
        import api.main as main_module
        import api.auth as auth_module
        
        # 保存原始值
        original_db_session_local = db_module.SessionLocal
        original_main_session_local = main_module.SessionLocal
        
        # 创建一个函数来返回测试会话
        def get_test_session():
            return TestSessionLocal()
        
        # 覆盖 SessionLocal
        db_module.SessionLocal = get_test_session
        main_module.SessionLocal = get_test_session
        auth_module.SessionLocal = get_test_session
        
        # 使用 FastAPI 的依赖覆盖
        app.dependency_overrides[original_get_current_user] = get_test_current_user
        
        # 创建测试客户端
        test_client = TestClient(app)
        yield test_client
        
        # 清理依赖覆盖
        app.dependency_overrides.clear()
        
        # 恢复原始值
        db_module.SessionLocal = original_db_session_local
        main_module.SessionLocal = original_main_session_local
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
def sample_teacher(db_session):
    """创建示例老师用户"""
    teacher = User(id="teacher001", username="张老师", role="teacher")
    db_session.add(teacher)
    db_session.commit()
    db_session.refresh(teacher)
    return teacher

@pytest.fixture
def sample_student(db_session):
    """创建示例学生用户"""
    student = User(id="student001", username="学生1", role="student")
    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)
    return student

@pytest.fixture
def test_teacher(db_session):
    """创建测试用的老师用户"""
    teacher = User(id="test_teacher", username="测试老师", role="teacher")
    db_session.add(teacher)
    db_session.commit()
    db_session.refresh(teacher)
    return teacher

@pytest.fixture
def test_student(db_session):
    """创建测试用的学生用户"""
    student = User(id="test_student", username="测试学生", role="student")
    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)
    return student

@pytest.fixture
def auth_headers_student(test_student):
    """返回学生认证头"""
    return {"X-User-Token": test_student.id}

@pytest.fixture
def auth_headers_teacher(test_teacher):
    """返回老师认证头"""
    return {"X-User-Token": test_teacher.id}

@pytest.fixture
def sample_evaluation(db_session, sample_question, sample_student):
    """创建示例评估结果"""
    evaluation = AnswerEvaluation(
        question_id=sample_question.question_id,
        student_id=sample_student.id,
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
