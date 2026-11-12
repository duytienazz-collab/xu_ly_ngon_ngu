import re
import unicodedata
from underthesea import sent_tokenize


_ALLOWED_PUNCT = r".;:!?,\-–—/\\()\[\]{}\"'“”‘’…"
_ALLOWED_SYMBOLS = r"%‰°±×÷=+*<>≤≥≠→←↔§¶©®™"


def clean_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text)

    # \w của Python là Unicode-aware: khớp mọi chữ cái (kể cả tiếng Việt) và chữ số.
    # Lưu ý: \w có bao gồm dấu gạch dưới _. Nếu không muốn giữ _, đổi \w thành [^\W_].
    keep_chars = r"\w\s" + _ALLOWED_PUNCT + _ALLOWED_SYMBOLS

    text = re.sub(f"[^{keep_chars}]", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


def preprocess(text: str) -> list[str]:
    cleaned = clean_text(text)
    sentences = sent_tokenize(cleaned)
    return [
        s.strip()
        for s in sentences
        if s.strip() and re.search(r"[\w]", s)
    ]