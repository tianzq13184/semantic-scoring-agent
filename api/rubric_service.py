from typing import Optional, Tuple
import json
import logging
from .db import SessionLocal, QuestionRubric

logger = logging.getLogger(__name__)

TOPIC_DEFAULT = {
    "airflow": {
        "version": "topic-airflow-v1",
        "dimensions": {"accuracy":1, "structure":1, "clarity":1, "business":1, "language":1},
        "key_points": [
            "DAG/Task semantics and scheduling cycles",
            "Dependencies and retry strategies",
            "Idempotency and repeatable execution",
            "Monitoring and alerting (SLAs/backfill)",
            "Resource/queue/concurrency control"
        ],
        "common_mistakes": [
            "Only discussing tools without trade-offs",
            "Ignoring dependencies and failure recovery",
            "Lacking business examples or impact"
        ]
    }
}


def load_manual_rubric(question_id: str) -> Optional[dict]:
    """Load rubric for question from database. Prioritize active rubric, otherwise return latest."""
    sess = SessionLocal()
    try:
        active_rubric = sess.query(QuestionRubric).filter(
            QuestionRubric.question_id == question_id,
            QuestionRubric.is_active == True
        ).first()
        
        if active_rubric:
            return active_rubric.rubric_json
        
        latest_rubric = sess.query(QuestionRubric).filter(
            QuestionRubric.question_id == question_id
        ).order_by(QuestionRubric.created_at.desc()).first()
        
        if latest_rubric:
            return latest_rubric.rubric_json
        
        return None
    except Exception as e:
        logger.error(f"Failed to load rubric: question_id={question_id}, error: {e}")
        return None
    finally:
        sess.close()


def generate_rubric_by_llm(question_text: str, topic: Optional[str] = None) -> dict:
    """Automatically generate rubric using LLM"""
    from .llm_client import _make_llm
    
    prompt = f"""You are an experienced educational assessment expert. Please generate a detailed rubric for the following question.

Question:
{question_text}

Topic: {topic if topic else "General"}

Please generate a JSON-formatted rubric with the following structure:
{{
  "version": "auto-gen-v1",
  "dimensions": {{
    "accuracy": 1,    // Accuracy weight (sum should be 5)
    "structure": 1,  // Structure weight
    "clarity": 1,    // Clarity weight
    "business": 1,   // Business understanding weight
    "language": 1    // Language expression weight
  }},
  "key_points": [
    "Key point 1",
    "Key point 2",
    "Key point 3"
  ],
  "common_mistakes": [
    "Common mistake 1",
    "Common mistake 2"
  ]
}}

Requirements:
1. Based on the question content, identify 3-5 key knowledge points
2. List 2-3 common mistakes students make
3. Dimension weights must sum to 5
4. Return only JSON, no other text
"""
    
    try:
        llm = _make_llm()
        resp = llm.invoke(prompt)
        text = resp.content.strip()
        
        try:
            rubric = json.loads(text)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                rubric = json.loads(json_match.group())
            else:
                raise ValueError("Unable to extract valid JSON from LLM response")
        
        if "version" not in rubric:
            rubric["version"] = "auto-gen-v1"
        
        if "dimensions" in rubric:
            total_weight = sum(rubric["dimensions"].values())
            if total_weight != 5:
                scale = 5.0 / total_weight
                rubric["dimensions"] = {k: v * scale for k, v in rubric["dimensions"].items()}
        
        return rubric
        
    except Exception as e:
        logger.error(f"LLM failed to generate rubric: {e}")
        return {
            "version": "auto-gen-v1",
            "dimensions": {"accuracy":1, "structure":1, "clarity":1, "business":1, "language":1},
            "key_points": ["Core concepts", "Implementation steps", "Common pitfalls", "Business impact"],
            "common_mistakes": ["Too general", "Lack of examples", "No trade-offs mentioned"]
        }


def save_rubric_to_db(question_id: str, rubric: dict, created_by: Optional[str] = None) -> bool:
    """Save rubric to database. If rubric with same version already exists, do not save."""
    sess = SessionLocal()
    try:
        version = rubric.get("version", "auto-gen-v1")
        
        existing = sess.query(QuestionRubric).filter(
            QuestionRubric.question_id == question_id,
            QuestionRubric.version == version
        ).first()
        
        if existing:
            return False
        
        new_rubric = QuestionRubric(
            question_id=question_id,
            version=version,
            rubric_json=rubric,
            is_active=False,
            created_by=created_by or "system"
        )
        sess.add(new_rubric)
        sess.commit()
        return True
        
    except Exception as e:
        sess.rollback()
        logger.error(f"Failed to save rubric: {question_id}, error: {e}")
        return False
    finally:
        sess.close()


def get_rubric(question_id: str, topic: str, provided: Optional[dict] = None, question_text: Optional[str] = None) -> Tuple[dict, str]:
    """Get rubric with priority fallback: user provided -> database -> topic default -> LLM auto-generated"""
    if provided:
        return provided, provided.get("version", "manual-provided")
    
    manual = load_manual_rubric(question_id)
    if manual:
        return manual, manual.get("version", "manual-v1")
    
    topic_rubric = TOPIC_DEFAULT.get(topic)
    if topic_rubric:
        return topic_rubric, topic_rubric["version"]
    
    if not question_text:
        auto = {
            "version": "auto-gen-v1",
            "dimensions": {"accuracy":1, "structure":1, "clarity":1, "business":1, "language":1},
            "key_points": ["Core concepts", "Implementation steps", "Common pitfalls", "Business impact"],
            "common_mistakes": ["Too general", "Lack of examples", "No trade-offs mentioned"]
        }
        return auto, auto["version"]
    
    auto_rubric = generate_rubric_by_llm(question_text, topic)
    save_rubric_to_db(question_id, auto_rubric, created_by="system")
    
    return auto_rubric, auto_rubric.get("version", "auto-gen-v1")
