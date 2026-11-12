import os
from pathlib import Path
from dotenv import load_dotenv
from google import genai

# Load .env ở thư mục gốc project
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(ROOT_DIR / ".env")

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

if not API_KEY:
    raise RuntimeError("Thiếu GEMINI_API_KEY trong file .env")

client = genai.Client(api_key=API_KEY)

DATA_INPUT_DIR = ROOT_DIR / "data" / "input"
DATA_OUTPUT_DIR = ROOT_DIR / "data" / "output"
DATA_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)