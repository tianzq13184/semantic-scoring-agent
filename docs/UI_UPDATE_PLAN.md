# 前端更新计划

## 📋 当前状态

前端已经实现了以下功能：
- ✅ 评估答案页面
- ✅ 评估结果列表页面
- ✅ 评估详情页面（包括教师审核功能）

## 🔧 需要更新的部分

### 1. **评估答案页面** - 需要更新 ⚠️

**当前问题**：
- 题目ID硬编码为 `["Q2105"]`，无法使用数据库中的其他题目

**需要修改**：
```python
# 当前代码（第26行）
question_id = st.selectbox("Question ID", ["Q2105"])

# 应该改为从API动态加载
try:
    r = requests.get(f"{API_BASE}/questions", params={"limit": 100}, timeout=5)
    if r.status_code == 200:
        questions = r.json()["items"]
        question_options = {q["question_id"]: q["question_id"] for q in questions}
        question_id = st.selectbox("Question ID", list(question_options.keys()))
    else:
        question_id = st.selectbox("Question ID", ["Q2105"])  # 回退
except:
    question_id = st.selectbox("Question ID", ["Q2105"])  # 回退
```

### 2. **新增页面：题目管理** - 建议添加 ✨

可以添加一个新页面来管理题目（CRUD操作）：

**功能**：
- 查看题目列表（支持筛选和分页）
- 创建新题目
- 编辑题目
- 删除题目
- 查看题目详情（包括关联的评分标准和评估数量）

**API接口**：
- `GET /questions` - 获取题目列表
- `GET /questions/{question_id}` - 获取题目详情
- `POST /questions` - 创建题目
- `PUT /questions/{question_id}` - 更新题目
- `DELETE /questions/{question_id}` - 删除题目

### 3. **新增页面：评分标准管理** - 建议添加 ✨

可以添加一个新页面来管理评分标准：

**功能**：
- 查看题目的所有评分标准版本
- 创建新版本的评分标准
- 编辑评分标准
- 激活/停用评分标准
- 查看评分标准详情

**API接口**：
- `GET /questions/{question_id}/rubrics` - 获取题目的评分标准列表
- `GET /rubrics/{rubric_id}` - 获取评分标准详情
- `POST /questions/{question_id}/rubrics` - 创建评分标准
- `PUT /rubrics/{rubric_id}` - 更新评分标准
- `POST /rubrics/{rubric_id}/activate` - 激活评分标准

## 📝 更新优先级

### 高优先级 ⚠️
1. **更新"评估答案"页面** - 从数据库动态加载题目列表
   - 影响：用户无法使用数据库中的其他题目进行评估
   - 修复难度：简单（只需修改一个函数）

### 中优先级 ✨
2. **添加"题目管理"页面** - 方便管理题目
   - 影响：提升用户体验，方便管理题目
   - 修复难度：中等（需要创建新页面和表单）

3. **添加"评分标准管理"页面** - 方便管理评分标准
   - 影响：提升用户体验，方便管理评分标准
   - 修复难度：中等（需要创建新页面和表单）

## 🚀 快速修复方案

如果只想快速修复"评估答案"页面的问题，可以只更新第26行：

```python
# 在页面顶部加载题目列表
@st.cache_data(ttl=60)  # 缓存60秒
def load_questions():
    try:
        r = requests.get(f"{API_BASE}/questions", params={"limit": 100}, timeout=5)
        if r.status_code == 200:
            return r.json()["items"]
    except:
        pass
    return []

# 在评估答案页面使用
questions = load_questions()
if questions:
    question_options = [q["question_id"] for q in questions]
    question_id = st.selectbox("Question ID", question_options)
else:
    question_id = st.selectbox("Question ID", ["Q2105"])  # 回退
```

## 📊 总结

**必须更新**：
- ✅ 评估答案页面的题目选择（硬编码问题）

**建议添加**：
- ✨ 题目管理页面（提升用户体验）
- ✨ 评分标准管理页面（提升用户体验）

**当前可用功能**：
- ✅ 评估答案（除了题目选择问题）
- ✅ 评估结果列表
- ✅ 评估详情和教师审核

---

**建议**：先修复"评估答案"页面的题目选择问题，然后根据实际需求决定是否添加管理页面。

