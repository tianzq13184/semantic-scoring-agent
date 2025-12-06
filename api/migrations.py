# api/migrations.py
"""
数据库迁移脚本：将硬编码的 QUESTION_BANK 迁移到数据库
"""
from sqlalchemy.exc import IntegrityError
from .db import SessionLocal, Question, QuestionRubric, Base, engine
from .rubric_service import TOPIC_DEFAULT

# 硬编码的题目数据（从 main.py 迁移过来）
QUESTION_BANK = {
    "Q2105": {"text": "简述如何在 Airflow 中实现可靠的依赖管理与失败恢复。", "topic": "airflow"}
}


def migrate_questions():
    """迁移题目数据到数据库"""
    sess = SessionLocal()
    try:
        for q_id, q_data in QUESTION_BANK.items():
            # 检查题目是否已存在
            existing = sess.query(Question).filter(Question.question_id == q_id).first()
            if existing:
                print(f"题目 {q_id} 已存在，跳过")
                continue
            
            # 创建新题目
            question = Question(
                question_id=q_id,
                text=q_data["text"],
                topic=q_data.get("topic")
            )
            sess.add(question)
            print(f"创建题目: {q_id}")
        
        sess.commit()
        print("题目迁移完成")
    except IntegrityError as e:
        sess.rollback()
        print(f"迁移失败: {e}")
    finally:
        sess.close()


def migrate_default_rubrics():
    """迁移默认评分标准到数据库"""
    sess = SessionLocal()
    try:
        for topic, rubric_data in TOPIC_DEFAULT.items():
            # 查找该主题的所有题目
            questions = sess.query(Question).filter(Question.topic == topic).all()
            
            for question in questions:
                # 检查是否已有该版本的评分标准
                existing = sess.query(QuestionRubric).filter(
                    QuestionRubric.question_id == question.question_id,
                    QuestionRubric.version == rubric_data["version"]
                ).first()
                
                if existing:
                    print(f"题目 {question.question_id} 的评分标准 {rubric_data['version']} 已存在，跳过")
                    continue
                
                # 创建评分标准
                rubric = QuestionRubric(
                    question_id=question.question_id,
                    version=rubric_data["version"],
                    rubric_json=rubric_data,
                    is_active=True,
                    created_by="system"
                )
                sess.add(rubric)
                print(f"为题目 {question.question_id} 创建评分标准: {rubric_data['version']}")
        
        sess.commit()
        print("评分标准迁移完成")
    except Exception as e:
        sess.rollback()
        print(f"迁移失败: {e}")
    finally:
        sess.close()


def run_migrations():
    """运行所有迁移"""
    print("开始数据库迁移...")
    print("=" * 50)
    
    # 确保表已创建
    Base.metadata.create_all(engine)
    print("数据库表已创建/验证")
    print("-" * 50)
    
    # 迁移题目
    migrate_questions()
    print("-" * 50)
    
    # 迁移评分标准
    migrate_default_rubrics()
    print("-" * 50)
    
    print("所有迁移完成！")


if __name__ == "__main__":
    run_migrations()

