import json
import csv
from datetime import datetime
from pathlib import Path
from docx import Document


def export_json(questions: list[dict], out_path, metadata: dict | None = None) -> Path:
    out_path = Path(out_path)
    payload = {"metadata": metadata or {}, "questions": questions}
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return out_path


def export_csv(questions: list[dict], out_path, metadata: dict | None = None) -> Path:
    out_path = Path(out_path)
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        if metadata:
            writer.writerow(["# Metadata"])
            for k, v in metadata.items():
                writer.writerow([k, json.dumps(v, ensure_ascii=False)])
            writer.writerow([])
        writer.writerow([
            "STT", "Câu hỏi", "A", "B", "C", "D", "Đáp án",
            "Giải thích", "Chunk", "Source sentence",
        ])
        for i, q in enumerate(questions, 1):
            opts = q["options"]
            writer.writerow([
                i, q["question"],
                opts.get("A", ""), opts.get("B", ""), opts.get("C", ""), opts.get("D", ""),
                q["correct_answer_label"], q.get("explanation", ""),
                q["source"].get("chunk_index", ""),
                q["source"].get("source_sentence", ""),
            ])
    return out_path


def export_docx(questions: list[dict], out_path, metadata: dict | None = None) -> Path:
    out_path = Path(out_path)
    doc = Document()
    doc.add_heading("BỘ CÂU HỎI TRẮC NGHIỆM", level=1)

    if metadata:
        doc.add_heading("Thông tin nguồn", level=2)
        for k, v in metadata.items():
            if isinstance(v, (dict, list)):
                doc.add_paragraph(f"{k}: {json.dumps(v, ensure_ascii=False)}")
            else:
                doc.add_paragraph(f"{k}: {v}")
        doc.add_page_break()

    for i, q in enumerate(questions, 1):
        doc.add_paragraph(f"Câu {i}. {q['question']}")
        for label in ["A", "B", "C", "D"]:
            doc.add_paragraph(f"   {label}. {q['options'].get(label, '')}")
        doc.add_paragraph(f"→ Đáp án: {q['correct_answer_label']}")
        if q.get("explanation"):
            doc.add_paragraph(f"   Giải thích: {q['explanation']}")
        src = q.get("source", {})
        doc.add_paragraph(
            f"   Nguồn: chunk {src.get('chunk_index', '?')} — \"{src.get('source_sentence', '')}\""
        )
        doc.add_paragraph("")

    doc.save(str(out_path))
    return out_path