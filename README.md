# Semantic Scoring Agent

An intelligent answer evaluation system based on Large Language Models (LLM) for automatically evaluating student short-answer questions, providing multi-dimensional scoring and improvement suggestions.

## Project Introduction

Semantic Scoring Agent is an educational assessment tool that uses LLM to automatically score student short answers. The system supports:
- Multi-dimensional scoring (accuracy, structure, clarity, business understanding, language expression)
- Key point evaluation
- Improvement suggestion generation
- Evaluation result persistence
- Flexible Rubric configuration

## Features

- **Intelligent Scoring**: Uses LLM to automatically score answers across multiple dimensions (0-10 points)
- **Dimension Analysis**: Provides detailed scoring across dimensions such as accuracy, structure, clarity, business understanding, and language expression
- **Key Point Checking**: Automatically identifies whether answers cover key knowledge points
- **Improvement Suggestions**: Generates specific, actionable improvement recommendations
- **Custom Rubrics**: Supports custom rubric configuration via JSON
- **Result Storage**: All evaluation results are automatically saved to the database
- **Web UI**: Provides a friendly Streamlit interface
- **RESTful API**: Provides FastAPI backend interface

## Tech Stack

- **Backend Framework**: FastAPI
- **Frontend Framework**: Streamlit
- **LLM Integration**: LangChain + OpenAI/OpenRouter
- **Database**: SQLite (can be configured to other databases)
- **ORM**: SQLAlchemy
- **Data Validation**: Pydantic
- **Python Version**: 3.8+

## Installation

### 1. Clone the project

```bash
git clone <repository-url>
cd semantic-scoring-agent
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Environment configuration

Create a `.env` file and configure the following environment variables:

```env
# LLM configuration (required)
OPENAI_API_KEY=your_api_key_here

# Optional: Use OpenRouter
# OPENROUTER_API_KEY=your_openrouter_key
# OPENAI_BASE_URL=https://openrouter.ai/api/v1
# LLM_PROVIDER=openrouter

# Model configuration (optional, default is gpt-4o-mini)
MODEL_ID=gpt-4o-mini
# or
MODEL_NAME=gpt-4o-mini

# Database configuration (optional, default is SQLite)
DB_URL=sqlite:///./answer_eval.db

# API base URL (for UI, optional)
API_BASE=http://127.0.0.1:8000

# Auto-run migrations (optional, development only)
# AUTO_MIGRATE=true
```

### 4. Initialize database and users

Before first run, initialize the database and create default users:

```bash
# Initialize database and migrate data
python run_migrations.py

# Create default users (teacher and student)
python init_users.py
```

This will create all necessary database tables, migrate hardcoded question data, and create default users:
- Teacher: `teacher001` (Teacher Zhang)
- Student: `student001` (Student 1)

### 5. Run tests (optional)

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx pytest-mock faker

# Run core functionality tests
pytest tests/test_models/ tests/test_db/ tests/test_services/ -v

# Run all tests (requires langchain-openai)
pytest tests/ -v
```

**Test Statistics**: 38 core tests all passed

## Usage

### Start backend API

**Important**: Must run from project root directory, not from the `api` directory.

```bash
# Run from project root (recommended)
uvicorn api.main:app --reload --port 8000
```

**Wrong way** (will cause import errors):
```bash
cd api
uvicorn main:app --reload --port 8000  # This will fail
```

API documentation will be automatically generated at: http://127.0.0.1:8000/docs

### Start frontend UI

Open a second terminal window:

```bash
cd ui
streamlit run app.py
```

UI will automatically open in browser, default address: http://localhost:8501

### Quick Start Summary

1. **Terminal 1 - Backend**:
   ```bash
   uvicorn api.main:app --reload --port 8000
   ```

2. **Terminal 2 - Frontend**:
   ```bash
   cd ui
   streamlit run app.py
   ```

3. **Access the UI**: http://localhost:8501
   - Login with `teacher001` (Teacher) or `student001` (Student)
   - Use different features based on your role

### Common Issues

#### Port already in use

If you encounter `ERROR: [Errno 48] Address already in use` when starting:

**Method 1: Stop the process using the port (recommended)**
```bash
# Find process using port 8000
lsof -ti:8000

# Stop the process (replace PID with actual process ID)
kill <PID>

# Or force stop
kill -9 <PID>

# Stop all uvicorn processes
pkill -f "uvicorn.*api.main"
```

**Method 2: Use a different port**
```bash
# Backend: Use port 8001
uvicorn api.main:app --reload --port 8001

# Frontend: Use port 8502
streamlit run app.py --server.port 8502
```
Then update `API_BASE=http://127.0.0.1:8001` in the `.env` file

#### Database errors

If you encounter database-related errors:

```bash
# Delete old database (warning: will lose data)
rm answer_eval.db

# Reinitialize
python run_migrations.py
python init_users.py
```

#### Import errors

If you see `ImportError: attempted relative import with no known parent package`:

1. **Ensure you're in project root** (not the `api` directory)
2. **Use correct command**: `uvicorn api.main:app --reload --port 8000`

#### Missing dependencies

If you encounter import errors:

```bash
pip install -r requirements.txt
```

#### API Key errors

Ensure `OPENAI_API_KEY` in `.env` file is correctly set.

### Using the API

#### Evaluate answer

```bash
curl -X POST "http://127.0.0.1:8000/evaluate/short-answer" \
  -H "Content-Type: application/json" \
  -d '{
    "question_id": "Q2105",
    "student_answer": "In Airflow, I can manage task dependencies by defining DAGs, and use retry parameters to handle failures..."
  }'
```

#### Use custom rubric

```bash
curl -X POST "http://127.0.0.1:8000/evaluate/short-answer" \
  -H "Content-Type: application/json" \
  -d '{
    "question_id": "Q2105",
    "student_answer": "Your answer...",
    "rubric_json": {
      "version": "custom-v1",
      "dimensions": {
        "accuracy": 1,
        "structure": 1,
        "clarity": 1
      },
      "key_points": ["Key point 1", "Key point 2"],
      "common_mistakes": ["Common mistake 1"]
    }
  }'
```

## Project Structure

```
semantic-scoring-agent/
├── api/                    # Backend API
│   ├── __init__.py
│   ├── main.py            # FastAPI application entry
│   ├── models.py          # Pydantic data models
│   ├── db.py              # Database configuration and models
│   ├── auth.py            # Authentication and authorization
│   ├── llm_client.py      # LLM client wrapper
│   ├── rubric_service.py  # Rubric service
│   └── migrations.py      # Database migration script
├── ui/                    # Frontend UI
│   └── app.py             # Streamlit application
├── tests/                 # Test suite
│   ├── test_models/       # Data model tests
│   ├── test_db/           # Database model tests
│   ├── test_services/     # Business logic tests
│   ├── test_api/          # API endpoint tests
│   └── test_auth/         # Authentication tests
├── requirements.txt       # Python dependencies
├── run_migrations.py      # Run database migrations
├── init_users.py        # Initialize default users
├── start_ui.sh            # UI startup script
├── answer_eval.db        # SQLite database (auto-generated)
└── README.md             # Project documentation
```

## API Documentation

### API Endpoints Overview

The system provides **18 API endpoints**:

**Evaluation related (3)**:
- POST `/evaluate/short-answer` - Evaluate answer
- GET `/evaluations` - Query evaluation list
- GET `/evaluations/{evaluation_id}` - Get evaluation details

**Review related (1)**:
- POST `/review/save` - Save teacher review

**Question management (5)**:
- GET `/questions` - Query question list
- GET `/questions/{question_id}` - Get question details
- POST `/questions` - Create question
- PUT `/questions/{question_id}` - Update question
- DELETE `/questions/{question_id}` - Delete question

**Rubric management (5)**:
- GET `/questions/{question_id}/rubrics` - Query rubric list
- GET `/rubrics/{rubric_id}` - Get rubric details
- POST `/questions/{question_id}/rubrics` - Create rubric
- PUT `/rubrics/{rubric_id}` - Update rubric
- POST `/rubrics/{rubric_id}/activate` - Activate rubric

**User management (3)**:
- POST `/users` - Create user
- GET `/users` - Get user list
- GET `/users/{user_id}` - Get user details

**Other (1)**:
- GET `/docs` - API documentation (auto-generated by FastAPI)

### POST `/evaluate/short-answer`

Evaluate student short answer.

**Request body**:
```json
{
  "question_id": "string",      // Required: Question ID
  "student_answer": "string",   // Required: Student answer (10-4000 characters)
  "with_rubric": false,         // Optional: Whether to use custom rubric
  "rubric_json": {}             // Optional: Custom rubric JSON
}
```

**Response**:
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
    "DAG/Task semantics and scheduling cycles -> covered",
    "Dependencies and retry strategies -> partially covered"
  ],
  "improvement_recommendations": [
    "Suggestion 1",
    "Suggestion 2"
  ],
  "raw_llm_output": {}
}
```

### POST `/review/save`

Save teacher score override.

**Request body**:
```json
{
  "evaluation_id": 1,          // Required: Evaluation record ID
  "final_score": 8.5,          // Required: Final score (0-10)
  "review_notes": "Good answer",   // Optional: Review notes
  "reviewer_id": "teacher001"  // Optional: Reviewer ID
}
```

**Response**:
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

Query evaluation result list.

**Query parameters**:
- `question_id` (optional): Filter by question ID
- `student_id` (optional): Filter by student ID
- `limit` (optional, default 50): Items per page (1-100)
- `offset` (optional, default 0): Offset

**Response**:
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

Get evaluation result details.

**Response**:
```json
{
  "id": 1,
  "question_id": "Q2105",
  "student_id": "student001",
  "student_answer": "Answer content...",
  "auto_score": 7.5,
  "final_score": 8.5,
  "dimension_scores_json": {
    "accuracy": 1.5,
    "structure": 1.8
  },
  "model_version": "openai:gpt-4o-mini",
  "rubric_version": "topic-airflow-v1",
  "review_notes": "Good answer",
  "reviewer_id": "teacher001",
  "raw_llm_output": {},
  "created_at": "2024-01-01T10:00:00",
  "updated_at": "2024-01-01T11:00:00"
}
```

### GET `/questions`

Query question list.

**Query parameters**:
- `topic` (optional): Filter by topic
- `limit` (optional, default 50): Items per page (1-100)
- `offset` (optional, default 0): Offset

**Response**:
```json
{
  "total": 10,
  "items": [
    {
      "id": 1,
      "question_id": "Q2105",
      "text": "Briefly describe how to implement reliable dependency management and failure recovery in Airflow.",
      "topic": "airflow",
      "created_at": "2024-01-01T10:00:00",
      "updated_at": "2024-01-01T10:00:00"
    }
  ]
}
```

### GET `/questions/{question_id}`

Get question details.

**Response**:
```json
{
  "id": 1,
  "question_id": "Q2105",
  "text": "Briefly describe how to implement reliable dependency management and failure recovery in Airflow.",
  "topic": "airflow",
  "created_at": "2024-01-01T10:00:00",
  "updated_at": "2024-01-01T10:00:00",
  "rubrics_count": 2,
  "evaluations_count": 15
}
```

### POST `/questions`

Create new question.

**Request body**:
```json
{
  "question_id": "Q2106",
  "text": "Question text",
  "topic": "airflow"
}
```

**Response**: Returns created question information (same format as GET `/questions/{question_id}`)

### PUT `/questions/{question_id}`

Update question.

**Request body**:
```json
{
  "text": "Updated question text",
  "topic": "updated-topic"
}
```

**Response**: Returns updated question information

### DELETE `/questions/{question_id}`

Delete question (will cascade delete associated rubrics).

**Response**: 204 No Content

### GET `/questions/{question_id}/rubrics`

Query question rubric list.

**Response**:
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

Get rubric details.

**Response**:
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

Create rubric for question.

**Request body**:
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

**Response**: Returns created rubric details

### PUT `/rubrics/{rubric_id}`

Update rubric.

**Request body**:
```json
{
  "rubric_json": {...},
  "is_active": true
}
```

**Response**: Returns updated rubric details

### POST `/rubrics/{rubric_id}/activate`

Activate rubric (will automatically deactivate other active rubrics for the same question).

**Response**:
```json
{
  "success": true,
  "message": "Rubric topic-airflow-v1 activated successfully",
  "rubric_id": 1,
  "question_id": "Q2105",
  "version": "topic-airflow-v1"
}
```

## Database Models

### User

User table, contains the following fields:
- `id`: Primary key (user ID, e.g., "teacher001", "student001")
- `username`: User name
- `role`: User role ("student" or "teacher")
- `created_at`: Creation time

### Question

Question table, contains the following fields:
- `id`: Primary key
- `question_id`: Question unique identifier (e.g., "Q2105")
- `text`: Question text
- `topic`: Question topic (e.g., "airflow")
- `created_at`: Creation time
- `updated_at`: Update time

### QuestionRubric

Rubric table, contains the following fields:
- `id`: Primary key
- `question_id`: Associated question ID (foreign key)
- `version`: Rubric version
- `rubric_json`: Rubric JSON (contains dimensions, key_points, common_mistakes, etc.)
- `is_active`: Whether activated
- `created_by`: Creator
- `created_at`: Creation time

### AnswerEvaluation

Evaluation result table, contains the following fields:
- `id`: Primary key
- `question_id`: Question ID (foreign key, SET NULL on delete)
- `student_id`: Student ID (optional, foreign key to User, SET NULL on delete)
- `student_answer`: Student answer
- `auto_score`: Auto score (0-10)
- `final_score`: Final score (optional, for teacher override)
- `dimension_scores_json`: Dimension scores JSON
- `model_version`: Model version used
- `rubric_version`: Rubric version used
- `raw_llm_output`: Raw LLM output
- `reviewer_id`: Reviewer teacher ID (optional, foreign key to User)
- `review_notes`: Review notes (optional)
- `created_at`: Creation time
- `updated_at`: Update time

## Rubrics

The system supports four rubric sources (automatically selected by priority):

1. **User-provided JSON**: Passed via `rubric_json` in API request
2. **Database rubric**: Loaded from `question_rubrics` table (prioritizes active rubrics)
3. **Topic default rubric**: Default standard based on question topic (e.g., `airflow` topic)
4. **LLM auto-generated**: If none of the above exist, system uses LLM to auto-generate rubric and save to database

### Rubric fallback logic

```
User provided → Database query → Topic default → LLM auto-generated
```

The system automatically selects the most appropriate rubric, ensuring every evaluation has available scoring criteria.

### Rubric format

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
    "Key point 1",
    "Key point 2"
  ],
  "common_mistakes": [
    "Common mistake 1",
    "Common mistake 2"
  ]
}
```

## Configuration

### LLM Providers

The system supports multiple LLM providers:

1. **OpenAI** (default):
   ```env
   OPENAI_API_KEY=sk-...
   MODEL_ID=gpt-4o-mini
   ```

2. **OpenRouter**:
   ```env
   OPENAI_BASE_URL=https://openrouter.ai/api/v1
   OPENAI_API_KEY=sk-or-...
   OPENROUTER_REFERER=https://your-site.com
   OPENROUTER_TITLE=Your App Name
   ```

3. **Custom OpenAI-compatible API**:
   ```env
   OPENAI_BASE_URL=https://your-api.com/v1
   OPENAI_API_KEY=your-key
   ```

## Authentication and Authorization

The system implements a simplified permission system with two roles:

### Roles

- **Student (student)**: Answer questions, view own results
- **Teacher (teacher)**: Manage, grade, view all results

### Authentication

- **Header**: `X-User-Token: {user_id}`
- **Frontend**: Automatically adds authentication header after login
- **Backend**: Validates user and role from database

### Permission Matrix

| Feature | Student | Teacher |
|---------|---------|---------|
| Answer questions | Yes | Yes |
| View own results | Yes | Yes |
| View all results | No | Yes |
| Review/Grade | No | Yes |
| Question management | No | Yes |
| Rubric management | No | Yes |
| User management | No | Yes |

### Create New Users

**Via API (requires teacher permission)**:
```bash
curl -X POST "http://127.0.0.1:8000/users" \
  -H "X-User-Token: teacher001" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "student002",
    "username": "Student 2",
    "role": "student"
  }'
```

**Via Python script**:
```python
from api.db import SessionLocal, User

sess = SessionLocal()
try:
    user = User(id="student002", username="Student 2", role="student")
    sess.add(user)
    sess.commit()
finally:
    sess.close()
```

## Testing

The project includes a complete test suite covering core functionality:

### Test Statistics

- **Core tests**: 38 tests all passed
- **Data model tests**: 19
- **Database model tests**: 9
- **Business logic tests**: 10

### Run tests

```bash
# Run all tests
pytest tests/

# Run core functionality tests (no additional dependencies required)
pytest tests/test_models/ tests/test_db/ tests/test_services/ -v

# Run specific test modules
pytest tests/test_models/
pytest tests/test_db/
pytest tests/test_services/

# Run with coverage
pytest --cov=api --cov-report=html

# Run all tests (requires langchain-openai)
pip install langchain-openai
pytest tests/ -v
```

### Test Structure

- `test_models/`: Data model validation tests (19 tests)
- `test_db/`: Database model and relationship tests (9 tests)
- `test_services/`: Business logic tests (10 tests, 2 skipped)
- `test_api/`: API endpoint tests (requires langchain-openai)

### Notes

1. Tests use SQLite in-memory database, each test case is independent
2. LLM calls are mocked, no actual API calls
3. Test data provided through fixtures
4. Some tests require langchain_openai module (marked as skip)

## Development Plan

### Completed
- [x] Implement teacher score override functionality (`/review/save` endpoint)
- [x] Support loading question-specific rubrics from database
- [x] Implement evaluation result query endpoints (`/evaluations`)
- [x] Complete teacher review UI interface
- [x] Question management endpoints (CRUD)
- [x] Rubric management endpoints
- [x] Establish complete test framework (38 tests passed)

### Planned
- [ ] Add more question examples
- [ ] Support batch evaluation
- [ ] Add evaluation result statistics and analysis features
- [ ] Support multiple languages

## Verification

Run tests to verify the system is working correctly:

```bash
# Run core functionality tests
pytest tests/test_models/ tests/test_db/ tests/test_services/ -v
```

Expected result: `38 passed`

## Contributing

Welcome to submit Issues and Pull Requests!

## License

[To be added]

## Authors

[To be added]
