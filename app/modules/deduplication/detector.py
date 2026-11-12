import re
import unicodedata
from difflib import SequenceMatcher


def _normalize(s: str) -> str:
    s = unicodedata.normalize("NFC", s).lower()
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"[^\w\s]", "", s)
    return s


def is_exact_duplicate(q1: str, q2: str) -> bool:
    return _normalize(q1) == _normalize(q2)


def similarity_ratio(q1: str, q2: str) -> float:
    return SequenceMatcher(None, _normalize(q1), _normalize(q2)).ratio()


def find_duplicates(
    questions: list[dict],
    threshold: float = 0.85,
) -> tuple[list[dict], list[dict]]:
    """
    Trả về (unique_questions, duplicate_pairs).
    - Exact duplicate luôn bị loại.
    - Semantic duplicate: similarity_ratio >= threshold.
    """
    unique: list[dict] = []
    duplicates: list[dict] = []

    for i, q in enumerate(questions):
        is_dup = False
        for j, prev in enumerate(unique):
            if is_exact_duplicate(q["question"], prev["question"]):
                duplicates.append({
                    "original_index": i,
                    "duplicate_of": j,
                    "reason": "exact",
                    "question": q["question"],
                })
                is_dup = True
                break
            sim = similarity_ratio(q["question"], prev["question"])
            if sim >= threshold:
                duplicates.append({
                    "original_index": i,
                    "duplicate_of": j,
                    "reason": f"semantic (sim={sim:.3f})",
                    "question": q["question"],
                })
                is_dup = True
                break
        if not is_dup:
            unique.append(q)

    return unique, duplicates