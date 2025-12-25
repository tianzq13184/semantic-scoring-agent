# api/db.py
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Float, JSON, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.sql import func

load_dotenv()

DATABASE_URL = os.getenv("DB_URL", "sqlite:///./answer_eval.db")
engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)
Base = declarative_base()


class User(Base):
    """User table"""
    __tablename__ = "users"
    id = Column(String(100), primary_key=True)
    username = Column(String(200), nullable=False, index=True)
    role = Column(String(50), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    evaluations = relationship("AnswerEvaluation", back_populates="user", foreign_keys="AnswerEvaluation.student_id")


class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    question_id = Column(String(100), unique=True, index=True, nullable=False)
    text = Column(Text, nullable=False)
    topic = Column(String(200), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    rubrics = relationship("QuestionRubric", back_populates="question", cascade="all, delete-orphan")
    evaluations = relationship("AnswerEvaluation", back_populates="question")


class QuestionRubric(Base):
    __tablename__ = "question_rubrics"
    id = Column(Integer, primary_key=True, autoincrement=True)
    question_id = Column(String(100), ForeignKey("questions.question_id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(String(50), nullable=False)
    rubric_json = Column(JSON, nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    question = relationship("Question", back_populates="rubrics")


class AnswerEvaluation(Base):
    __tablename__ = "answer_evaluations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    question_id = Column(String(100), ForeignKey("questions.question_id", ondelete="SET NULL"), index=True)
    student_id = Column(String(100), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    student_answer = Column(Text)
    auto_score = Column(Float)
    final_score = Column(Float, nullable=True)
    dimension_scores_json = Column(JSON)
    model_version = Column(String(50))
    rubric_version = Column(String(50))
    raw_llm_output = Column(JSON)
    reviewer_id = Column(String(100), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    review_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    question = relationship("Question", back_populates="evaluations")
    user = relationship("User", foreign_keys=[student_id], back_populates="evaluations")


def init_db():
    Base.metadata.create_all(engine)
