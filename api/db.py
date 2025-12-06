# api/db.py
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Float, JSON, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import func

load_dotenv()

DATABASE_URL = os.getenv("DB_URL", "sqlite:///./answer_eval.db")
engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)
Base = declarative_base()

class AnswerEvaluation(Base):
    __tablename__ = "answer_evaluations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    question_id = Column(String, index=True)
    student_id = Column(String, nullable=True)
    student_answer = Column(Text)
    auto_score = Column(Float)
    final_score = Column(Float, nullable=True)
    dimension_scores_json = Column(JSON)
    model_version = Column(String)
    rubric_version = Column(String)
    raw_llm_output = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

def init_db():
    Base.metadata.create_all(engine)
