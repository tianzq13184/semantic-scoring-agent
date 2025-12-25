# api/migrations.py
"""
Database migration script: migrate hardcoded QUESTION_BANK to database
"""
from sqlalchemy.exc import IntegrityError
from .db import SessionLocal, Question, QuestionRubric, Base, engine
from .rubric_service import TOPIC_DEFAULT

# Hardcoded question data (migrated from main.py)
QUESTION_BANK = {
    "Q2105": {"text": "Briefly describe how to implement reliable dependency management and failure recovery in Airflow.", "topic": "airflow"}
}


def migrate_questions():
    """Migrate question data to database"""
    sess = SessionLocal()
    try:
        for q_id, q_data in QUESTION_BANK.items():
            existing = sess.query(Question).filter(Question.question_id == q_id).first()
            if existing:
                print(f"Question {q_id} already exists, skipping")
                continue
            question = Question(
                question_id=q_id,
                text=q_data["text"],
                topic=q_data.get("topic")
            )
            sess.add(question)
            print(f"Created question: {q_id}")
        
        sess.commit()
        print("Question migration completed")
    except IntegrityError as e:
        sess.rollback()
        print(f"Migration failed: {e}")
    finally:
        sess.close()


def migrate_default_rubrics():
    """Migrate default rubrics to database"""
    sess = SessionLocal()
    try:
        for topic, rubric_data in TOPIC_DEFAULT.items():
            questions = sess.query(Question).filter(Question.topic == topic).all()
            
            for question in questions:
                existing = sess.query(QuestionRubric).filter(
                    QuestionRubric.question_id == question.question_id,
                    QuestionRubric.version == rubric_data["version"]
                ).first()
                
                if existing:
                    print(f"Rubric {rubric_data['version']} for question {question.question_id} already exists, skipping")
                    continue
                rubric = QuestionRubric(
                    question_id=question.question_id,
                    version=rubric_data["version"],
                    rubric_json=rubric_data,
                    is_active=True,
                    created_by="system"
                )
                sess.add(rubric)
                print(f"Created rubric {rubric_data['version']} for question {question.question_id}")
        
        sess.commit()
        print("Rubric migration completed")
    except Exception as e:
        sess.rollback()
        print(f"Migration failed: {e}")
    finally:
        sess.close()


def run_migrations():
    """Run all migrations"""
    print("Starting database migration...")
    print("=" * 50)
    
    Base.metadata.create_all(engine)
    print("Database tables created/verified")
    print("-" * 50)
    
    migrate_questions()
    print("-" * 50)
    
    migrate_default_rubrics()
    print("-" * 50)
    
    print("All migrations completed!")


if __name__ == "__main__":
    run_migrations()

