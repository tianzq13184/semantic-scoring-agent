# 产品需求文档（PRD）

## 1. 产品背景（Background）

目前教师在批改简答题时存在效率低、主观性强、难以复盘的问题。

目标是通过一个基于 LLM 的「题目打分 Agent」系统，自动完成评分、生成可解释结果、支持人工复核与持续优化，实现从人工打分 → 半自动 → 智能化评分的闭环。

---

## 2. 产品目标（Objectives）

- **提升效率**：自动化评分流程，减少教师批改时间
- **提高一致性**：基于标准化评分标准，减少主观性差异
- **可追溯性**：完整记录评分过程，支持复盘和优化
- **持续改进**：通过教师反馈优化评分标准

---

## 3. 系统架构（Architecture Overview）

```
POST /evaluate/short-answer
  → Rubric Service
  → Scoring Agent (LLM + Rule Engine)
  → Persistence Layer
  → Teacher Review Layer (optional)
```

### 分层架构：

1. **API 层**：接收"题目+答案"请求
2. **Rubric 层**：查找/生成评分标准
3. **Scoring Agent 层**：LLM 一次推理输出维度化评分
4. **Persistence 层**：存储评分全过程
5. **Teacher Review 层**：教师查看与修订分数

---

## 4. 模块设计（Modules）

### 4.1 API / Service 层

**接口：**

`POST /evaluate/short-answer`

**请求体：**

```json
{
  "question_id": "Q2105",
  "student_answer": "I will use Airflow to schedule jobs...",
  "with_rubric": false
}
```

**返回：**

包含 `total_score`, `dimension_breakdown`, `improvements`, `rubric_version`, `model_version`。

---

### 4.2 Rubric Service

**职责：**

1. 优先从数据库查询人工或历史 rubric
2. 若无则查默认模板
3. 若仍无则由 LLM 动态生成并存库

**回退逻辑：**

```
rubric_table → topic_default_rubric → LLM auto_generate
```

**生成 prompt：**

给定题目 `topic=airflow`，请拆分 3-5 个 key points，每点给权重(总和=1.0)，附常见错误。输出 JSON。

---

### 4.3 Scoring / Agent 层

**目标：** 一次 LLM 调用完成所有维度打分。

**Prompt 结构：**

1. Role & Task
2. Context（题目+rubric+学生答案+维度）
3. Output contract（JSON schema）

**示例输出：**

```json
{
  "total_score": 8.5,
  "dimension_breakdown": {
    "accuracy": 2,
    "structure": 1.5,
    "clarity": 1.5,
    "business": 2,
    "language": 1.5
  },
  "key_points_evaluation": [
    {"point": "DAG scheduling", "status": "covered"},
    {"point": "dependencies", "status": "missing"}
  ],
  "improvement_recommendations": [
    "Add explanation of dependency management",
    "Clarify Airflow DAG retry logic"
  ]
}
```

**稳定性措施：**

- JSON Schema 校验 + 自动重试
- 规则兜底（rubric 关键字判分）
- LLM 负责语义判断，不直接决策最终分数

---

### 4.4 Persistence 层

**存储字段：**

- 题目ID、学生ID、答案文本
- 自动评分（auto_score）
- 最终评分（final_score，教师覆盖）
- 维度评分JSON
- 模型版本、评分标准版本
- 原始LLM输出
- 创建时间、更新时间

---

### 4.5 Teacher Review 层

**功能：**

- 展示题目、答案、LLM评分
- 教师修改 `final_score`、添加备注
- 保留 `auto_score` 与 `final_score`
- 后续支持 rubric 修订建议自动回流

**接口：**

`POST /review/save` - 保存教师评分覆盖

---

## 5. 数据结构设计（Database Schema）

### questions

存储题目信息：

- `id`: 主键
- `question_id`: 题目唯一标识（如 "Q2105"）
- `text`: 题目文本
- `topic`: 题目主题（如 "airflow"）
- `created_at`: 创建时间
- `updated_at`: 更新时间

### question_rubrics

存储评分标准：

- `id`: 主键
- `question_id`: 关联题目ID
- `version`: 评分标准版本
- `rubric_json`: 评分标准JSON（包含dimensions, key_points, common_mistakes等）
- `is_active`: 是否激活
- `created_by`: 创建者
- `created_at`: 创建时间

### answer_evaluations

存储评估结果：

- `id`: 主键
- `question_id`: 题目ID
- `student_id`: 学生ID（可选）
- `student_answer`: 学生答案
- `auto_score`: 自动评分（0-10）
- `final_score`: 最终评分（教师覆盖，可选）
- `dimension_scores_json`: 维度评分JSON
- `model_version`: 使用的模型版本
- `rubric_version`: 使用的评分标准版本
- `raw_llm_output`: 原始LLM输出
- `reviewer_id`: 审核教师ID（可选）
- `review_notes`: 审核备注（可选）
- `created_at`: 创建时间
- `updated_at`: 更新时间

---

## 6. 技术方案（Tech Stack）

- **后端框架**：FastAPI
- **前端框架**：Streamlit（MVP阶段），后续可迁移到 React/Vue
- **LLM 集成**：LangChain + OpenAI/OpenRouter
- **数据库**：SQLite（开发）→ PostgreSQL（生产）
- **ORM**：SQLAlchemy
- **数据验证**：Pydantic

---

## 8. 开发计划（Milestones）

### Phase 1: MVP（当前阶段）✅
- [x] 基础API接口
- [x] LLM评分Agent
- [x] 基础数据持久化
- [x] 简单UI界面

### Phase 2: 数据模型完善 ✅
- [x] 实现 `questions` 表
- [x] 实现 `question_rubrics` 表
- [x] 完善 Rubric Service 数据库查询
- [x] 数据迁移脚本

### Phase 2.3: 题目管理接口 ✅
- [x] 题目 CRUD 接口
- [x] 评分标准管理接口

### Phase 3: 教师审核功能 ✅
- [x] `POST /review/save` 接口
- [x] 教师审核UI界面
- [x] 评估结果列表查询接口
- [x] 评分对比展示（auto_score vs final_score）

### Phase 4: 高级功能
- [ ] 审计日志
- [ ] Rubric 自动优化建议
- [ ] 批量评估接口
- [ ] 统计分析Dashboard

---

## 9. 成功指标（Success Metrics）

- **效率提升**：教师批改时间减少 60%+
- **一致性**：同一答案评分标准差 < 0.5
- **准确性**：自动评分与教师评分相关性 > 0.85
- **用户满意度**：教师满意度 > 4.0/5.0

---

## 10. 风险与对策（Risks & Mitigations）

| 风险 | 影响 | 对策 |
|------|------|------|
| LLM 输出不稳定 | 高 | JSON Schema 校验 + 重试机制 + 规则兜底 |
| 评分标准不准确 | 高 | 支持人工修订 + 持续优化机制 |
| 数据隐私安全 | 中 | 加密存储 + 审计日志 |
| 成本控制 | 中 | 模型选择优化 + 缓存机制 |

---

## 11. 未来扩展（Future Enhancements）

- 支持代码类题目（结合自动测试）
- RAG 检索参考答案
- 教学分析 Dashboard（Topic难度、错误趋势）
- 教师修改反馈反向训练 Rubric
- 多语言支持

