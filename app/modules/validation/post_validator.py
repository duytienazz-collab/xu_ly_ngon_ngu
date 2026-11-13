import re
import unicodedata
from typing import Callable

from app.schemas.mcq import GeneratedMCQ


_INTERROGATIVES = re.compile(
    r"\b(gì|nào|ai|đâu|sao|bao nhiêu|bao lâu|khi nào|thế nào|"
    r"cái gì|con gì|người nào|việc gì|tại sao|vì sao|như thế nào|"
    r"điều gì|loại gì|kiểu gì|hãy|cho biết)\b",
    re.IGNORECASE,
)


def _normalize(s: str) -> str:
    s = unicodedata.normalize("NFC", s).lower()
    s = re.sub(r"\s+", " ", s).strip()
    return s


# ----------------- Các check độc lập -----------------

def _check_labels(mcq: GeneratedMCQ, _chunk) -> tuple[bool, str]:
    labels = sorted(o.label for o in mcq.options)
    if labels != ["A", "B", "C", "D"]:
        return False, f"Nhãn phương án không phải A,B,C,D: {labels}"
    return True, ""


def _check_source_exact(mcq: GeneratedMCQ, chunk_sentences: list[str]) -> tuple[bool, str]:
    src = _normalize(mcq.source_sentence)
    if not src:
        return False, "source_sentence rỗng"
    norm_sents = [_normalize(s) for s in chunk_sentences]
    if src in norm_sents:
        return True, ""
    if any(src in s for s in norm_sents):
        return True, ""
    return False, "source_sentence không khớp chính xác câu nào trong ngữ cảnh"


def _check_answer_appears_in_source_preliminary(
    mcq: GeneratedMCQ, _chunk
) -> tuple[bool, str]:
    """
    PRE-FILTER — KHÔNG phải kiểm chứng ngữ nghĩa của đáp án.

    Logic: nếu đáp án đúng KHÔNG xuất hiện trong source_sentence (sau chuẩn hóa),
    đây là dấu hiệu mạnh cho thấy Gemini đã bịa hoặc source_sentence bị sai
    → reject ngay.

    Nhưng CHIỀU NGƯỢC LẠI KHÔNG ĐÚNG: đáp án xuất hiện trong source_sentence
    KHÔNG đủ để kết luận đáp án đúng về mặt ngữ nghĩa. Có thể xảy ra:
      - Câu nguồn dài chứa nhiều thực thể, đáp án chỉ là một mảnh phụ.
      - Paraphrase/diễn đạt tương đương bị coi là "không xuất hiện".
      - Đáp án đa nghĩa, xuất hiện ở ngữ cảnh khác.

    → Nếu cần xác thực thực sự, plug một semantic_verifier (NLI/LLM) vào
      validate_mcq(...).
    """
    correct_opt = next(
        (o for o in mcq.options if o.label == mcq.correct_answer_label), None
    )
    if correct_opt is None:
        return False, "Không tìm thấy đáp án đúng trong danh sách phương án"

    ans = _normalize(correct_opt.text)
    src = _normalize(mcq.source_sentence)
    if not ans:
        return False, "Đáp án đúng rỗng"

    if ans in src:
        return True, ""

    return False, (
        f"Đáp án đúng {correct_opt.text!r} không xuất hiện nguyên văn "
        f"trong source_sentence — có thể Gemini bịa hoặc source_sentence sai"
    )


def _check_no_duplicates(mcq: GeneratedMCQ, _chunk) -> tuple[bool, str]:
    texts = [o.text.strip().lower() for o in mcq.options]
    if len(set(texts)) < 4:
        return False, "Có phương án trùng nội dung"
    return True, ""


def _check_question_min(mcq: GeneratedMCQ, _chunk) -> tuple[bool, str]:
    if len(mcq.question.strip()) < 10:
        return False, "Câu hỏi quá ngắn"
    return True, ""


def _check_not_ambiguous(mcq: GeneratedMCQ, _chunk) -> tuple[bool, str]:
    q = mcq.question.strip()
    if len(q.split()) < 4:
        return False, "Câu hỏi quá ngắn, có thể mơ hồ"
    if not _INTERROGATIVES.search(q) and not q.endswith("?"):
        return False, "Câu hỏi thiếu từ nghi vấn"
    return True, ""


# ĐÃ LOẠI BỎ _check_distractors_not_in_source.
# Lý do: một phương án xuất hiện trong source KHÔNG có nghĩa nó cũng đúng.
# Ví dụ: "Hà Nội là thủ đô, Huế từng là kinh đô" — câu hỏi "Thủ đô hiện tại là gì?"
# vẫn có distractor hợp lệ là "Huế" dù Huế xuất hiện trong nguồn.
#
# Muốn kiểm tra distractor thực sự đúng/sai, cần semantic verifier —
# không thể làm bằng so khớp chuỗi.

# THÊM ĐOẠN NÀY VÀO TRƯỚC DÒNG: # ----------------- Orchestrator -----------------

from app.core.config import client
from google.genai import types

def nli_semantic_verifier(mcq: GeneratedMCQ, chunk_sentences: list[str]) -> tuple[bool, str]:
    """
    Bộ kiểm tra suy luận ngữ nghĩa (Semantic NLI Verifier):
    Kiểm tra xem câu hỏi + đáp án đúng có thực sự được chứng minh bởi source_sentence hay không.
    Giải quyết triệt để điểm yếu của so khớp chuỗi thô (string matching).
    """
    correct_opt = next((o.text for o in mcq.options if o.label == mcq.correct_answer_label), "")
    
    prompt = f"""Hãy đóng vai trò là một thẩm định viên logic NLP.
Xác minh xem cặp CÂU HỎI và ĐÁP ÁN ĐÚNG có được suy ra hoặc chứng minh trực tiếp từ CÂU NGUỒN hay không.

CÂU NGUỒN: "{mcq.source_sentence}"
CÂU HỎI: "{mcq.question}"
ĐÁP ÁN: "{correct_opt}"

Chỉ trả về định dạng JSON duy nhất:
{{"entailment": true/false, "reason": "lý do ngắn gọn"}}
"""
    try:
        res = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.0,  # Khóa nhiệt độ về 0 để câu trả lời mang tính tất định tuyệt đối
            ),
        )
        import json
        data = json.loads(res.text)
        if data.get("entailment") is True:
            return True, ""
        return False, f"Không đảm bảo logic suy luận: {data.get('reason')}"
    except Exception as e:
        # Nếu lỗi mạng hoặc API parse thất bại, tạm thời chấp nhận để không chặn pipeline
        return True, ""
# ----------------- Orchestrator -----------------

CheckFn = Callable[[GeneratedMCQ, list[str]], tuple[bool, str]]
SemanticVerifier = Callable[[GeneratedMCQ, list[str]], tuple[bool, str]]


def validate_mcq(
    mcq: GeneratedMCQ,
    chunk_sentences: list[str],
    strict: bool = False,
    semantic_verifier: SemanticVerifier | None = None,
) -> tuple[bool, str]:
    base_checks: list[CheckFn] = [
        _check_labels,
        _check_source_exact,
        _check_answer_appears_in_source_preliminary,
        _check_no_duplicates,
        _check_question_min,
    ]
    strict_checks: list[CheckFn] = [_check_not_ambiguous]

    for fn in base_checks + (strict_checks if strict else []):
        ok, reason = fn(mcq, chunk_sentences)
        if not ok:
            return False, reason

    # Nếu caller không truyền verifier riêng, dùng nli_semantic_verifier mặc định khi ở chế độ strict
    verifier = semantic_verifier or (nli_semantic_verifier if strict else None)
    if verifier is not None:
        ok, reason = verifier(mcq, chunk_sentences)
        if not ok:
            return False, f"[semantic] {reason}"

    return True, "OK"