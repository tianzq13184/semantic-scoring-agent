# Semantic Scoring Agent

一个基于大语言模型（LLM）的智能答案评估系统，用于自动评估学生的短答案题目，提供多维度评分和改进建议。

## 📋 项目简介

Semantic Scoring Agent 是一个教育评估工具，通过 LLM 对学生的短答案进行自动化评分。系统支持：
- 多维度评分（准确性、结构、清晰度、业务理解、语言表达）
- 关键点评估
- 改进建议生成
- 评估结果持久化存储
- 灵活的评分标准（Rubric）配置

## ✨ 功能特性

- 🤖 **智能评分**：使用 LLM 对答案进行多维度自动评分（0-10分）
- 📊 **维度分析**：提供准确性、结构、清晰度、业务理解、语言表达等维度的详细评分
- 🎯 **关键点检查**：自动识别答案是否覆盖了关键知识点
- 💡 **改进建议**：生成具体的、可操作的改进建议
- 📝 **自定义评分标准**：支持通过 JSON 配置自定义评分标准
- 💾 **结果存储**：所有评估结果自动保存到数据库
- 🌐 **Web UI**：提供友好的 Streamlit 界面
- 🔌 **RESTful API**：提供 FastAPI 后端接口

## 🛠️ 技术栈

- **后端框架**：FastAPI
- **前端框架**：Streamlit
- **LLM 集成**：LangChain + OpenAI/OpenRouter
- **数据库**：SQLite（可配置为其他数据库）
- **ORM**：SQLAlchemy
- **数据验证**：Pydantic
- **Python 版本**：3.8+

## 📦 安装

### 1. 克隆项目

```bash
git clone <repository-url>
cd semantic-scoring-agent
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 环境配置

创建 `.env` 文件并配置以下环境变量：

```env
# LLM 配置（必需）
OPENAI_API_KEY=your_api_key_here

# 可选：使用 OpenRouter
# OPENROUTER_API_KEY=your_openrouter_key
# OPENAI_BASE_URL=https://openrouter.ai/api/v1
# LLM_PROVIDER=openrouter

# 模型配置（可选，默认使用 gpt-4o-mini）
MODEL_ID=gpt-4o-mini
# 或
MODEL_NAME=gpt-4o-mini

# 数据库配置（可选，默认使用 SQLite）
DB_URL=sqlite:///./answer_eval.db

# API 基础 URL（UI 使用，可选）
API_BASE=http://127.0.0.1:8000
```

## 🚀 使用方法

### 启动后端 API

```bash
cd api
uvicorn main:app --reload --port 8000
```

API 文档将自动生成在：http://127.0.0.1:8000/docs

### 启动前端 UI

```bash
cd ui
streamlit run app.py
```

UI 将在浏览器中自动打开，默认地址：http://localhost:8501

### 使用 API

#### 评估答案

```bash
curl -X POST "http://127.0.0.1:8000/evaluate/short-answer" \
  -H "Content-Type: application/json" \
  -d '{
    "question_id": "Q2105",
    "student_answer": "在 Airflow 中，我可以通过定义 DAG 来管理任务依赖关系，使用 retry 参数处理失败情况..."
  }'
```

#### 使用自定义评分标准

```bash
curl -X POST "http://127.0.0.1:8000/evaluate/short-answer" \
  -H "Content-Type: application/json" \
  -d '{
    "question_id": "Q2105",
    "student_answer": "你的答案...",
    "rubric_json": {
      "version": "custom-v1",
      "dimensions": {
        "accuracy": 1,
        "structure": 1,
        "clarity": 1
      },
      "key_points": ["关键点1", "关键点2"],
      "common_mistakes": ["常见错误1"]
    }
  }'
```

## 📁 项目结构

```
semantic-scoring-agent/
├── api/                    # 后端 API
│   ├── __init__.py
│   ├── main.py            # FastAPI 应用入口
│   ├── models.py          # Pydantic 数据模型
│   ├── db.py              # 数据库配置和模型
│   ├── llm_client.py      # LLM 客户端封装
│   └── rubric_service.py  # 评分标准服务
├── ui/                    # 前端 UI
│   └── app.py             # Streamlit 应用
├── docs/                  # 文档
│   └── PRD.md            # 产品需求文档
├── requirements.txt       # Python 依赖
├── answer_eval.db        # SQLite 数据库（自动生成）
└── README.md             # 项目说明文档
```

## 🔌 API 文档

### POST `/evaluate/short-answer`

评估学生的短答案。

**请求体**：
```json
{
  "question_id": "string",      // 必需：题目 ID
  "student_answer": "string",   // 必需：学生答案（10-4000 字符）
  "with_rubric": false,         // 可选：是否使用自定义评分标准
  "rubric_json": {}             // 可选：自定义评分标准 JSON
}
```

**响应**：
```json
{
  "question_id": "Q2105",
  "rubric_version": "topic-airflow-v1",
  "provider": "openai",
  "model_id": "gpt-4o-mini",
  "model_version": "openai:gpt-4o-mini",
  "total_score": 7.5,
  "dimension_breakdown": {
    "accuracy": 1.5,
    "structure": 1.8,
    "clarity": 1.6,
    "business": 1.4,
    "language": 1.2
  },
  "key_points_evaluation": [
    "DAG/Task 语义与调度周期 -> covered",
    "依赖与重试策略 -> partially covered"
  ],
  "improvement_recommendations": [
    "建议1",
    "建议2"
  ],
  "raw_llm_output": {}
}
```

## 📊 数据库模型

### AnswerEvaluation

评估结果表，包含以下字段：
- `id`: 主键
- `question_id`: 题目 ID
- `student_id`: 学生 ID（可选）
- `student_answer`: 学生答案
- `auto_score`: 自动评分（0-10）
- `final_score`: 最终评分（可选，用于教师覆盖）
- `dimension_scores_json`: 维度评分 JSON
- `model_version`: 使用的模型版本
- `rubric_version`: 使用的评分标准版本
- `raw_llm_output`: 原始 LLM 输出
- `created_at`: 创建时间

## 🎯 评分标准（Rubric）

系统支持三种评分标准来源（按优先级）：
1. **用户提供的 JSON**：通过 API 请求中的 `rubric_json` 传入
2. **题目特定的评分标准**：从数据库加载（待实现）
3. **主题默认评分标准**：基于题目主题的默认标准
4. **自动生成**：如果以上都不存在，使用通用模板

### 评分标准格式

```json
{
  "version": "topic-airflow-v1",
  "dimensions": {
    "accuracy": 1,
    "structure": 1,
    "clarity": 1,
    "business": 1,
    "language": 1
  },
  "key_points": [
    "关键点1",
    "关键点2"
  ],
  "common_mistakes": [
    "常见错误1",
    "常见错误2"
  ]
}
```

## 🔧 配置说明

### LLM 提供商

系统支持多种 LLM 提供商：

1. **OpenAI**（默认）：
   ```env
   OPENAI_API_KEY=sk-...
   MODEL_ID=gpt-4o-mini
   ```

2. **OpenRouter**：
   ```env
   OPENAI_BASE_URL=https://openrouter.ai/api/v1
   OPENAI_API_KEY=sk-or-...
   OPENROUTER_REFERER=https://your-site.com
   OPENROUTER_TITLE=Your App Name
   ```

3. **自定义 OpenAI 兼容 API**：
   ```env
   OPENAI_BASE_URL=https://your-api.com/v1
   OPENAI_API_KEY=your-key
   ```

## 📝 开发计划

- [ ] 实现教师评分覆盖功能（`/review/save` 接口）
- [ ] 支持从数据库加载题目特定的评分标准
- [ ] 添加更多题目示例
- [ ] 支持批量评估
- [ ] 添加评估结果统计和分析功能
- [ ] 支持多语言

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

[待添加]

## 👥 作者

[待添加]

