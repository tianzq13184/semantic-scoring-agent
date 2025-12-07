# 测试说明

## 运行测试

```bash
# 运行所有测试
pytest tests/

# 运行核心功能测试（不需要 langchain_openai）
pytest tests/test_models/ tests/test_db/ tests/test_services/test_rubric_service.py::TestLoadManualRubric tests/test_services/test_rubric_service.py::TestGetRubric tests/test_services/test_rubric_service.py::TestSaveRubricToDB

# 运行特定模块的测试
pytest tests/test_models/
pytest tests/test_db/
pytest tests/test_services/

# 运行并显示覆盖率
pytest --cov=api --cov-report=html

# 运行特定测试
pytest tests/test_models/test_validation.py::TestEvaluationRequest::test_valid_request
```

## 测试结构

- `test_models/`: 数据模型验证测试 ✅ 19个测试
- `test_db/`: 数据库模型和关系测试 ✅ 9个测试
- `test_services/`: 业务逻辑测试 ✅ 10个测试（2个跳过）
- `test_api/`: API 接口测试 ⚠️ 需要 langchain_openai 模块

## 测试统计

### ✅ 通过的测试: 38个

- **数据模型测试**: 19个 ✅
- **数据库模型测试**: 9个 ✅
- **Rubric Service 测试**: 10个 ✅（2个跳过）

### ⚠️ 需要 langchain_openai 的测试

API 接口测试需要 `langchain_openai` 模块。安装后可以运行：

```bash
pip install langchain-openai
pytest tests/test_api/ -v
```

## 注意事项

1. 测试使用 SQLite 内存数据库，每个测试用例独立
2. LLM 调用使用 Mock，不实际调用 API
3. 测试数据通过 fixtures 提供
4. 部分测试需要 langchain_openai 模块（已标记为 skip）

## 测试覆盖的核心功能

- ✅ 数据模型验证（字段验证、类型检查、范围检查）
- ✅ 数据库 CRUD 操作
- ✅ 模型关系（一对多、外键约束）
- ✅ 级联删除
- ✅ 评分标准回退逻辑
- ✅ 数据库查询逻辑

## 快速验证

运行核心测试验证系统：

```bash
pytest tests/test_models/ tests/test_db/ tests/test_services/test_rubric_service.py::TestLoadManualRubric tests/test_services/test_rubric_service.py::TestGetRubric tests/test_services/test_rubric_service.py::TestSaveRubricToDB -v
```

预期结果：**38 passed**
