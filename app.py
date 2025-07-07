import streamlit as st
import json
import os
import random
from PIL import Image
import pandas as pd
from streamlit.components.v1 import html
import time
from streamlit_autorefresh import st_autorefresh

# === CẤU HÌNH ===
IMAGE_DIR = "images"
JSON_FILE = "questions.json"
EXAM_DURATION_MINUTES = 30
NUM_QUESTIONS = 40

# === TIỆN ÍCH ===
def load_questions(json_file):
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    modules = list(data.items())  # list of (module_name, questions)
    total_modules = len(modules)
    per_module = NUM_QUESTIONS // total_modules
    remainder = NUM_QUESTIONS % total_modules

    selected_questions = []
    for i, (module_name, questions) in enumerate(modules):
        num_questions = per_module + (1 if i < remainder else 0)
        chosen = random.sample(questions, min(num_questions, len(questions)))
        for q in chosen:
            q["module"] = module_name  # gắn thẻ module
        selected_questions.extend(chosen)

    random.shuffle(selected_questions)
    return selected_questions

def clean_question_text(text):
    if ":" in text:
        return text.split(":", 1)[1].strip()
    return text

def parse_text_with_image(text):
    if "[IMG:" in text:
        before_img = text.split("[IMG:")[0].strip()
        img_name = text.split("[IMG:")[1].split("]")[0].strip()
        after_img = text.split("]")[-1].strip()
        img_path = os.path.join(IMAGE_DIR, img_name)
        return before_img, img_path, after_img
    return text, None, None

def update_sidebar_state(idx):
    st.session_state.answers[idx] = st.session_state[f"select_q_{idx}"]

def show_question(idx, q):
    st.markdown(f"<a name='cau_{idx}'></a>", unsafe_allow_html=True)
    raw_question = clean_question_text(q["question"])
    before_img, img_path, after_img = parse_text_with_image(raw_question)

    st.markdown(f"### Câu {idx+1}: {before_img}")
    if img_path and os.path.exists(img_path):
        st.image(Image.open(img_path))
    if after_img:
        st.markdown(after_img)

    valid_options = [
        opt for opt in q["options"]
        if opt.get("label", "").strip() and opt.get("text", "").strip()
    ]

    labels = []
    for opt in valid_options:
        label = opt["label"]
        labels.append(label)
        before, img, after = parse_text_with_image(opt["text"])
        col1, col2 = st.columns([0.05, 0.95])
        with col1:
            st.markdown(f"**{label}.**")
        with col2:
            if before:
                st.markdown(before)
            if img and os.path.exists(img):
                st.image(Image.open(img))
            if after:
                st.markdown(after)

    current = st.session_state.answers[idx]
    disabled = st.session_state.get("submitted", False) or st.session_state.get("submitted_early", False)
    st.selectbox(
        "📌 Chọn đáp án đúng:",
        options=[""] + labels,
        index=labels.index(current) + 1 if current in labels else 0,
        key=f"select_q_{idx}",
        on_change=update_sidebar_state,
        args=(idx,),
        disabled=disabled
    )

def submit_exam():
    results = []
    correct_count = 0

    for idx, q in enumerate(st.session_state.selected_questions):
        selected_label = st.session_state.answers[idx]
        valid_options = [opt for opt in q["options"] if opt.get("label", "").strip() and opt.get("text", "").strip()]
        correct_label = next((opt["label"] for opt in valid_options if opt.get("is_correct", False)), "")
        is_correct = (selected_label == correct_label)
        if is_correct:
            correct_count += 1
        results.append({
            "Câu": f"Câu {idx+1}",
            "Module": q.get("module", ""),
            "Câu hỏi": clean_question_text(q["question"]),
            "Đáp án đã chọn": selected_label if selected_label else "—",
            "Đáp án đúng": correct_label,
            "Kết quả": "✅ Đúng" if is_correct else "❌ Sai"
        })

    score = round(correct_count * 10 / len(st.session_state.selected_questions), 1)
    st.success(f"✅ Bạn đã làm đúng {correct_count}/{len(st.session_state.selected_questions)} câu. Điểm: **{score}/10**")

    df = pd.DataFrame(results)
    st.dataframe(df, use_container_width=True)

    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("📄 Tải kết quả về (.csv)", data=csv, file_name="ket_qua_thi_thu.csv", mime="text/csv")

def exam_mode(questions):
    st_autorefresh(interval=1000, key="auto-refresh")
    st.title("👩‍🎓 Thi thử môn Chứng chỉ Tin học")

    if "start_time" not in st.session_state:
        st.session_state.start_time = time.time()

    time_left = int(EXAM_DURATION_MINUTES * 60 - (time.time() - st.session_state.start_time))
    minutes = time_left // 60
    seconds = time_left % 60
    if time_left > 0:
        st.markdown(f"### ⏰ Thời gian còn lại: **{minutes:02d}:{seconds:02d}**")
    else:
        if not st.session_state.get("submitted") and not st.session_state.get("submitted_early"):
            st.session_state.submitted = True
        st.warning("⏱ Hết thời gian làm bài! Đã tự động nộp bài.")

    st.divider()

    if "selected_questions" not in st.session_state:
        st.session_state.selected_questions = questions
    if "answers" not in st.session_state:
        st.session_state.answers = [""] * len(st.session_state.selected_questions)
    if "submitted" not in st.session_state:
        st.session_state.submitted = False
    if "submitted_early" not in st.session_state:
        st.session_state.submitted_early = False

    st.sidebar.markdown("### 🧾 Bảng câu hỏi")
    for idx in range(len(st.session_state.selected_questions)):
        status = "✅" if st.session_state.answers[idx] else "❌"
        st.sidebar.markdown(
            f"<a href='#cau_{idx}' style='text-decoration: none; font-size: 16px;'>{status} Câu {idx+1}</a>",
            unsafe_allow_html=True
        )

    st.sidebar.markdown("---")
    if st.session_state.submitted or st.session_state.submitted_early:
        st.sidebar.button("📝 Nộp bài sớm", disabled=True)
    else:
        if st.sidebar.button("📝 Nộp bài sớm"):
            st.session_state.submitted_early = True
            st.rerun()

    for idx, q in enumerate(st.session_state.selected_questions):
        show_question(idx, q)
        st.divider()

    if st.session_state.submitted or st.session_state.submitted_early:
        st.button("📝 Nộp bài", disabled=True)
    else:
        if st.button("📝 Nộp bài"):
            st.session_state.submitted = True

    if st.session_state.submitted_early:
        st.markdown("## 📊 Kết quả bài thi (Nộp sớm)")
        submit_exam()

    if st.session_state.submitted:
        st.markdown("## 📊 Kết quả bài thi")
        submit_exam()

def main():
    st.set_page_config(page_title="Thi thử Tin học", layout="wide")
    questions = load_questions(JSON_FILE)
    exam_mode(questions)

if __name__ == "__main__":
    main()
