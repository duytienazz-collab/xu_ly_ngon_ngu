import io
import csv
import json
import uuid
import tempfile
from datetime import datetime
from pathlib import Path

import streamlit as st
from docx import Document

from app.services.pipeline_service import run_pipeline

st.set_page_config(page_title="Text-to-MCQ Generator", page_icon="📝", layout="wide")
st.title("📝 Text-to-MCQ Generator (Gemini API)")

# --------- Session state ---------
if "result" not in st.session_state:
    st.session_state["result"] = None
if "processed_file" not in st.session_state:
    st.session_state["processed_file"] = None
if "session_id" not in st.session_state:
    # #23: ID riêng cho mỗi session → không đè file của nhau
    st.session_state["session_id"] = uuid.uuid4().hex[:8]

# --------- Sidebar ---------
st.sidebar.header("⚙️ Cấu hình")
num_per_chunk = st.sidebar.slider("Số câu / chunk", 1, 5, 2)
max_chunks = st.sidebar.slider("Giới hạn chunk", 1, 20, 3)
strict = st.sidebar.checkbox("Kiểm tra nghiêm ngặt", value=False)
dedup_thr = st.sidebar.slider("Ngưỡng lọc trùng", 0.5, 1.0, 0.85, 0.05)

uploaded = st.file_uploader("Tải tài liệu (PDF, DOCX, TXT)", type=["pdf", "docx", "txt"])

if uploaded and st.button("🚀 Bắt đầu tạo câu hỏi", type="primary"):
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=Path(uploaded.name).suffix
        ) as tmp:
            tmp.write(uploaded.read())
            tmp_path = tmp.name

        with st.spinner("Đang xử lý..."):
            result = run_pipeline(
                tmp_path,
                num_questions_per_chunk=num_per_chunk,
                max_chunks=max_chunks,
                strict_validation=strict,
                dedup_threshold=dedup_thr,
            )
        st.session_state["result"] = result
        st.session_state["processed_file"] = uploaded.name
    except Exception as e:
        st.error(f"Lỗi: {e}")
    finally:
        # #22: dọn file tạm dù thành công hay thất bại
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)

# --------- Render kết quả ---------
result = st.session_state["result"]

if result and result["questions"]:
    questions = result["questions"]
    stats = result["stats"]

    st.success(
        f"Đã tạo **{len(questions)} câu hỏi** từ **{st.session_state['processed_file']}**"
    )

    # Metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Câu hỏi thô", stats["raw_questions"])
    c2.metric("Sau lọc trùng", stats["unique_questions"])
    c3.metric("Bị loại (validate)", stats["total_rejected"])
    c4.metric("Chunk lỗi API", stats["chunks_failed"])

    with st.expander("📊 Chi tiết thống kê"):
        st.json(stats)
        if result.get("duplicates"):
            st.write("Câu trùng bị loại:")
            st.json(result["duplicates"])
        if result.get("chunk_status"):
            st.write("Trạng thái từng chunk:")
            st.json(result["chunk_status"])

    st.divider()

    for i, q in enumerate(questions, 1):
        with st.expander(f"Câu {i}. {q['question']}", expanded=True):
            for label in ["A", "B", "C", "D"]:
                marker = " ✅" if label == q["correct_answer_label"] else ""
                st.write(f"**{label}.** {q['options'].get(label, '')}{marker}")
            st.caption(f"Giải thích: {q.get('explanation', '')}")
            st.caption(f"Nguồn: {q['source']['source_sentence']}")

    st.divider()
    st.subheader("📥 Xuất kết quả")

    metadata = {
        "session_id": st.session_state["session_id"],
        "source_file": st.session_state["processed_file"],
        "generated_at": datetime.now().isoformat(),
        "stats": stats,
    }

    # JSON
    json_bytes = json.dumps(
        {"metadata": metadata, "questions": questions},
        ensure_ascii=False, indent=2,
    ).encode("utf-8")

    # CSV
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["STT", "Câu hỏi", "A", "B", "C", "D", "Đáp án",
                "Giải thích", "Chunk", "Source sentence"])
    for i, q in enumerate(questions, 1):
        o = q["options"]
        w.writerow([
            i, q["question"],
            o.get("A", ""), o.get("B", ""), o.get("C", ""), o.get("D", ""),
            q["correct_answer_label"], q.get("explanation", ""),
            q["source"].get("chunk_index", ""),
            q["source"].get("source_sentence", ""),
        ])
    csv_bytes = buf.getvalue().encode("utf-8-sig")

    # DOCX
    doc = Document()
    doc.add_heading("BỘ CÂU HỎI TRẮC NGHIỆM", level=1)
    for k, v in metadata.items():
        doc.add_paragraph(f"{k}: {json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v}")
    doc.add_page_break()
    for i, q in enumerate(questions, 1):
        doc.add_paragraph(f"Câu {i}. {q['question']}")
        for label in ["A", "B", "C", "D"]:
            doc.add_paragraph(f"   {label}. {q['options'].get(label, '')}")
        doc.add_paragraph(f"→ Đáp án: {q['correct_answer_label']}")
        doc.add_paragraph(f"   Nguồn: {q['source']['source_sentence']}")
        doc.add_paragraph("")
    docx_buf = io.BytesIO()
    doc.save(docx_buf)

    prefix = f"{Path(st.session_state['processed_file']).stem}_{st.session_state['session_id']}"

    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button(
            "⬇️ JSON", json_bytes,
            file_name=f"{prefix}.json", mime="application/json",
            use_container_width=True,
        )
    with c2:
        st.download_button(
            "⬇️ CSV", csv_bytes,
            file_name=f"{prefix}.csv", mime="text/csv",
            use_container_width=True,
        )
    with c3:
        st.download_button(
            "⬇️ DOCX", docx_buf.getvalue(),
            file_name=f"{prefix}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )

    st.divider()
    if st.button("🗑️ Xóa kết quả và bắt đầu lại"):
        st.session_state["result"] = None
        st.session_state["processed_file"] = None
        st.rerun()