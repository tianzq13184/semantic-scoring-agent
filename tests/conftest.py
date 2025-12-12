"""
Pytest configuration and shared fixtures
"""
import pytest
import os
import sys
import logging

# 配置测试环境的日志级别
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# 设置测试环境变量（必须在导入之前）
# 测试环境使用 MySQL 数据库
# 注意：密码中的 @ 需要 URL 编码为 %40
os.environ["DB_URL"] = "mysql+pymysql://root:Drillinsight%402099@mysql-tcs.drillinsight.com:3306/semantic_scoring_test"
os.environ["OPENAI_API_KEY"] = "test-key"  # Mock key for testing

# 延迟导入，避免在测试时加载 langchain_openai
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.db import Base, Question, QuestionRubric, AnswerEvaluation, User


@pytest.fixture(scope="function")
def db_session():
    """创建测试数据库会话"""
    # 使用 MySQL 数据库
    # 数据库信息：mysql-tcs.drillinsight.com:3306, root, Drillinsight@2099
    # 测试数据库名：semantic_scoring_test
    import pymysql
    pymysql.install_as_MySQLdb()
    
    # 测试数据库连接字符串
    # 注意：密码中的 @ 需要 URL 编码为 %40
    test_db_url = "mysql+pymysql://root:Drillinsight%402099@mysql-tcs.drillinsight.com:3306/semantic_scoring_test"
    
    # 创建 engine，设置连接超时和池大小
    # 测试环境需要足够的连接池大小，避免连接竞争导致阻塞
    # 问题：pool_size=1 时，db_session 占用连接后，_get_question 无法获取新连接
    engine = create_engine(
        test_db_url, 
        echo=False, 
        pool_pre_ping=True,
        pool_size=5,  # 增加连接池大小，避免连接竞争
        max_overflow=2,  # 允许少量溢出连接
        pool_recycle=3600,  # 1小时后回收连接
        pool_timeout=5,  # 5秒获取连接超时，避免无限等待
        connect_args={'connect_timeout': 3}  # 3秒连接超时，快速失败
    )
    
    # 创建所有表
    Base.metadata.create_all(engine)
    
    TestingSessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    
    session = TestingSessionLocal()
    
    # 在每个测试前清理数据（按依赖顺序删除）
    def cleanup_data():
        try:
            # 禁用外键检查（MySQL 特有），这样可以按任意顺序删除
            from sqlalchemy import text
            session.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
            # 删除所有数据
            session.query(AnswerEvaluation).delete()
            session.query(QuestionRubric).delete()
            session.query(Question).delete()
            session.query(User).delete()
            # 重新启用外键检查
            session.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
            session.commit()
        except Exception as e:
            session.rollback()
            try:
                session.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
                session.commit()
            except:
                pass
    
    # 测试前清理
    cleanup_data()
    
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        # 测试结束后再次清理数据
        cleanup_data()
        session.close()


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
        
        # 获取测试数据库的 engine（与 db_session 使用同一个 engine）
        # 关键：db_session.bind 返回创建 db_session 的 engine
        # 我们必须使用这个相同的 engine，这样它们才能共享同一个内存数据库
        test_engine = db_session.bind
        if test_engine is None:
            # 如果 bind 为 None，说明 db_session 还没有绑定到 engine
            # 这种情况下，我们需要从 db_session 的类中获取 engine
            # 但更好的方法是确保 db_session 已经绑定
            raise RuntimeError("db_session is not bound to an engine")
        
        # 确保表已创建（包括 User 表）
        # db_session fixture 已经创建了所有表，这里再次确保
        Base.metadata.create_all(test_engine)
        # 验证 users 表是否存在
        from sqlalchemy import inspect
        inspector = inspect(test_engine)
        existing_tables = inspector.get_table_names()
        if 'users' not in existing_tables:
            # 如果 users 表不存在，重新创建所有表
            Base.metadata.drop_all(test_engine)
            Base.metadata.create_all(test_engine)
        
        # 创建 TestSessionLocal，使用与 db_session 相同的 engine
        # 这确保了它们共享同一个内存数据库
        TestSessionLocal = sessionmaker(bind=test_engine, expire_on_commit=False)
        
        # 覆盖 api.main 和 api.auth 中的 SessionLocal
        import api.db as db_module
        import api.main as main_module
        import api.auth as auth_module
        
        # 保存原始值
        original_db_session_local = db_module.SessionLocal
        original_main_session_local = main_module.SessionLocal
        
        # 创建一个函数来返回测试会话
        # 注意：对于 MySQL，创建新连接可能导致连接池阻塞
        # 我们使用一个共享的 session 工厂，但限制连接数
        def get_test_session():
            # 使用 TestSessionLocal 创建新会话
            # 注意：如果连接池已满，这里可能会阻塞
            return TestSessionLocal()
        
        # 覆盖 SessionLocal - 确保所有模块都使用测试数据库
        db_module.SessionLocal = get_test_session
        main_module.SessionLocal = get_test_session
        # 重要：直接覆盖 auth 模块中的 SessionLocal
        auth_module.SessionLocal = get_test_session
        
        # 为了调试，记录 SessionLocal 覆盖情况
        import logging
        test_logger = logging.getLogger(__name__)
        test_logger.debug(f"[client fixture] SessionLocal已覆盖: main_module.SessionLocal={main_module.SessionLocal}")
        
        # 创建一个使用测试数据库的 get_current_user
        # 关键：必须使用与 db_session 相同的 engine
        # 对于 MySQL，使用 TestSessionLocal 创建新会话可以避免连接问题
        def make_get_test_current_user(shared_session):
            def get_test_current_user(token: Optional[str] = Header(None, alias="X-User-Token")) -> Optional[dict]:
                """使用测试数据库的 get_current_user"""
                if not token:
                    return None
                
                # 直接使用共享的 db_session 查询，避免创建新连接导致超时
                # 这样可以确保使用同一个数据库连接，看到相同的数据
                try:
                    # 刷新会话以确保看到最新数据
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
                    # 如果查询失败，返回 None
                    # 在生产环境中应该记录日志
                    import logging
                    logging.getLogger(__name__).error(f"[get_test_current_user] 查询失败: {e}")
                    return None
            return get_test_current_user
        
        get_test_current_user = make_get_test_current_user(db_session)
        
        # 使用 FastAPI 的依赖覆盖 - 覆盖 get_current_user 函数本身
        # 这也会自动覆盖所有依赖 get_current_user 的函数（如 require_role）
        app.dependency_overrides[original_get_current_user] = get_test_current_user
        
        # 验证覆盖是否成功
        # 注意：FastAPI 的依赖覆盖是递归的，所以覆盖 get_current_user 也会影响 require_role
        
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
def sample_evaluation(db_session, sample_question, test_student):
    """创建示例评估结果（使用test_student，以便与auth_headers_student匹配）"""
    evaluation = AnswerEvaluation(
        question_id=sample_question.question_id,
        student_id=test_student.id,
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
