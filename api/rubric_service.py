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
            "DAG/Task 语义与调度周期",
            "依赖与重试策略",
            "Idempotency 与可重复运行",
            "监控与告警（SLAs/回填）",
            "资源/队列/并发控制"
        ],
        "common_mistakes": [
            "只谈工具不谈trade-off",
            "忽略依赖与失败恢复",
            "缺少业务例子或影响"
        ]
    }
}


def load_manual_rubric(question_id: str) -> Optional[dict]:
    """
    从数据库加载题目的评分标准
    
    优先返回激活的评分标准，如果没有激活的则返回最新的
    """
    sess = SessionLocal()
    try:
        # 优先查找激活的评分标准
        active_rubric = sess.query(QuestionRubric).filter(
            QuestionRubric.question_id == question_id,
            QuestionRubric.is_active == True
        ).first()
        
        if active_rubric:
            logger.info(f"从数据库加载激活的评分标准: {question_id} -> {active_rubric.version}")
            return active_rubric.rubric_json
        
        # 如果没有激活的，查找最新的评分标准
        latest_rubric = sess.query(QuestionRubric).filter(
            QuestionRubric.question_id == question_id
        ).order_by(QuestionRubric.created_at.desc()).first()
        
        if latest_rubric:
            logger.info(f"从数据库加载最新的评分标准: {question_id} -> {latest_rubric.version}")
            return latest_rubric.rubric_json
        
        return None
    except Exception as e:
        logger.error(f"加载评分标准失败: {question_id}, 错误: {e}")
        return None
    finally:
        sess.close()


def generate_rubric_by_llm(question_text: str, topic: Optional[str] = None) -> dict:
    """
    使用 LLM 自动生成评分标准
    
    返回格式化的 rubric dict
    """
    from .llm_client import _make_llm
    
    prompt = f"""你是一位经验丰富的教育评估专家。请为以下题目生成一个详细的评分标准（rubric）。

题目：
{question_text}

主题：{topic if topic else "通用"}

请生成一个包含以下结构的 JSON 格式评分标准：
{{
  "version": "auto-gen-v1",
  "dimensions": {{
    "accuracy": 1,    // 准确性权重（总和应为5）
    "structure": 1,  // 结构权重
    "clarity": 1,    // 清晰度权重
    "business": 1,   // 业务理解权重
    "language": 1    // 语言表达权重
  }},
  "key_points": [
    "关键知识点1",
    "关键知识点2",
    "关键知识点3"
  ],
  "common_mistakes": [
    "常见错误1",
    "常见错误2"
  ]
}}

要求：
1. 根据题目内容，识别3-5个关键知识点
2. 列出2-3个学生常见的错误
3. 维度权重总和必须等于5
4. 只返回 JSON，不要其他文字
"""
    
    try:
        llm = _make_llm()
        resp = llm.invoke(prompt)
        text = resp.content.strip()
        
        # 尝试解析 JSON
        try:
            rubric = json.loads(text)
        except json.JSONDecodeError:
            # 如果直接解析失败，尝试提取 JSON 部分
            import re
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                rubric = json.loads(json_match.group())
            else:
                raise ValueError("无法从 LLM 响应中提取有效的 JSON")
        
        # 验证和规范化
        if "version" not in rubric:
            rubric["version"] = "auto-gen-v1"
        
        # 确保维度权重总和为5
        if "dimensions" in rubric:
            total_weight = sum(rubric["dimensions"].values())
            if total_weight != 5:
                # 按比例调整
                scale = 5.0 / total_weight
                rubric["dimensions"] = {k: v * scale for k, v in rubric["dimensions"].items()}
        
        logger.info(f"LLM 成功生成评分标准，版本: {rubric.get('version')}")
        return rubric
        
    except Exception as e:
        logger.error(f"LLM 生成评分标准失败: {e}")
        # 返回默认模板
        return {
            "version": "auto-gen-v1",
            "dimensions": {"accuracy":1, "structure":1, "clarity":1, "business":1, "language":1},
            "key_points": ["核心概念", "实现步骤", "常见坑", "业务影响"],
            "common_mistakes": ["泛泛而谈", "缺少例子", "未提trade-off"]
        }


def save_rubric_to_db(question_id: str, rubric: dict, created_by: Optional[str] = None) -> bool:
    """
    将评分标准保存到数据库
    
    如果已存在相同版本的评分标准，则不保存
    """
    sess = SessionLocal()
    try:
        version = rubric.get("version", "auto-gen-v1")
        
        # 检查是否已存在
        existing = sess.query(QuestionRubric).filter(
            QuestionRubric.question_id == question_id,
            QuestionRubric.version == version
        ).first()
        
        if existing:
            logger.info(f"评分标准已存在: {question_id} -> {version}")
            return False
        
        # 创建新的评分标准
        new_rubric = QuestionRubric(
            question_id=question_id,
            version=version,
            rubric_json=rubric,
            is_active=False,  # 自动生成的默认不激活
            created_by=created_by or "system"
        )
        sess.add(new_rubric)
        sess.commit()
        
        logger.info(f"评分标准已保存到数据库: {question_id} -> {version}")
        return True
        
    except Exception as e:
        sess.rollback()
        logger.error(f"保存评分标准失败: {question_id}, 错误: {e}")
        return False
    finally:
        sess.close()


def get_rubric(question_id: str, topic: str, provided: Optional[dict] = None, question_text: Optional[str] = None) -> Tuple[dict, str]:
    """
    获取评分标准，按优先级回退：
    1. 用户提供的 (provided)
    2. 数据库中的 (load_manual_rubric)
    3. 主题默认的 (TOPIC_DEFAULT)
    4. LLM 自动生成的 (generate_rubric_by_llm)
    
    如果使用 LLM 生成，会自动保存到数据库
    """
    # 优先级1: 用户提供的
    if provided:
        logger.info(f"使用用户提供的评分标准: {question_id}")
        return provided, provided.get("version", "manual-provided")
    
    # 优先级2: 从数据库加载
    manual = load_manual_rubric(question_id)
    if manual:
        return manual, manual.get("version", "manual-v1")
    
    # 优先级3: 主题默认
    topic_rubric = TOPIC_DEFAULT.get(topic)
    if topic_rubric:
        logger.info(f"使用主题默认评分标准: {question_id} -> {topic}")
        return topic_rubric, topic_rubric["version"]
    
    # 优先级4: LLM 自动生成
    logger.info(f"使用 LLM 自动生成评分标准: {question_id}")
    if not question_text:
        # 如果没有提供题目文本，使用通用模板
        auto = {
            "version": "auto-gen-v1",
            "dimensions": {"accuracy":1, "structure":1, "clarity":1, "business":1, "language":1},
            "key_points": ["核心概念", "实现步骤", "常见坑", "业务影响"],
            "common_mistakes": ["泛泛而谈", "缺少例子", "未提trade-off"]
        }
        return auto, auto["version"]
    
    # 使用 LLM 生成
    auto_rubric = generate_rubric_by_llm(question_text, topic)
    
    # 保存到数据库
    save_rubric_to_db(question_id, auto_rubric, created_by="system")
    
    return auto_rubric, auto_rubric.get("version", "auto-gen-v1")
