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
    """用户表"""
    __tablename__ = "users"
    id = Column(String, primary_key=True)  # 用户ID（可以是学号、工号等）
    username = Column(String, nullable=False, index=True)
    role = Column(String, nullable=False, index=True)  # "student" 或 "teacher"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    evaluations = relationship("AnswerEvaluation", back_populates="user", foreign_keys="AnswerEvaluation.student_id")


class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    question_id = Column(String, unique=True, index=True, nullable=False)
    text = Column(Text, nullable=False)
    topic = Column(String, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    rubrics = relationship("QuestionRubric", back_populates="question", cascade="all, delete-orphan")
    evaluations = relationship("AnswerEvaluation", back_populates="question")


class QuestionRubric(Base):
    __tablename__ = "question_rubrics"
    id = Column(Integer, primary_key=True, autoincrement=True)
    question_id = Column(String, ForeignKey("questions.question_id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(String, nullable=False)
    rubric_json = Column(JSON, nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    question = relationship("Question", back_populates="rubrics")


class AnswerEvaluation(Base):
    __tablename__ = "answer_evaluations"
    id = Column(Integer, primary_key=True, autoincrement=True)
    question_id = Column(String, ForeignKey("questions.question_id", ondelete="SET NULL"), index=True)
    student_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    student_answer = Column(Text)
    auto_score = Column(Float)
    final_score = Column(Float, nullable=True)
    dimension_scores_json = Column(JSON)
    model_version = Column(String)
    rubric_version = Column(String)
    raw_llm_output = Column(JSON)
    reviewer_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    review_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    question = relationship("Question", back_populates="evaluations")
    user = relationship("User", foreign_keys=[student_id], back_populates="evaluations")


def init_db():
    Base.metadata.create_all(engine)
