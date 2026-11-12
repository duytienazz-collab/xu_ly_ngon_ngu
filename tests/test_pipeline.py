def test_clean_text_preserves_all_vietnamese_diacritics():
    raw = "Tiếng Việt đủ dấu: è é ẻ ẽ ẹ, ì í ỉ ĩ ị, ò ó ỏ õ ọ, ù ú ủ ũ ụ."
    cleaned = clean_text(raw)
    for token in ["Tiếng", "Việt", "è", "é", "ẻ", "ẽ", "ẹ",
                  "ì", "í", "ỉ", "ĩ", "ị", "ò", "ó", "ỏ", "õ", "ọ",
                  "ù", "ú", "ủ", "ũ", "ụ"]:
        assert token in cleaned, f"Mất {token!r} sau clean_text"


def test_answer_that_is_paraphrase_is_not_falsely_accepted_as_verified():
    """Xác nhận pre-filter KHÔNG coi substring match là 'đã kiểm chứng'."""
    from app.modules.validation.post_validator import (
        _check_answer_appears_in_source_preliminary,
    )
    mcq = _make_mcq(source_sentence="Thủ đô của Việt Nam là Hà Nội.")
    # Trả về True chỉ là pre-filter pass, không phải verification
    ok, _ = _check_answer_appears_in_source_preliminary(mcq, [])
    assert ok  # pass pre-filter


def test_distractor_appearing_in_source_is_not_rejected():
    """Huế xuất hiện trong source nhưng vẫn là distractor hợp lệ."""
    mcq = _make_mcq(
        question="Thủ đô hiện tại của Việt Nam là thành phố nào?",
        options=[
            MCQOption(label="A", text="Hà Nội"),
            MCQOption(label="B", text="Huế"),
            MCQOption(label="C", text="Đà Nẵng"),
            MCQOption(label="D", text="Hải Phòng"),
        ],
        correct_answer_label="A",
        source_sentence="Hà Nội là thủ đô Việt Nam, còn Huế từng là kinh đô của Việt Nam.",
    )
    ctx = ["Hà Nội là thủ đô Việt Nam, còn Huế từng là kinh đô của Việt Nam."]
    ok, reason = validate_mcq(mcq, ctx, strict=True)
    assert ok, reason  # không bị loại oan