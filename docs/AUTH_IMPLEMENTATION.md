# 权限系统实现计划

## 设计概述

简化的权限系统，支持两个角色：
- **学生（student）**：答题、浏览自己的结果
- **老师（teacher）**：管理、判分、查看所有结果

## 实现步骤

### 1. 数据模型 ✅
- [x] 创建 User 表（id, username, role）
- [x] 更新 AnswerEvaluation 表，添加外键关联

### 2. 权限系统 ✅
- [x] 创建 `api/auth.py` 权限检查模块
- [x] 实现 `get_current_user` 函数（从请求头获取用户）
- [x] 实现 `require_role` 权限检查装饰器

### 3. API 接口权限控制

#### 学生权限（require_student）
- `POST /evaluate/short-answer` - 答题
- `GET /evaluations` - 只能查看自己的评估结果
- `GET /evaluations/{id}` - 只能查看自己的评估详情

#### 老师权限（require_teacher）
- `POST /review/save` - 判分
- `GET /evaluations` - 查看所有评估结果
- `GET /evaluations/{id}` - 查看所有评估详情
- `GET /questions` - 题目管理
- `POST /questions` - 创建题目
- `PUT /questions/{id}` - 更新题目
- `DELETE /questions/{id}` - 删除题目
- `GET /questions/{id}/rubrics` - 评分标准管理
- `POST /questions/{id}/rubrics` - 创建评分标准
- `PUT /rubrics/{id}` - 更新评分标准
- `POST /rubrics/{id}/activate` - 激活评分标准

### 4. 用户管理接口
- `POST /users` - 创建用户（仅老师）
- `GET /users` - 用户列表（仅老师）
- `GET /users/{id}` - 用户详情

### 5. 前端更新
- 添加登录/角色选择界面
- 根据角色显示不同功能
- 在请求头中添加 `X-User-Token`

### 6. 用户初始化脚本
- 创建默认管理员账户
- 创建测试学生账户

## 认证方式

简化实现：使用 `X-User-Token` 请求头传递用户ID
- 优点：简单快速
- 缺点：安全性较低（适合内部使用）

生产环境建议使用 JWT 或 OAuth2

## 权限矩阵

| 功能 | 学生 | 老师 |
|------|------|------|
| 答题 | ✅ | ✅ |
| 查看自己的结果 | ✅ | ✅ |
| 查看所有结果 | ❌ | ✅ |
| 判分 | ❌ | ✅ |
| 题目管理 | ❌ | ✅ |
| 评分标准管理 | ❌ | ✅ |

