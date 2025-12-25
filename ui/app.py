# ui/app.py
import os
import json
import streamlit as st
import requests
from dotenv import load_dotenv
from datetime import datetime

st.set_page_config(page_title="Answer Evaluator", layout="wide")

load_dotenv()

# Try to get API_BASE from secrets or environment variables
try:
    API_BASE = st.secrets.get("API_BASE", None)
except (FileNotFoundError, AttributeError):
    API_BASE = None

API_BASE = API_BASE or os.getenv("API_BASE", "http://127.0.0.1:8000")

# Get request headers (including user token)
def get_headers():
    """Get request headers containing user authentication information"""
    headers = {}
    if "user_token" in st.session_state:
        headers["X-User-Token"] = st.session_state.user_token
    return headers

# ==================== User Login/Role Selection ====================
# Initialize session state
if "current_user" not in st.session_state:
    st.session_state.current_user = None
if "user_token" not in st.session_state:
    st.session_state.user_token = None

# Sidebar: User login
with st.sidebar:
    st.title("Login")
    
    if st.session_state.current_user is None:
        # Not logged in: show login form
        user_id = st.selectbox("Select User", ["teacher001", "student001"], help="Select the user ID to log in")
        
        if st.button("Login", type="primary", use_container_width=True):
            # Verify user (simplified implementation: use user ID directly as token)
            try:
                r = requests.get(f"{API_BASE}/users/{user_id}", headers={"X-User-Token": user_id}, timeout=5)
                if r.status_code == 200:
                    user_data = r.json()
                    st.session_state.current_user = user_data
                    st.session_state.user_token = user_id
                    st.success(f"Login successful! Welcome, {user_data['username']}")
                    st.rerun()
                elif r.status_code == 401:
                    st.error("Login required")
                else:
                    st.error(f"Login failed: {r.status_code}")
            except Exception as e:
                st.error(f"Login failed: {e}")
    else:
        # Logged in: show user info and logout button
        user = st.session_state.current_user
        st.success(f"{user['username']}")
        st.caption(f"Role: {'Teacher' if user['role'] == 'teacher' else 'Student'}")
        
        if st.button("Logout", use_container_width=True):
            st.session_state.current_user = None
            st.session_state.user_token = None
            st.rerun()

# If not logged in, show prompt
if st.session_state.current_user is None:
    st.warning("Please login first")
    st.stop()

# Get current user information
current_user = st.session_state.current_user
user_role = current_user["role"]
user_token = st.session_state.user_token

# Show different page options based on role
if user_role == "teacher":
    pages = ["Evaluate Answer", "Evaluation List", "Evaluation Detail", "Question Management", "Rubric Management"]
else:
    pages = ["Evaluate Answer", "Evaluation List", "Evaluation Detail"]

# Page selection
page = st.sidebar.selectbox("Page", pages)

# Load question list (cached for 60 seconds)
@st.cache_data(ttl=60)
def load_questions():
    """Load question list from API"""
    try:
        r = requests.get(f"{API_BASE}/questions", params={"limit": 100}, timeout=5)
        if r.status_code == 200:
            return r.json()["items"]
    except Exception as e:
        st.sidebar.warning(f"Failed to load question list: {e}")
    return []

if page == "Evaluate Answer":
    with st.sidebar:
        st.title("Answer Evaluator")
        
        # Dynamically load question list from database
        @st.cache_data(ttl=60)
        def load_questions_with_auth():
            """Load question list from API (with authentication)"""
            try:
                headers = {"X-User-Token": user_token}
                r = requests.get(f"{API_BASE}/questions", params={"limit": 100}, headers=headers, timeout=5)
                if r.status_code == 200:
                    return r.json()["items"]
            except Exception as e:
                st.sidebar.warning(f"Failed to load question list: {e}")
            return []
        
        questions = load_questions_with_auth()
        if questions:
            question_options = [q["question_id"] for q in questions]
            question_id = st.selectbox("Question ID", question_options)
            # Show question information
            selected_question = next((q for q in questions if q["question_id"] == question_id), None)
            if selected_question:
                st.caption(f"Topic: {selected_question.get('topic', 'N/A')}")
        else:
            # Fallback to hardcoded (if API is unavailable)
            question_id = st.selectbox("Question ID", ["Q2105"])
            st.warning("Unable to load question list, using default question")
        
        with_rubric = st.checkbox("I already have a rubric JSON", value=False)
        rubric_text = ""
        if with_rubric:
            rubric_text = st.text_area("Paste rubric JSON", height=180, placeholder='{"version":"manual-v1", ...}')

    st.markdown("### Candidate Answer")
    student_answer = st.text_area("Write your answer here", height=220, placeholder="I will use Airflow to schedule jobs...")
    has_answer = bool(student_answer.strip())
    if not has_answer:
        st.caption("Answer is required before running evaluation.")

    col_run, col_res = st.columns([1,2])

    with col_run:
        if st.button("Evaluate", type="primary", use_container_width=True, disabled=not has_answer):
            payload = {
                "question_id": question_id,
                "student_answer": student_answer
            }
            # If user provided rubric, add to payload
            if with_rubric and rubric_text.strip():
                try:
                    payload["rubric_json"] = json.loads(rubric_text)
                except Exception as e:
                    st.error(f"Rubric JSON invalid: {e}")
                    st.stop()  # Stop execution, don't send request
            try:
                with st.spinner("Evaluating..."):
                    r = requests.post(f"{API_BASE}/evaluate/short-answer", json=payload, headers=get_headers(), timeout=60)
                if r.status_code == 200:
                    result = r.json()
                    st.session_state["last_result"] = result
                    st.session_state["last_evaluation_id"] = None  # Need to get from response, but current API doesn't return it
                    st.success("Evaluation completed!")
                else:
                    st.error(f"API Error: {r.status_code} {r.text}")
            except Exception as e:
                st.error(f"Request failed: {e}")

    with col_res:
        st.markdown("### Result")
        res = st.session_state.get("last_result")
        if res:
            total_score = res.get("total_score")
            if total_score is not None:
                st.metric("Total Score (0-10)", f"{float(total_score):.2f}")

            st.subheader("Dimension Breakdown")
            dims = res.get("dimension_breakdown") or {}
            if dims:
                st.table([{"dimension": k, "score": v} for k, v in dims.items()])
            else:
                st.info("No dimension data returned.")

            st.subheader("Key Points Evaluation")
            for i, kp in enumerate(res.get("key_points_evaluation") or [], 1):
                st.write(f"{i}. {kp}")

            st.subheader("Improvement Recommendations")
            for i, tip in enumerate(res.get("improvement_recommendations") or [], 1):
                st.write(f"{i}. {tip}")

            with st.expander("Raw JSON"):
                st.json(res)
        else:
            st.info("Waiting for evaluation results...")

elif page == "Evaluation List":
    st.title("Evaluation List")
    
    # Filter conditions
    col1, col2 = st.columns(2)
    with col1:
        filter_question_id = st.text_input("Question ID", value="")
    with col2:
        filter_student_id = st.text_input("Student ID", value="")
    
    col3, col4 = st.columns(2)
    with col3:
        limit = st.number_input("Items per page", min_value=1, max_value=100, value=20)
    with col4:
        offset = st.number_input("Offset", min_value=0, value=0)
    
    if st.button("Search", type="primary"):
        params = {"limit": limit, "offset": offset}
        if filter_question_id:
            params["question_id"] = filter_question_id
        if filter_student_id:
            params["student_id"] = filter_student_id
        
        try:
            with st.spinner("Loading..."):
                r = requests.get(f"{API_BASE}/evaluations", params=params, headers=get_headers(), timeout=10)
            if r.status_code == 200:
                data = r.json()
                st.session_state["evaluation_list"] = data
                st.success(f"Found {data['total']} records")
            else:
                st.error(f"API Error: {r.status_code} {r.text}")
        except Exception as e:
            st.error(f"Request failed: {e}")
    
    # Display list
    if "evaluation_list" in st.session_state:
        data = st.session_state["evaluation_list"]
        st.markdown(f"**Total: {data['total']} records**")
        
        if data["items"]:
            for item in data["items"]:
                with st.expander(f"Evaluation #{item['id']} - {item['question_id']} (Created: {item['created_at']})"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Auto Score", f"{item['auto_score']:.2f}" if item['auto_score'] else "N/A")
                    with col2:
                        st.metric("Final Score", f"{item['final_score']:.2f}" if item['final_score'] else "Not reviewed")
                    with col3:
                        if item['reviewer_id']:
                            st.caption(f"Reviewer: {item['reviewer_id']}")
                    
                    if st.button(f"View Details", key=f"detail_{item['id']}"):
                        st.session_state["selected_evaluation_id"] = item['id']
                        st.rerun()
        else:
            st.info("No evaluation results found")

elif page == "Evaluation Detail":
    st.title("Evaluation Detail")
    
    # Navigate from list page
    evaluation_id = st.session_state.get("selected_evaluation_id")
    if not evaluation_id:
        evaluation_id = st.number_input("Enter Evaluation ID", min_value=1, value=1)
    
    if st.button("Load Details", type="primary") or evaluation_id:
        try:
            with st.spinner("Loading..."):
                headers = {"X-User-Token": user_token}
                r = requests.get(f"{API_BASE}/evaluations/{evaluation_id}", headers=headers, timeout=10)
            if r.status_code == 200:
                detail = r.json()
                st.session_state["evaluation_detail"] = detail
            elif r.status_code == 404:
                st.error(f"Evaluation record {evaluation_id} does not exist")
            else:
                st.error(f"API Error: {r.status_code} {r.text}")
        except Exception as e:
            st.error(f"Request failed: {e}")
    
    # Display details
    if "evaluation_detail" in st.session_state:
        detail = st.session_state["evaluation_detail"]
        
        # Basic information
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Auto Score", f"{detail['auto_score']:.2f}" if detail['auto_score'] else "N/A")
        with col2:
            st.metric("Final Score", f"{detail['final_score']:.2f}" if detail['final_score'] else "Not reviewed")
        
        st.markdown("---")
        
        # Question and answer
        st.subheader("Question Information")
        st.write(f"**Question ID:** {detail['question_id']}")
        if detail['student_id']:
            st.write(f"**Student ID:** {detail['student_id']}")
        
        st.subheader("Student Answer")
        st.text_area("Answer Content", value=detail['student_answer'], height=150, disabled=True)
        
        # Scoring details
        if detail['dimension_scores_json']:
            st.subheader("Dimension Scores")
            st.table([{"Dimension": k, "Score": v} for k, v in detail['dimension_scores_json'].items()])
        
        # Model information
        if detail['model_version']:
            st.subheader("Model Information")
            st.write(f"**Model Version:** {detail['model_version']}")
            st.write(f"**Rubric Version:** {detail['rubric_version']}")
        
        # Teacher review (only visible to teachers)
        if user_role == "teacher":
            st.markdown("---")
            st.subheader("Teacher Review")
            
            with st.form("review_form"):
                final_score = st.number_input(
                    "Final Score",
                    min_value=0.0,
                    max_value=10.0,
                    value=float(detail['final_score']) if detail['final_score'] else float(detail['auto_score']) if detail['auto_score'] else 0.0,
                    step=0.1
                )
                review_notes = st.text_area("Review Notes", value=detail.get('review_notes', ''), height=100)
                
                submitted = st.form_submit_button("Save Review", type="primary")
                
                if submitted:
                    payload = {
                        "evaluation_id": detail['id'],
                        "final_score": final_score,
                        "review_notes": review_notes if review_notes else None
                    }
                    try:
                        with st.spinner("Saving..."):
                            headers = {"X-User-Token": user_token}
                            r = requests.post(f"{API_BASE}/review/save", json=payload, headers=headers, timeout=10)
                        if r.status_code == 200:
                            result = r.json()
                            st.success(f"Review saved! Auto score: {result['auto_score']:.2f}, Final score: {result['final_score']:.2f}")
                            # Clear cache and reload
                            if "evaluation_detail" in st.session_state:
                                del st.session_state["evaluation_detail"]
                            st.rerun()
                        else:
                            st.error(f"Save failed: {r.status_code} {r.text}")
                    except Exception as e:
                        st.error(f"Request failed: {e}")
        
        # Display existing review information
        if detail.get('review_notes'):
            st.info(f"**Existing Notes:** {detail['review_notes']}")
        
        # Raw output
        with st.expander("Raw LLM Output"):
            st.json(detail.get('raw_llm_output', {}))

elif page == "Question Management":
    st.title("Question Management")
    
    try:
        headers = get_headers()
        r = requests.get(f"{API_BASE}/questions", params={"limit": 100}, headers=headers, timeout=10)
        
        if r.status_code == 200:
            questions_data = r.json()
            questions = questions_data.get("items", [])
            st.success(f"Found {questions_data.get('total', 0)} questions")
        else:
            st.error(f"Failed to load question list: {r.status_code} {r.text}")
            questions = []
    except Exception as e:
        st.error(f"Request failed: {e}")
        questions = []
    
    # Display question list
    if questions:
        st.subheader("Question List")
        for q in questions:
            with st.expander(f"{q['question_id']} - {q.get('topic', 'N/A')}"):
                st.write(f"**Question Text:** {q['text']}")
                st.caption(f"Created: {q.get('created_at', 'N/A')}")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"View Details", key=f"q_detail_{q['question_id']}"):
                        st.session_state["selected_question_id"] = q['question_id']
                        st.rerun()
                with col2:
                    if st.button(f"Delete", key=f"q_delete_{q['question_id']}"):
                        try:
                            headers = get_headers()
                            r = requests.delete(f"{API_BASE}/questions/{q['question_id']}", headers=headers, timeout=10)
                            if r.status_code == 204:
                                st.success("Question deleted")
                                st.rerun()
                            else:
                                st.error(f"Delete failed: {r.status_code} {r.text}")
                        except Exception as e:
                            st.error(f"Delete failed: {e}")
    else:
        st.info("No questions available")
    
    # Create new question
    st.markdown("---")
    st.subheader("Create New Question")
    with st.form("create_question_form"):
        question_id = st.text_input("Question ID", placeholder="e.g., Q2106")
        question_text = st.text_area("Question Text", height=100, placeholder="Enter question content...")
        topic = st.text_input("Topic", placeholder="e.g., airflow")
        
        submitted = st.form_submit_button("Create Question", type="primary")
        
        if submitted:
            if not question_id or not question_text or not topic:
                st.error("Please fill in all required fields")
            else:
                try:
                    payload = {
                        "question_id": question_id,
                        "text": question_text,
                        "topic": topic
                    }
                    headers = get_headers()
                    r = requests.post(f"{API_BASE}/questions", json=payload, headers=headers, timeout=10)
                    if r.status_code == 201:
                        st.success("Question created successfully!")
                        st.rerun()
                    else:
                        st.error(f"Creation failed: {r.status_code} {r.text}")
                except Exception as e:
                    st.error(f"Creation failed: {e}")

elif page == "Rubric Management":
    st.title("Rubric Management")
    
    # Select question
    st.subheader("Select Question")
    try:
        headers = get_headers()
        r = requests.get(f"{API_BASE}/questions", params={"limit": 100}, headers=headers, timeout=10)
        if r.status_code == 200:
            questions_data = r.json()
            questions = questions_data.get("items", [])
            if questions:
                question_options = {f"{q['question_id']} - {q.get('topic', 'N/A')}": q['question_id'] for q in questions}
                selected_label = st.selectbox("Select Question", list(question_options.keys()))
                selected_question_id = question_options[selected_label]
            else:
                st.warning("No questions available, please create a question first")
                selected_question_id = None
        else:
            st.error(f"Failed to load question list: {r.status_code}")
            selected_question_id = None
    except Exception as e:
        st.error(f"Failed to load question list: {e}")
        selected_question_id = None
    
    if selected_question_id:
        # Display rubric list for this question
        st.markdown("---")
        st.subheader(f"Rubrics for Question {selected_question_id}")
        
        try:
            headers = get_headers()
            r = requests.get(f"{API_BASE}/questions/{selected_question_id}/rubrics", headers=headers, timeout=10)
            
            if r.status_code == 200:
                rubrics_data = r.json()
                rubrics = rubrics_data.get("items", [])
                
                if rubrics:
                    for rubric in rubrics:
                        with st.expander(f"Version: {rubric['version']} {'Active' if rubric['is_active'] else 'Inactive'}"):
                            st.write(f"**Created By:** {rubric.get('created_by', 'N/A')}")
                            st.write(f"**Created At:** {rubric.get('created_at', 'N/A')}")
                            
                            # View details
                            if st.button(f"View Details", key=f"r_detail_{rubric['id']}"):
                                try:
                                    headers = get_headers()
                                    r_detail = requests.get(f"{API_BASE}/rubrics/{rubric['id']}", headers=headers, timeout=10)
                                    if r_detail.status_code == 200:
                                        detail = r_detail.json()
                                        st.json(detail.get('rubric_json', {}))
                                    else:
                                        st.error(f"Failed to load details: {r_detail.status_code}")
                                except Exception as e:
                                    st.error(f"Failed to load details: {e}")
                            
                            # Activate/Deactivate
                            if not rubric['is_active']:
                                if st.button(f"Activate", key=f"r_activate_{rubric['id']}"):
                                    try:
                                        headers = get_headers()
                                        r_activate = requests.post(f"{API_BASE}/rubrics/{rubric['id']}/activate", headers=headers, timeout=10)
                                        if r_activate.status_code == 200:
                                            st.success("Rubric activated")
                                            st.rerun()
                                        else:
                                            st.error(f"Activation failed: {r_activate.status_code} {r_activate.text}")
                                    except Exception as e:
                                        st.error(f"Activation failed: {e}")
                else:
                    st.info("No rubrics available for this question")
            else:
                st.error(f"Failed to load rubric list: {r.status_code} {r.text}")
        except Exception as e:
            st.error(f"Failed to load rubric list: {e}")
        
        # Create new rubric
        st.markdown("---")
        st.subheader("Create New Rubric")
        with st.form("create_rubric_form"):
            version = st.text_input("Version", placeholder="e.g., v1.0")
            is_active = st.checkbox("Activate this rubric", value=False)
            rubric_json_text = st.text_area("Rubric JSON", height=300, placeholder='{"version": "v1.0", "dimensions": {...}, "key_points": [...], "common_mistakes": [...]}')
            
            submitted = st.form_submit_button("Create Rubric", type="primary")
            
            if submitted:
                if not version or not rubric_json_text:
                    st.error("Please fill in version and rubric JSON")
                else:
                    try:
                        rubric_json = json.loads(rubric_json_text)
                        payload = {
                            "version": version,
                            "rubric_json": rubric_json,
                            "is_active": is_active
                        }
                        headers = get_headers()
                        r = requests.post(f"{API_BASE}/questions/{selected_question_id}/rubrics", json=payload, headers=headers, timeout=10)
                        if r.status_code == 201:
                            st.success("Rubric created successfully!")
                            st.rerun()
                        else:
                            st.error(f"Creation failed: {r.status_code} {r.text}")
                    except json.JSONDecodeError as e:
                        st.error(f"JSON format error: {e}")
                    except Exception as e:
                        st.error(f"Creation failed: {e}")
