# 测试计划（Test Plan）

## 测试目标

验证 Semantic Scoring Agent 系统的核心功能逻辑，确保：
1. API 接口正确响应
2. 数据模型验证有效
3. 数据库操作正确
4. 业务逻辑符合预期
5. 错误处理完善

## 测试范围

### 1. API 接口测试

#### 1.1 评估接口
- ✅ `POST /evaluate/short-answer`
  - 正常评估流程
  - 题目不存在的情况
  - 答案格式验证（长度、必填）
  - 自定义评分标准
  - LLM 调用失败处理
  - 数据库保存失败处理

#### 1.2 教师审核接口
- ✅ `POST /review/save`
  - 正常保存审核
  - 评估记录不存在
  - 评分范围验证（0-10）
  - 数据库更新失败处理

#### 1.3 评估结果查询接口
- ✅ `GET /evaluations`
  - 列表查询（无筛选）
  - 按 question_id 筛选
  - 按 student_id 筛选
  - 分页功能
  - 空结果处理

- ✅ `GET /evaluations/{evaluation_id}`
  - 正常获取详情
  - 记录不存在的情况

#### 1.4 题目管理接口
- ✅ `GET /questions`
  - 列表查询
  - 按 topic 筛选
  - 分页功能

- ✅ `GET /questions/{question_id}`
  - 正常获取详情
  - 题目不存在的情况
  - 统计信息正确性

- ✅ `POST /questions`
  - 创建题目
  - 重复 question_id 处理
  - 必填字段验证

- ✅ `PUT /questions/{question_id}`
  - 更新题目
  - 部分更新
  - 题目不存在的情况

- ✅ `DELETE /questions/{question_id}`
  - 删除题目
  - 级联删除评分标准
  - 题目不存在的情况

#### 1.5 评分标准管理接口
- ✅ `GET /questions/{question_id}/rubrics`
  - 查询评分标准列表
  - 题目不存在的情况
  - 空列表处理

- ✅ `GET /rubrics/{rubric_id}`
  - 获取评分标准详情
  - 记录不存在的情况

- ✅ `POST /questions/{question_id}/rubrics`
  - 创建评分标准
  - 版本重复检查
  - 激活时自动取消其他激活

- ✅ `PUT /rubrics/{rubric_id}`
  - 更新评分标准
  - 部分更新
  - 激活状态更新

- ✅ `POST /rubrics/{rubric_id}/activate`
  - 激活评分标准
  - 自动取消同题目的其他激活
  - 记录不存在的情况

### 2. 数据模型测试

#### 2.1 Pydantic 模型验证
- ✅ `EvaluationRequest`
  - question_id 必填和格式验证
  - student_answer 长度验证（10-4000）
  - rubric_json 格式验证

- ✅ `LLMScorePayload`
  - total_score 范围验证（0-10）
  - dimension_breakdown 维度分数验证（0-2）
  - 必填字段验证

- ✅ `ReviewSaveRequest`
  - final_score 范围验证
  - evaluation_id 必填

- ✅ `QuestionCreate/Update`
  - 字段验证
  - 可选字段处理

- ✅ `RubricCreate/Update`
  - rubric_json 格式验证
  - version 必填验证

### 3. 数据库操作测试

#### 3.1 模型关系测试
- ✅ Question ↔ QuestionRubric（一对多）
- ✅ Question ↔ AnswerEvaluation（一对多）
- ✅ 外键约束测试
- ✅ 级联删除测试

#### 3.2 CRUD 操作测试
- ✅ Question 的增删改查
- ✅ QuestionRubric 的增删改查
- ✅ AnswerEvaluation 的增删改查
- ✅ 事务回滚测试

### 4. Rubric Service 测试

#### 4.1 评分标准查询逻辑
- ✅ `load_manual_rubric()`
  - 优先返回激活的评分标准
  - 无激活时返回最新的
  - 题目不存在的情况

#### 4.2 评分标准回退逻辑
- ✅ `get_rubric()`
  - 优先级1: 用户提供的
  - 优先级2: 数据库中的
  - 优先级3: 主题默认的
  - 优先级4: LLM 自动生成的

#### 4.3 LLM 生成评分标准
- ✅ `generate_rubric_by_llm()`
  - 正常生成
  - LLM 调用失败处理
  - JSON 解析失败处理
  - 维度权重自动调整

#### 4.4 评分标准保存
- ✅ `save_rubric_to_db()`
  - 正常保存
  - 版本重复检查
  - 数据库错误处理

### 5. LLM Client 测试（需要 Mock）

#### 5.1 LLM 调用
- ✅ `call_llm()`
  - 正常调用
  - API 调用失败处理
  - JSON 解析失败处理
  - 重试机制

#### 5.2 Prompt 构建
- ✅ `build_prompt()`
  - Prompt 格式正确
  - 包含所有必要信息

#### 5.3 提供商检测
- ✅ `_detect_provider()`
  - OpenAI 检测
  - OpenRouter 检测
  - 自定义 base_url 检测

### 6. 数据迁移测试

#### 6.1 迁移脚本
- ✅ `migrate_questions()`
  - 正常迁移
  - 重复数据跳过
  - 错误处理

- ✅ `migrate_default_rubrics()`
  - 正常迁移
  - 重复版本跳过

### 7. 集成测试

#### 7.1 完整评估流程
- ✅ 创建题目 → 创建评分标准 → 评估答案 → 保存结果
- ✅ 评估答案 → 教师审核 → 查询结果

#### 7.2 评分标准选择流程
- ✅ 不同优先级场景的完整测试

## 测试工具和框架

### 推荐工具
- **pytest**: Python 测试框架
- **pytest-asyncio**: 异步测试支持
- **httpx**: FastAPI 测试客户端
- **pytest-mock**: Mock 工具
- **faker**: 测试数据生成

### 测试数据库
- 使用 SQLite 内存数据库（:memory:）进行测试
- 每个测试用例独立数据库状态

## 测试文件结构

```
tests/
├── __init__.py
├── conftest.py              # pytest 配置和 fixtures
├── test_api/
│   ├── test_evaluation.py  # 评估接口测试
│   ├── test_review.py       # 审核接口测试
│   ├── test_questions.py    # 题目管理接口测试
│   └── test_rubrics.py      # 评分标准接口测试
├── test_models/
│   └── test_validation.py  # 数据模型验证测试
├── test_db/
│   ├── test_models.py      # 数据库模型测试
│   └── test_relationships.py # 关系测试
├── test_services/
│   ├── test_rubric_service.py # Rubric Service 测试
│   └── test_llm_client.py    # LLM Client 测试（Mock）
└── test_integration/
    └── test_workflows.py    # 集成测试
```

## 测试覆盖率目标

- **单元测试覆盖率**: ≥ 80%
- **API 接口覆盖率**: 100%
- **核心业务逻辑覆盖率**: ≥ 90%

## 测试执行计划

### Phase 1: 基础测试（优先级：高）
1. 数据模型验证测试
2. 数据库操作测试
3. API 接口基础测试

### Phase 2: 业务逻辑测试（优先级：高）
1. Rubric Service 测试
2. LLM Client Mock 测试
3. 评分标准回退逻辑测试

### Phase 3: 集成测试（优先级：中）
1. 完整工作流测试
2. 错误场景测试

### Phase 4: 性能测试（优先级：低）
1. 并发测试
2. 数据库查询性能测试

## 测试数据准备

### Fixtures
- 测试题目数据
- 测试评分标准数据
- 测试评估结果数据
- Mock LLM 响应数据

## CI/CD 集成

- 每次 PR 自动运行测试
- 测试失败阻止合并
- 生成测试覆盖率报告

