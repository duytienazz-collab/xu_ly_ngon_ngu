import re

from underthesea import word_tokenize


def est_tokens(text: str) -> int:
    """
    #11: ước lượng token chính xác hơn len(text)//4.
    Tách từ tiếng Việt (underthesea) → đếm "word" → nhân hệ số subword ~1.2.
    Chậm hơn nhưng đáng tin cậy hơn cho tiếng Việt.
    """
    if not text:
        return 0
    try:
        words = word_tokenize(text, format="text").split()
    except Exception:
        words = text.split()
    return max(1, int(len(words) * 1.2))


def _split_long_sentence(sentence: str, max_tokens: int) -> list[str]:
    """#12: tách câu quá dài theo dấu phẩy/chấm phẩy, fallback hard-split."""
    # Ưu tiên dấu câu
    parts = re.split(r"(?<=[,;:])\s+", sentence)
    if len(parts) == 1:
        # Hard-split theo số ký tự ước lượng
        max_chars = int(max_tokens * 3.5)
        return [sentence[i:i + max_chars] for i in range(0, len(sentence), max_chars)]

    # Gom phần cho đến khi vừa max_tokens
    out: list[str] = []
    buf = ""
    for p in parts:
        if not buf:
            buf = p
        elif est_tokens(buf + " " + p) <= max_tokens:
            buf += " " + p
        else:
            out.append(buf)
            buf = p
    if buf:
        out.append(buf)

    # Đệ quy cho phần vẫn quá dài
    final: list[str] = []
    for s in out:
        if est_tokens(s) <= max_tokens:
            final.append(s)
        else:
            final.extend(_split_long_sentence(s, max_tokens))
    return final


def _make_chunk(items: list[tuple[str, int]]) -> dict:
    # #13: lưu vị trí câu gốc
    return {
        "text": " ".join(t for t, _ in items),
        "sentences": [t for t, _ in items],
        "start_sentence": items[0][1],
        "end_sentence": items[-1][1],
    }


def chunk_sentences(
    sentences: list[str],
    max_tokens: int = 200,
    overlap: int = 1,
) -> list[dict]:
    """
    Chia câu thành chunk, lưu start_sentence / end_sentence.
    """
    if not sentences:
        return []

    # Bước 1: tách câu quá dài (#12), giữ index gốc
    expanded: list[tuple[str, int]] = []
    for idx, sent in enumerate(sentences):
        if est_tokens(sent) <= max_tokens:
            expanded.append((sent, idx))
        else:
            for piece in _split_long_sentence(sent, max_tokens):
                expanded.append((piece, idx))

    # Bước 2: gom chunk
    chunks: list[dict] = []
    current: list[tuple[str, int]] = []
    current_len = 0

    for sent, orig_idx in expanded:
        sent_len = est_tokens(sent)
        if current and current_len + sent_len > max_tokens:
            chunks.append(_make_chunk(current))
            current = current[-overlap:] if overlap > 0 else []
            current_len = sum(est_tokens(s) for s, _ in current)

        current.append((sent, orig_idx))
        current_len += sent_len

    if current:
        chunks.append(_make_chunk(current))

    return chunks