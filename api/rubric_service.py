from typing import Optional, Tuple
import json

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
    # MVP：先不接DB，留个钩子
    return None

def get_rubric(question_id: str, topic: str, provided: Optional[dict]) -> Tuple[dict, str]:
    if provided:
        return provided, provided.get("version","manual-provided")
    manual = load_manual_rubric(question_id)
    if manual:
        return manual, manual.get("version","manual-v1")
    topic_rubric = TOPIC_DEFAULT.get(topic)
    if topic_rubric:
        return topic_rubric, topic_rubric["version"]
    # 动态生成（MVP 先用 topic-agnostic 的模板）
    auto = {
        "version":"auto-gen-v1",
        "dimensions":{"accuracy":1,"structure":1,"clarity":1,"business":1,"language":1},
        "key_points":["核心概念","实现步骤","常见坑","业务影响"],
        "common_mistakes":["泛泛而谈","缺少例子","未提trade-off"]
    }
    return auto, auto["version"]
