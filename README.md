<!-- # 📝 Text-to-MCQ Generator (Gemini API)

Hệ thống tự động chuyển đổi tài liệu tiếng Việt (PDF, DOCX, TXT) thành bộ câu hỏi trắc nghiệm 4 lựa chọn (A, B, C, D) sử dụng Google Gemini API.

## 🛠 1. Yêu cầu hệ thống
- **Python:** 3.10 trở lên.
- **API Key:** Lấy miễn phí tại [Google AI Studio](https://aistudio.google.com/apikey).

## 🚀 2. Hướng dẫn cài đặt

**Bước 1: Tạo và kích hoạt môi trường ảo**
```bash
cd .\text-to-mcq\
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

cài đặt thư viện pip install -r requirements.txt
Tạo file .env ở thư mục gốc (copy từ .env.example) và điền key của bạn:
GEMINI_API_KEY=điền_api_key_của_bạn_vào_đây
GEMINI_MODEL=gemini-2.5-flash

Dùng giao diện Web (Khuyên dùng)   streamlit run streamlit_app.py -->
