from collections import Counter
from pathlib import Path

from app.modules.document_processing.reader import read_document
from app.modules.preprocessing.cleaner import preprocess
from app.modules.chunking.chunker import chunk_sentences
from app.modules.mcq_generator.generator import generate_mcqs
from app.modules.validation.post_validator import validate_mcq, SemanticVerifier
from app.modules.deduplication.detector import find_duplicates


def run_pipeline(
    file_path,
    num_questions_per_chunk: int = 2,
    max_chunks: int | None = None,
    strict_validation: bool = False,
    dedup_threshold: float = 0.85,
    semantic_verifier: SemanticVerifier | None = None,
    include_headers_footers: bool = False,
) -> dict:
    """
    Trả về dict:
      - questions: list câu hỏi hợp lệ (đã dedup)
      - stats: thống kê tổng hợp
      - chunk_status: trạng thái từng chunk
      - duplicates: danh sách câu trùng bị loại
    """
    print(f"[1/4] Đọc file: {file_path}")
    raw = read_document(file_path, include_headers_footers=include_headers_footers)
    if not raw.strip():
        raise ValueError("Không trích xuất được nội dung từ file")

    print("[2/4] Tiền xử lý và tách câu...")
    sentences = preprocess(raw)
    print(f"     → {len(sentences)} câu")

    print("[3/4] Chunking...")
    chunks = chunk_sentences(sentences, max_tokens=200, overlap=1)
    if max_chunks:
        chunks = chunks[:max_chunks]
    print(f"     → {len(chunks)} chunk")

    print("[4/4] Gọi Gemini API...")
    raw_questions: list[dict] = []
    chunk_status: list[dict] = []
    reject_reasons: Counter = Counter()
    total_in = total_out = 0

    for i, chunk in enumerate(chunks, 1):
        print(f"  Chunk {i}/{len(chunks)}: {chunk['text'][:60]}...")
        status = {
            "chunk_index": i - 1,
            "chunk_preview": chunk["text"][:60],
            "start_sentence": chunk.get("start_sentence", 0),
            "end_sentence": chunk.get("end_sentence", 0),
        }

        # Gọi API
        result = generate_mcqs(chunk["text"], num_questions_per_chunk)
        total_in += result.tokens_in
        total_out += result.tokens_out

        if result.parsed is None:
            status.update({
                "status": "api_failed",
                "error_type": result.error_type,
                "accepted": 0,
                "rejected": 0,
            })
            chunk_status.append(status)
            print(f"    → Bỏ qua (lỗi {result.error_type})")
            continue

        accepted = rejected = 0
        for mcq in result.parsed.questions:
            ok, reason = validate_mcq(
                mcq, 
                chunk["sentences"], 
                strict=strict_validation,
                semantic_verifier=semantic_verifier  # Sẽ tự động gọi nli_semantic_verifier nếu strict=True
            )
            if ok:
                raw_questions.append({
                    "question": mcq.question,
                    "options": {opt.label: opt.text for opt in mcq.options},
                    "correct_answer_label": mcq.correct_answer_label,
                    "explanation": mcq.explanation,
                    "source": {
                        "chunk_index": i - 1,
                        "source_sentence": mcq.source_sentence,
                        "start_sentence": chunk.get("start_sentence", 0),
                        "end_sentence": chunk.get("end_sentence", 0),
                    },
                })
                accepted += 1
            else:
                rejected += 1
                reason_key = reason.split(":")[0].strip()
                reject_reasons[reason_key] += 1
                print(f"    [LOẠI] {reason}: {mcq.question[:60]}...")

        status.update({
            "status": "ok",
            "accepted": accepted,
            "rejected": rejected,
        })
        chunk_status.append(status)

    # Lọc trùng
    unique_questions, duplicates = find_duplicates(
        raw_questions, threshold=dedup_threshold
    )

    stats = {
        "total_sentences": len(sentences),
        "total_chunks": len(chunks),
        "chunks_ok": sum(1 for c in chunk_status if c["status"] == "ok"),
        "chunks_failed": sum(1 for c in chunk_status if c["status"] == "api_failed"),
        "raw_questions": len(raw_questions),
        "unique_questions": len(unique_questions),
        "duplicates_removed": len(duplicates),
        "validation_rejects": dict(reject_reasons),
        "total_rejected": sum(reject_reasons.values()),
        "tokens_in": total_in,
        "tokens_out": total_out,
    }

    print(
        f"\n✅ Hoàn tất: {len(unique_questions)} câu hợp lệ "
        f"(thô: {len(raw_questions)}, trùng: {len(duplicates)}, "
        f"loại validation: {stats['total_rejected']})"
    )

    return {
        "questions": unique_questions,
        "stats": stats,
        "chunk_status": chunk_status,
        "duplicates": duplicates,
    }