# 启动说明

## ⚠️ 重要：启动方式

### 后端 API 启动

**必须在项目根目录运行**，不要进入 `api` 目录：

```bash
# 在项目根目录（semantic-scoring-agent）运行
uvicorn api.main:app --reload --port 8000
```

**错误的方式**（会导致导入错误）：
```bash
cd api
uvicorn main:app --reload --port 8000  # ❌ 这会报错
```

### 前端 UI 启动

```bash
cd ui
streamlit run app.py
```

## 🔧 如果遇到导入错误

如果看到 `ImportError: attempted relative import with no known parent package`：

1. **确保在项目根目录**（不是 `api` 目录）
2. **使用正确的命令**：`uvicorn api.main:app --reload --port 8000`

## 📝 完整启动流程

```bash
# 1. 进入项目根目录
cd /Users/kurttian/Desktop/semantic-scoring-agent

# 2. 启动后端（终端1）
uvicorn api.main:app --reload --port 8000

# 3. 启动前端（终端2）
cd ui
streamlit run app.py
```

