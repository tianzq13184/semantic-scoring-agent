# ui/app.py
import os
import json
import streamlit as st
import requests
from dotenv import load_dotenv

st.set_page_config(page_title="Answer Evaluator", layout="wide")

load_dotenv()

try:
    API_BASE = st.secrets.get("API_BASE")
except FileNotFoundError:
    API_BASE = None

API_BASE = API_BASE or os.getenv("API_BASE", "http://127.0.0.1:8000")

with st.sidebar:
    st.title("Answer Evaluator")
    question_id = st.selectbox("Question ID", ["Q2105"])
    with_rubric = st.checkbox("I already have a rubric JSON", value=False)
    rubric_text = ""
    if with_rubric:
        rubric_text = st.text_area("Paste rubric JSON", height=180, placeholder='{"version":"manual-v1", ...}')

st.markdown("### ✍️ Candidate Answer")
student_answer = st.text_area("Write your answer here", height=220, placeholder="I will use Airflow to schedule jobs...")
has_answer = bool(student_answer.strip())
if not has_answer:
    st.caption("Answer is required before running evaluation.")

col_run, col_res = st.columns([1,2])

with col_run:
    if st.button("Evaluate", type="primary", use_container_width=True, disabled=not has_answer):
        payload = {
            "question_id": question_id,
            "student_answer": student_answer,
            "with_rubric": bool(with_rubric)
        }
        if with_rubric and rubric_text.strip():
            try:
                payload["rubric_json"] = json.loads(rubric_text)
            except Exception as e:
                st.error(f"Rubric JSON invalid: {e}")
        try:
            with st.spinner("Evaluating..."):
                r = requests.post(f"{API_BASE}/evaluate/short-answer", json=payload, timeout=60)
            if r.status_code == 200:
                st.session_state["last_result"] = r.json()
            else:
                st.error(f"API Error: {r.status_code} {r.text}")
        except Exception as e:
            st.error(f"Request failed: {e}")

with col_res:
    st.markdown("### 📊 Result")
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

        st.divider()
        st.subheader("Teacher Override (Preview)")
        final = st.number_input("Final score (optional)", min_value=0.0, max_value=10.0, step=0.5)
        st.caption("👉 今天先不上写回接口，明天加 /review/save。")
    else:
        st.info("等待评估结果…")
