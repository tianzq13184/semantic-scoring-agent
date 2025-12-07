# 权限系统快速实现指南

## 已完成 ✅

1. **数据模型**
   - ✅ User 表已创建
   - ✅ AnswerEvaluation 表已更新（外键关联）

2. **权限系统核心**
   - ✅ `api/auth.py` 已创建
   - ✅ 权限检查函数已实现

## 待实现 📋

### 1. 在 API 接口中添加权限控制

需要在 `api/main.py` 中为各个接口添加权限检查：

**学生接口**（添加 `current_user: dict = Depends(require_student)`）：
- `POST /evaluate/short-answer` - 答题时记录 student_id
- `GET /evaluations` - 只返回当前学生的结果
- `GET /evaluations/{id}` - 只能查看自己的结果

**老师接口**（添加 `current_user: dict = Depends(require_teacher)`）：
- `POST /review/save` - 判分
- `GET /evaluations` - 查看所有结果
- `GET /evaluations/{id}` - 查看所有结果
- 所有题目和评分标准管理接口

### 2. 添加用户管理接口

在 `api/main.py` 末尾添加：

```python
@app.post("/users", response_model=UserItem, status_code=201)
def create_user(req: UserCreate, current_user: dict = Depends(require_teacher)):
    """创建用户（仅老师）"""
    # 实现代码

@app.get("/users", response_model=List[UserItem])
def list_users(current_user: dict = Depends(require_teacher)):
    """用户列表（仅老师）"""
    # 实现代码
```

### 3. 创建用户初始化脚本

创建 `init_users.py`：

```python
from api.db import SessionLocal, User

def init_users():
    sess = SessionLocal()
    try:
        # 创建默认老师
        teacher = User(id="teacher001", username="张老师", role="teacher")
        sess.add(teacher)
        
        # 创建测试学生
        student = User(id="student001", username="学生1", role="student")
        sess.add(student)
        
        sess.commit()
        print("用户初始化完成")
    finally:
        sess.close()
```

### 4. 更新前端 UI

在 `ui/app.py` 中添加：
- 登录/角色选择界面
- 在请求头中添加 `X-User-Token`
- 根据角色显示/隐藏功能

## 使用方式

1. **初始化用户**：
   ```bash
   python init_users.py
   ```

2. **前端使用**：
   - 选择角色（学生/老师）
   - 系统自动在请求头中添加 `X-User-Token`

3. **API 调用**：
   ```python
   headers = {"X-User-Token": "student001"}
   response = requests.post(url, json=data, headers=headers)
   ```

## 权限矩阵

| 功能 | 学生 | 老师 |
|------|------|------|
| 答题 | ✅ | ✅ |
| 查看自己的结果 | ✅ | ✅ |
| 查看所有结果 | ❌ | ✅ |
| 判分 | ❌ | ✅ |
| 题目管理 | ❌ | ✅ |
| 评分标准管理 | ❌ | ✅ |

