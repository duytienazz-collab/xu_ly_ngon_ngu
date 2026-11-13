import re
import unicodedata
from difflib import SequenceMatcher
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# Import client từ config để tạo embedding
from app.core.config import client


def _normalize(s: str) -> str:
    s = unicodedata.normalize("NFC", s).lower()
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"[^\w\s]", "", s)
    return s


def is_exact_duplicate(q1: str, q2: str) -> bool:
    return _normalize(q1) == _normalize(q2)


def surface_similarity_ratio(q1: str, q2: str) -> float:
    """So khớp chuỗi ký tự bề mặt (fallback)."""
    return SequenceMatcher(None, _normalize(q1), _normalize(q2)).ratio()


def get_embeddings(texts: list[str]) -> list[list[float]] | None:
    """
    Sinh vector ngữ nghĩa bằng mô hình embedding chính thức của Gemini.
    Tự động thử 'gemini-embedding-001' (chuẩn v1) hoặc fallback sang v1beta.
    """
    if not texts:
        return []
    
    # 1. Thử mô hình chuẩn chính thức trên v1
    for model_name in ["gemini-embedding-001", "text-embedding-004"]:
        try:
            response = client.models.embed_content(
                model=model_name,
                contents=texts,
            )
            # Trích xuất danh sách vector từ response
            if hasattr(response, "embeddings") and response.embeddings:
                return [item.values for item in response.embeddings]
            if hasattr(response, "embedding") and response.embedding:
                return [response.embedding.values]
        except Exception as e:
            continue  # Nếu model này không khớp version, thử model tiếp theo

    print("[WARN] Cả 2 model embedding đều không phản hồi, tự động dùng so khớp ký tự.")
    return None


def find_duplicates(
    questions: list[dict],
    threshold: float = 0.88,
) -> tuple[list[dict], list[dict]]:
    """
    Khử trùng lặp 2 tầng:
    - Tầng 1: Exact Match (trùng chữ 100%).
    - Tầng 2: Semantic Embedding (đo Cosine Similarity giữa 2 vector câu hỏi).
    """
    if not questions:
        return [], []

    # 1. Tách trùng lặp tuyệt đối trước
    unique_candidates: list[dict] = []
    duplicates: list[dict] = []
    
    for i, q in enumerate(questions):
        is_exact = False
        for j, prev in enumerate(unique_candidates):
            if is_exact_duplicate(q["question"], prev["question"]):
                duplicates.append({
                    "original_index": i,
                    "duplicate_of": j,
                    "reason": "exact_match",
                    "question": q["question"],
                })
                is_exact = True
                break
        if not is_exact:
            unique_candidates.append(q)

    if len(unique_candidates) <= 1:
        return unique_candidates, duplicates

    # 2. Lấy Embedding cho toàn bộ câu hỏi độc nhất còn lại
    q_texts = [q["question"] for q in unique_candidates]
    vectors = get_embeddings(q_texts)

    unique: list[dict] = []
    kept_indices: list[int] = []

    for idx, q in enumerate(unique_candidates):
        is_dup = False
        
        # Nếu có vector embedding -> tính Cosine Similarity ngữ nghĩa
        if vectors is not None:
            curr_vec = np.array(vectors[idx]).reshape(1, -1)
            for prev_idx in kept_indices:
                prev_vec = np.array(vectors[prev_idx]).reshape(1, -1)
                sim = float(cosine_similarity(curr_vec, prev_vec)[0][0])
                if sim >= threshold:
                    duplicates.append({
                        "original_index": idx,
                        "duplicate_of": prev_idx,
                        "reason": f"semantic_embedding (cosine={sim:.3f})",
                        "question": q["question"],
                    })
                    is_dup = True
                    break
        else:
            # Fallback nếu không có mạng/lỗi API: dùng SequenceMatcher
            for prev_idx in kept_indices:
                sim = surface_similarity_ratio(q["question"], unique_candidates[prev_idx]["question"])
                if sim >= threshold:
                    duplicates.append({
                        "original_index": idx,
                        "duplicate_of": prev_idx,
                        "reason": f"surface_similarity (sim={sim:.3f})",
                        "question": q["question"],
                    })
                    is_dup = True
                    break

        if not is_dup:
            kept_indices.append(idx)
            unique.append(q)

    return unique, duplicates