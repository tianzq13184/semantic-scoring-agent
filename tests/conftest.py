"""
Pytest configuration and shared fixtures
"""
import pytest
import os
import sys
import logging

# Configure test environment log level
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Set test environment variables (must be before imports)
# Test environment uses MySQL database
# Note: @ in password needs to be URL encoded as %40
os.environ["DB_URL"] = "mysql+pymysql://root:Drillinsight%402099@mysql-tcs.drillinsight.com:3306/semantic_scoring_test"
os.environ["OPENAI_API_KEY"] = "test-key"  # Mock key for testing

# Defer import to avoid loading langchain_openai during test
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.db import Base, Question, QuestionRubric, AnswerEvaluation, User


@pytest.fixture(scope="function")
def db_session():
    """Create test database session"""
    import pymysql
    pymysql.install_as_MySQLdb()
    
    test_db_url = "mysql+pymysql://root:Drillinsight%402099@mysql-tcs.drillinsight.com:3306/semantic_scoring_test"
    
    engine = create_engine(
        test_db_url, 
        echo=False, 
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=2,
        pool_recycle=3600,
        pool_timeout=5,
        connect_args={'connect_timeout': 3}
    )
    
    Base.metadata.create_all(engine)
    
    TestingSessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    
    session = TestingSessionLocal()
    
    def cleanup_data():
        try:
            from sqlalchemy import text
            session.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
            session.query(AnswerEvaluation).delete()
            session.query(QuestionRubric).delete()
            session.query(Question).delete()
            session.query(User).delete()
            session.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
            session.commit()
        except Exception as e:
            session.rollback()
            try:
                session.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
                session.commit()
            except:
                pass
    
    cleanup_data()
    
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        cleanup_data()
        session.close()


@pytest.fixture(scope="function")
def client(db_session):
    """Create test client using test database"""
    try:
        from fastapi.testclient import TestClient
        from fastapi import Header
        from typing import Optional
        from sqlalchemy.orm import sessionmaker
        from api.main import app
        from api.db import User, Base
        from api.auth import get_current_user as original_get_current_user
        
        test_engine = db_session.bind
        if test_engine is None:
            raise RuntimeError("db_session is not bound to an engine")
        
        Base.metadata.create_all(test_engine)
        from sqlalchemy import inspect
        inspector = inspect(test_engine)
        existing_tables = inspector.get_table_names()
        if 'users' not in existing_tables:
            Base.metadata.drop_all(test_engine)
            Base.metadata.create_all(test_engine)
        
        TestSessionLocal = sessionmaker(bind=test_engine, expire_on_commit=False)
        
        import api.db as db_module
        import api.main as main_module
        import api.auth as auth_module
        
        original_db_session_local = db_module.SessionLocal
        original_main_session_local = main_module.SessionLocal
        
        def get_test_session():
            return TestSessionLocal()
        
        db_module.SessionLocal = get_test_session
        main_module.SessionLocal = get_test_session
        auth_module.SessionLocal = get_test_session
        
        def make_get_test_current_user(shared_session):
            def get_test_current_user(token: Optional[str] = Header(None, alias="X-User-Token")) -> Optional[dict]:
                """get_current_user using test database"""
                if not token:
                    return None
                
                try:
                    shared_session.expire_all()
                    user = shared_session.query(User).filter(User.id == token).first()
                    if user:
                        return {
                            "id": user.id,
                            "username": user.username,
                            "role": user.role
                        }
                    return None
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).error(f"[get_test_current_user] Query failed: {e}")
                    return None
            return get_test_current_user
        
        get_test_current_user = make_get_test_current_user(db_session)
        
        app.dependency_overrides[original_get_current_user] = get_test_current_user
        
        test_client = TestClient(app)
        yield test_client
        
        app.dependency_overrides.clear()
        
        db_module.SessionLocal = original_db_session_local
        main_module.SessionLocal = original_main_session_local
    except ImportError as e:
        pytest.skip(f"langchain_openai module required: {e}")


@pytest.fixture
def sample_question(db_session):
    """Create sample question"""
    question = Question(
        question_id="TEST_Q1",
        text="Test question: Please briefly describe Python's basic data types.",
        topic="python"
    )
    db_session.add(question)
    db_session.commit()
    db_session.refresh(question)
    return question


@pytest.fixture
def sample_rubric(db_session, sample_question):
    """Create sample rubric"""
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
            "key_points": ["Data types", "Usage scenarios"],
            "common_mistakes": ["Concept confusion"]
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
    """Create sample teacher user"""
    teacher = User(id="teacher001", username="Teacher Zhang", role="teacher")
    db_session.add(teacher)
    db_session.commit()
    db_session.refresh(teacher)
    return teacher

@pytest.fixture
def sample_student(db_session):
    """Create sample student user"""
    student = User(id="student001", username="Student 1", role="student")
    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)
    return student

@pytest.fixture
def test_teacher(db_session):
    """Create test teacher user"""
    teacher = User(id="test_teacher", username="Test Teacher", role="teacher")
    db_session.add(teacher)
    db_session.commit()
    db_session.refresh(teacher)
    return teacher

@pytest.fixture
def test_student(db_session):
    """Create test student user"""
    student = User(id="test_student", username="Test Student", role="student")
    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)
    return student

@pytest.fixture
def auth_headers_student(test_student):
    """Return student authentication headers"""
    return {"X-User-Token": test_student.id}

@pytest.fixture
def auth_headers_teacher(test_teacher):
    """Return teacher authentication headers"""
    return {"X-User-Token": test_teacher.id}

@pytest.fixture
def sample_evaluation(db_session, sample_question, test_student):
    """Create sample evaluation result (using test_student to match auth_headers_student)"""
    evaluation = AnswerEvaluation(
        question_id=sample_question.question_id,
        student_id=test_student.id,
        student_answer="Python's basic data types include integers, floats, strings, etc.",
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
    """Mock LLM response data"""
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
            "Data types -> covered",
            "Usage scenarios -> partially covered"
        ],
        "improvement_recommendations": [
            "Can add more data type examples",
            "Suggest explaining application scenarios for each type"
        ]
    }
