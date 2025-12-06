# 开发计划（Development Plan）

## 当前状态分析

### ✅ 已实现功能

1. **基础API层**
   - `POST /evaluate/short-answer` 接口
   - 基本的请求/响应模型
   - 错误处理

2. **Scoring Agent层**
   - LLM 集成（支持 OpenAI/OpenRouter）
   - Prompt 构建
   - JSON 输出解析和验证

3. **基础数据持久化**
   - `answer_evaluations` 表
   - SQLAlchemy ORM 配置

4. **简单UI**
   - Streamlit 基础界面
   - 答案输入和结果展示

5. **Rubric Service（部分）**
   - 默认主题评分标准
   - 用户提供 JSON 支持
   - 回退逻辑框架

### ❌ 待实现功能

1. **数据模型不完整**
   - 缺少 `questions` 表
   - 缺少 `question_rubrics` 表

2. **Rubric Service 不完整**
   - 数据库查询未实现
   - LLM 自动生成 Rubric 未实现

3. **教师审核功能缺失**
   - 缺少 `POST /review/save` 接口
   - 缺少评估结果查询接口
   - UI 中教师覆盖功能未完成

4. **题目管理缺失**
   - 题目硬编码在代码中
   - 无题目 CRUD 接口

---

## 下一步开发计划

### 🎯 Phase 2.1: 完善数据模型（优先级：高）

**目标**：建立完整的数据模型，支持题目和评分标准管理

#### 任务清单

1. **创建 Questions 表**
   - [ ] 在 `api/db.py` 中添加 `Question` 模型
   - [ ] 字段：id, question_id, text, topic, created_at, updated_at
   - [ ] 创建数据库迁移脚本

2. **创建 QuestionRubric 表**
   - [ ] 在 `api/db.py` 中添加 `QuestionRubric` 模型
   - [ ] 字段：id, question_id, version, rubric_json, is_active, created_by, created_at
   - [ ] 建立与 Question 的外键关系

3. **更新 AnswerEvaluation 模型**
   - [ ] 添加 `reviewer_id` 字段
   - [ ] 添加 `review_notes` 字段
   - [ ] 添加 `updated_at` 字段

4. **创建数据库迁移工具**
   - [ ] 使用 Alembic 或手动迁移脚本
   - [ ] 初始化数据脚本（迁移现有 QUESTION_BANK）

#### 预计工作量：2-3 天

---

### 🎯 Phase 2.2: 完善 Rubric Service（优先级：高）

**目标**：实现完整的评分标准查询和生成逻辑

#### 任务清单

1. **实现数据库查询** ✅
   - [x] 实现 `load_manual_rubric()` 从数据库查询
   - [x] 支持按 question_id 和 version 查询
   - [x] 支持查询激活的评分标准

2. **实现 LLM 自动生成 Rubric** ✅
   - [x] 创建 `generate_rubric_by_llm()` 函数
   - [x] 构建生成 prompt
   - [x] 解析并验证生成的 JSON
   - [x] 自动保存到数据库（`save_rubric_to_db()`）

3. **完善回退逻辑** ✅
   - [x] 确保回退链完整：provided → DB → topic_default → LLM生成
   - [x] 添加日志记录

#### 预计工作量：2-3 天 ✅ 已完成

---

### 🎯 Phase 2.3: 题目管理接口（优先级：中）✅

**目标**：提供题目的 CRUD 接口

#### 任务清单

1. **题目查询接口** ✅
   - [x] `GET /questions` - 列表查询（支持分页、按主题筛选）
   - [x] `GET /questions/{question_id}` - 详情查询（包含统计信息）

2. **题目管理接口** ✅
   - [x] `POST /questions` - 创建题目
   - [x] `PUT /questions/{question_id}` - 更新题目
   - [x] `DELETE /questions/{question_id}` - 删除题目

3. **评分标准管理接口** ✅
   - [x] `GET /questions/{question_id}/rubrics` - 查询评分标准列表
   - [x] `GET /rubrics/{rubric_id}` - 获取评分标准详情
   - [x] `POST /questions/{question_id}/rubrics` - 创建评分标准
   - [x] `PUT /rubrics/{rubric_id}` - 更新评分标准
   - [x] `POST /rubrics/{rubric_id}/activate` - 激活评分标准（自动取消其他激活）

#### 预计工作量：2-3 天 ✅ 已完成

---

### 🎯 Phase 2.4: 教师审核功能（优先级：高）✅

**目标**：实现教师查看和修改评分的完整流程

#### 任务清单

1. **评估结果查询接口** ✅
   - [x] `GET /evaluations` - 列表查询（支持分页、筛选）
   - [x] `GET /evaluations/{evaluation_id}` - 详情查询
   - [x] 支持按 question_id, student_id 筛选

2. **教师审核接口** ✅
   - [x] `POST /review/save` - 保存教师评分覆盖
   - [x] 请求体：evaluation_id, final_score, review_notes, reviewer_id
   - [x] 更新 `final_score` 和 `reviewer_id`

3. **UI 增强** ✅
   - [x] 评估结果列表页面
   - [x] 详情页面（显示 auto_score 和 final_score 对比）
   - [x] 评分覆盖表单
   - [x] 完成 UI 中的教师审核功能

#### 预计工作量：3-4 天 ✅ 已完成

---

### 🎯 Phase 3: 高级功能（优先级：低）

#### 任务清单

1. **统计分析**
   - [ ] 评分分布统计
   - [ ] 维度分析
   - [ ] 题目难度分析
   - [ ] Dashboard 页面

3. **批量评估**
   - [ ] `POST /evaluate/batch` 接口
   - [ ] 支持 CSV 文件上传
   - [ ] 异步处理支持

---

## 开发优先级建议

### 立即开始（本周）

1. ✅ **Phase 2.1: 完善数据模型** - 这是所有功能的基础
2. ✅ **Phase 2.2: 完善 Rubric Service** - 核心功能，影响评分质量

### 接下来（下周）

3. ✅ **Phase 2.4: 教师审核功能** - 核心业务流程，用户急需
4. ✅ **Phase 2.3: 题目管理接口** - 支持系统扩展

### 后续（下月）

5. ✅ **Phase 3: 高级功能** - 增强功能

---

## 技术债务

1. **代码组织**
   - [ ] 将 QUESTION_BANK 迁移到数据库
   - [ ] 重构代码结构（按功能模块拆分）
   - [ ] 添加单元测试

2. **错误处理**
   - [ ] 统一错误响应格式
   - [ ] 添加更详细的错误信息
   - [ ] 添加重试机制

3. **性能优化**
   - [ ] 添加缓存机制（Rubric 缓存）
   - [ ] 数据库查询优化
   - [ ] LLM 调用优化

4. **文档**
   - [ ] API 文档完善
   - [ ] 部署文档
   - [ ] 开发环境搭建文档

---

## 里程碑时间表

| 里程碑 | 预计完成时间 | 状态 |
|--------|------------|------|
| Phase 1: MVP | ✅ 已完成 | 完成 |
| Phase 2.1: 数据模型 | 本周 | 待开始 |
| Phase 2.2: Rubric Service | 本周 | 待开始 |
| Phase 2.4: 教师审核 | 下周 | 待开始 |
| Phase 2.3: 题目管理 | 下周 | 待开始 |
| Phase 3: 高级功能 | 后续 | 待开始 |

---

## 下一步行动

**建议立即开始的任务：**

1. 创建 `Question` 和 `QuestionRubric` 数据模型
2. 实现数据库迁移脚本
3. 完善 `rubric_service.py` 中的数据库查询逻辑

**需要讨论的问题：**

1. 是否使用 Alembic 进行数据库迁移？
2. 是否需要立即实现审计日志功能？

