# ui/app.py
import os
import json
import streamlit as st
import requests
from dotenv import load_dotenv
from datetime import datetime

st.set_page_config(page_title="Answer Evaluator", layout="wide")

load_dotenv()

# 尝试从 secrets 或环境变量获取 API_BASE
try:
    API_BASE = st.secrets.get("API_BASE", None)
except (FileNotFoundError, AttributeError):
    API_BASE = None

API_BASE = API_BASE or os.getenv("API_BASE", "http://127.0.0.1:8000")

# 页面选择
page = st.sidebar.selectbox("页面", ["评估答案", "评估结果列表", "评估详情"])

# 加载题目列表（缓存60秒）
@st.cache_data(ttl=60)
def load_questions():
    """从API加载题目列表"""
    try:
        r = requests.get(f"{API_BASE}/questions", params={"limit": 100}, timeout=5)
        if r.status_code == 200:
            return r.json()["items"]
    except Exception as e:
        st.sidebar.warning(f"加载题目列表失败: {e}")
    return []

if page == "评估答案":
    with st.sidebar:
        st.title("Answer Evaluator")
        
        # 从数据库动态加载题目列表
        questions = load_questions()
        if questions:
            question_options = [q["question_id"] for q in questions]
            question_id = st.selectbox("Question ID", question_options)
            # 显示题目信息
            selected_question = next((q for q in questions if q["question_id"] == question_id), None)
            if selected_question:
                st.caption(f"主题: {selected_question.get('topic', 'N/A')}")
        else:
            # 回退到硬编码（如果API不可用）
            question_id = st.selectbox("Question ID", ["Q2105"])
            st.warning("无法加载题目列表，使用默认题目")
        
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
                "student_answer": student_answer
            }
            # 如果用户提供了评分标准，添加到 payload
            if with_rubric and rubric_text.strip():
                try:
                    payload["rubric_json"] = json.loads(rubric_text)
                except Exception as e:
                    st.error(f"Rubric JSON invalid: {e}")
                    st.stop()  # 停止执行，不发送请求
            try:
                with st.spinner("Evaluating..."):
                    r = requests.post(f"{API_BASE}/evaluate/short-answer", json=payload, timeout=60)
                if r.status_code == 200:
                    result = r.json()
                    st.session_state["last_result"] = result
                    st.session_state["last_evaluation_id"] = None  # 需要从响应中获取，但当前API不返回
                    st.success("评估完成！")
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
        else:
            st.info("等待评估结果…")

elif page == "评估结果列表":
    st.title("📋 评估结果列表")
    
    # 筛选条件
    col1, col2 = st.columns(2)
    with col1:
        filter_question_id = st.text_input("题目 ID", value="")
    with col2:
        filter_student_id = st.text_input("学生 ID", value="")
    
    col3, col4 = st.columns(2)
    with col3:
        limit = st.number_input("每页数量", min_value=1, max_value=100, value=20)
    with col4:
        offset = st.number_input("偏移量", min_value=0, value=0)
    
    if st.button("查询", type="primary"):
        params = {"limit": limit, "offset": offset}
        if filter_question_id:
            params["question_id"] = filter_question_id
        if filter_student_id:
            params["student_id"] = filter_student_id
        
        try:
            with st.spinner("加载中..."):
                r = requests.get(f"{API_BASE}/evaluations", params=params, timeout=10)
            if r.status_code == 200:
                data = r.json()
                st.session_state["evaluation_list"] = data
                st.success(f"找到 {data['total']} 条记录")
            else:
                st.error(f"API Error: {r.status_code} {r.text}")
        except Exception as e:
            st.error(f"Request failed: {e}")
    
    # 显示列表
    if "evaluation_list" in st.session_state:
        data = st.session_state["evaluation_list"]
        st.markdown(f"**总计: {data['total']} 条记录**")
        
        if data["items"]:
            for item in data["items"]:
                with st.expander(f"评估 #{item['id']} - {item['question_id']} (创建时间: {item['created_at']})"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("自动评分", f"{item['auto_score']:.2f}" if item['auto_score'] else "N/A")
                    with col2:
                        st.metric("最终评分", f"{item['final_score']:.2f}" if item['final_score'] else "未审核")
                    with col3:
                        if item['reviewer_id']:
                            st.caption(f"审核人: {item['reviewer_id']}")
                    
                    if st.button(f"查看详情", key=f"detail_{item['id']}"):
                        st.session_state["selected_evaluation_id"] = item['id']
                        st.rerun()
        else:
            st.info("没有找到评估结果")

elif page == "评估详情":
    st.title("📄 评估详情")
    
    # 从列表页面跳转
    evaluation_id = st.session_state.get("selected_evaluation_id")
    if not evaluation_id:
        evaluation_id = st.number_input("输入评估 ID", min_value=1, value=1)
    
    if st.button("加载详情", type="primary") or evaluation_id:
        try:
            with st.spinner("加载中..."):
                r = requests.get(f"{API_BASE}/evaluations/{evaluation_id}", timeout=10)
            if r.status_code == 200:
                detail = r.json()
                st.session_state["evaluation_detail"] = detail
            elif r.status_code == 404:
                st.error(f"评估记录 {evaluation_id} 不存在")
            else:
                st.error(f"API Error: {r.status_code} {r.text}")
        except Exception as e:
            st.error(f"Request failed: {e}")
    
    # 显示详情
    if "evaluation_detail" in st.session_state:
        detail = st.session_state["evaluation_detail"]
        
        # 基本信息
        col1, col2 = st.columns(2)
        with col1:
            st.metric("自动评分", f"{detail['auto_score']:.2f}" if detail['auto_score'] else "N/A")
        with col2:
            st.metric("最终评分", f"{detail['final_score']:.2f}" if detail['final_score'] else "未审核")
        
        st.markdown("---")
        
        # 题目和答案
        st.subheader("题目信息")
        st.write(f"**题目 ID:** {detail['question_id']}")
        if detail['student_id']:
            st.write(f"**学生 ID:** {detail['student_id']}")
        
        st.subheader("学生答案")
        st.text_area("答案内容", value=detail['student_answer'], height=150, disabled=True)
        
        # 评分详情
        if detail['dimension_scores_json']:
            st.subheader("维度评分")
            st.table([{"维度": k, "得分": v} for k, v in detail['dimension_scores_json'].items()])
        
        # 模型信息
        if detail['model_version']:
            st.subheader("模型信息")
            st.write(f"**模型版本:** {detail['model_version']}")
            st.write(f"**评分标准版本:** {detail['rubric_version']}")
        
        # 教师审核
        st.markdown("---")
        st.subheader("教师审核")
        
        with st.form("review_form"):
            final_score = st.number_input(
                "最终评分",
                min_value=0.0,
                max_value=10.0,
                value=float(detail['final_score']) if detail['final_score'] else float(detail['auto_score']) if detail['auto_score'] else 0.0,
                step=0.1
            )
            reviewer_id = st.text_input("审核人 ID", value=detail.get('reviewer_id', ''))
            review_notes = st.text_area("审核备注", value=detail.get('review_notes', ''), height=100)
            
            submitted = st.form_submit_button("保存审核", type="primary")
            
            if submitted:
                payload = {
                    "evaluation_id": detail['id'],
                    "final_score": final_score,
                    "reviewer_id": reviewer_id if reviewer_id else None,
                    "review_notes": review_notes if review_notes else None
                }
                try:
                    with st.spinner("保存中..."):
                        r = requests.post(f"{API_BASE}/review/save", json=payload, timeout=10)
                    if r.status_code == 200:
                        result = r.json()
                        st.success(f"审核已保存！自动评分: {result['auto_score']:.2f}, 最终评分: {result['final_score']:.2f}")
                        # 清除缓存，重新加载
                        if "evaluation_detail" in st.session_state:
                            del st.session_state["evaluation_detail"]
                        st.rerun()
                    else:
                        st.error(f"保存失败: {r.status_code} {r.text}")
                except Exception as e:
                    st.error(f"Request failed: {e}")
        
        # 显示现有审核信息
        if detail.get('review_notes'):
            st.info(f"**现有备注:** {detail['review_notes']}")
        
        # 原始输出
        with st.expander("原始 LLM 输出"):
            st.json(detail.get('raw_llm_output', {}))
