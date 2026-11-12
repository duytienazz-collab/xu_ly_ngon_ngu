SYSTEM_PROMPT = (
    "Bạn là một chuyên gia soạn đề trắc nghiệm tiếng Việt. "
    "Bạn CHỈ được phép dùng thông tin trong NGỮ CẢNH được cung cấp. "
    "Không dùng kiến thức bên ngoài. Mọi câu hỏi và phương án phải bằng tiếng Việt."
)

USER_PROMPT_TEMPLATE = """NGỮ CẢNH:
\"\"\"
{context}
\"\"\"

YÊU CẦU:
Tạo đúng {num_questions} câu hỏi trắc nghiệm 4 lựa chọn (A, B, C, D) từ ngữ cảnh trên.

RÀNG BUỘC:
1. Mỗi câu có CHÍNH XÁC MỘT đáp án đúng, được xác nhận trực tiếp bởi một câu trong ngữ cảnh.
2. Trường source_sentence phải là câu NGUYÊN VĂN, sao chép chính xác từng ký tự từ ngữ cảnh.
3. Ba phương án nhiễu phải:
   - Cùng loại thông tin với đáp án đúng (địa danh ↔ địa danh, số liệu ↔ số liệu, ...).
   - Hợp lý nhưng SAI theo ngữ cảnh.
   - Không trùng đáp án đúng và không trùng lẫn nhau.
4. Câu hỏi không được chứa đáp án trực tiếp bên trong.
5. Nếu ngữ cảnh không đủ, hãy tạo ít hơn thay vì bịa đặt."""


def build_prompt(context: str, num_questions: int = 2) -> str:
    return USER_PROMPT_TEMPLATE.format(context=context, num_questions=num_questions)