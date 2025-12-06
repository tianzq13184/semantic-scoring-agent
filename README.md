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

# 自动运行迁移（可选，仅开发环境）
# AUTO_MIGRATE=true
```

### 4. 初始化数据库

首次运行前，需要初始化数据库并迁移数据：

```bash
python run_migrations.py
```

这将创建所有必要的数据库表，并将硬编码的题目数据迁移到数据库中。

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

### POST `/review/save`

保存教师评分覆盖。

**请求体**：
```json
{
  "evaluation_id": 1,          // 必需：评估记录 ID
  "final_score": 8.5,          // 必需：最终评分（0-10）
  "review_notes": "答案很好",   // 可选：审核备注
  "reviewer_id": "teacher001"  // 可选：审核人 ID
}
```

**响应**：
```json
{
  "success": true,
  "message": "Review saved successfully",
  "evaluation_id": 1,
  "auto_score": 7.5,
  "final_score": 8.5
}
```

### GET `/evaluations`

查询评估结果列表。

**查询参数**：
- `question_id` (可选): 按题目 ID 筛选
- `student_id` (可选): 按学生 ID 筛选
- `limit` (可选, 默认50): 每页数量（1-100）
- `offset` (可选, 默认0): 偏移量

**响应**：
```json
{
  "total": 100,
  "items": [
    {
      "id": 1,
      "question_id": "Q2105",
      "student_id": "student001",
      "auto_score": 7.5,
      "final_score": 8.5,
      "created_at": "2024-01-01T10:00:00",
      "updated_at": "2024-01-01T11:00:00",
      "reviewer_id": "teacher001"
    }
  ]
}
```

### GET `/evaluations/{evaluation_id}`

获取评估结果详情。

**响应**：
```json
{
  "id": 1,
  "question_id": "Q2105",
  "student_id": "student001",
  "student_answer": "答案内容...",
  "auto_score": 7.5,
  "final_score": 8.5,
  "dimension_scores_json": {
    "accuracy": 1.5,
    "structure": 1.8
  },
  "model_version": "openai:gpt-4o-mini",
  "rubric_version": "topic-airflow-v1",
  "review_notes": "答案很好",
  "reviewer_id": "teacher001",
  "raw_llm_output": {},
  "created_at": "2024-01-01T10:00:00",
  "updated_at": "2024-01-01T11:00:00"
}
```

### GET `/questions`

查询题目列表。

**查询参数**：
- `topic` (可选): 按主题筛选
- `limit` (可选, 默认50): 每页数量（1-100）
- `offset` (可选, 默认0): 偏移量

**响应**：
```json
{
  "total": 10,
  "items": [
    {
      "id": 1,
      "question_id": "Q2105",
      "text": "简述如何在 Airflow 中实现可靠的依赖管理与失败恢复。",
      "topic": "airflow",
      "created_at": "2024-01-01T10:00:00",
      "updated_at": "2024-01-01T10:00:00"
    }
  ]
}
```

### GET `/questions/{question_id}`

获取题目详情。

**响应**：
```json
{
  "id": 1,
  "question_id": "Q2105",
  "text": "简述如何在 Airflow 中实现可靠的依赖管理与失败恢复。",
  "topic": "airflow",
  "created_at": "2024-01-01T10:00:00",
  "updated_at": "2024-01-01T10:00:00",
  "rubrics_count": 2,
  "evaluations_count": 15
}
```

### POST `/questions`

创建新题目。

**请求体**：
```json
{
  "question_id": "Q2106",
  "text": "题目文本",
  "topic": "airflow"
}
```

**响应**：返回创建的题目信息（格式同 GET `/questions/{question_id}`）

### PUT `/questions/{question_id}`

更新题目。

**请求体**：
```json
{
  "text": "更新后的题目文本",
  "topic": "updated-topic"
}
```

**响应**：返回更新后的题目信息

### DELETE `/questions/{question_id}`

删除题目（会级联删除关联的评分标准）。

**响应**：204 No Content

### GET `/questions/{question_id}/rubrics`

查询题目的评分标准列表。

**响应**：
```json
{
  "total": 2,
  "items": [
    {
      "id": 1,
      "question_id": "Q2105",
      "version": "topic-airflow-v1",
      "is_active": true,
      "created_by": "system",
      "created_at": "2024-01-01T10:00:00"
    }
  ]
}
```

### GET `/rubrics/{rubric_id}`

获取评分标准详情。

**响应**：
```json
{
  "id": 1,
  "question_id": "Q2105",
  "version": "topic-airflow-v1",
  "rubric_json": {
    "version": "topic-airflow-v1",
    "dimensions": {...},
    "key_points": [...],
    "common_mistakes": [...]
  },
  "is_active": true,
  "created_by": "system",
  "created_at": "2024-01-01T10:00:00"
}
```

### POST `/questions/{question_id}/rubrics`

为题目创建评分标准。

**请求体**：
```json
{
  "version": "custom-v2",
  "rubric_json": {
    "version": "custom-v2",
    "dimensions": {...},
    "key_points": [...],
    "common_mistakes": [...]
  },
  "is_active": false,
  "created_by": "teacher001"
}
```

**响应**：返回创建的评分标准详情

### PUT `/rubrics/{rubric_id}`

更新评分标准。

**请求体**：
```json
{
  "rubric_json": {...},
  "is_active": true
}
```

**响应**：返回更新后的评分标准详情

### POST `/rubrics/{rubric_id}/activate`

激活评分标准（会自动取消同题目的其他激活评分标准）。

**响应**：
```json
{
  "success": true,
  "message": "Rubric topic-airflow-v1 activated successfully",
  "rubric_id": 1,
  "question_id": "Q2105",
  "version": "topic-airflow-v1"
}
```

## 📊 数据库模型

### Question

题目表，包含以下字段：
- `id`: 主键
- `question_id`: 题目唯一标识（如 "Q2105"）
- `text`: 题目文本
- `topic`: 题目主题（如 "airflow"）
- `created_at`: 创建时间
- `updated_at`: 更新时间

### QuestionRubric

评分标准表，包含以下字段：
- `id`: 主键
- `question_id`: 关联题目ID（外键）
- `version`: 评分标准版本
- `rubric_json`: 评分标准JSON（包含dimensions, key_points, common_mistakes等）
- `is_active`: 是否激活
- `created_by`: 创建者
- `created_at`: 创建时间

### AnswerEvaluation

评估结果表，包含以下字段：
- `id`: 主键
- `question_id`: 题目 ID（外键）
- `student_id`: 学生 ID（可选）
- `student_answer`: 学生答案
- `auto_score`: 自动评分（0-10）
- `final_score`: 最终评分（可选，用于教师覆盖）
- `dimension_scores_json`: 维度评分 JSON
- `model_version`: 使用的模型版本
- `rubric_version`: 使用的评分标准版本
- `raw_llm_output`: 原始 LLM 输出
- `reviewer_id`: 审核教师ID（可选）
- `review_notes`: 审核备注（可选）
- `created_at`: 创建时间
- `updated_at`: 更新时间

## 🎯 评分标准（Rubric）

系统支持四种评分标准来源（按优先级自动选择）：

1. **用户提供的 JSON**：通过 API 请求中的 `rubric_json` 传入
2. **数据库中的评分标准**：从 `question_rubrics` 表加载（优先使用激活的评分标准）
3. **主题默认评分标准**：基于题目主题的默认标准（如 `airflow` 主题）
4. **LLM 自动生成**：如果以上都不存在，系统会使用 LLM 自动生成评分标准并保存到数据库

### 评分标准回退逻辑

```
用户提供 → 数据库查询 → 主题默认 → LLM 自动生成
```

系统会自动选择最合适的评分标准，确保每次评估都有可用的评分依据。

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
  }, b v
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

### 已完成 ✅
- [x] 实现教师评分覆盖功能（`/review/save` 接口）
- [x] 支持从数据库加载题目特定的评分标准
- [x] 实现评估结果查询接口（`/evaluations`）
- [x] 完善教师审核 UI 界面

### 已完成 ✅
- [x] 题目管理接口（CRUD）

### 计划中 📋
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

