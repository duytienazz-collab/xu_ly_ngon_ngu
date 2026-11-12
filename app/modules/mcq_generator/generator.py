import time
from dataclasses import dataclass

from google.genai import types

from app.core.config import client, MODEL_NAME
from app.schemas.mcq import MCQList
from app.modules.mcq_generator.prompt_builder import SYSTEM_PROMPT, build_prompt


@dataclass
class GenerationResult:
    parsed: MCQList | None
    tokens_in: int = 0
    tokens_out: int = 0
    error_type: str | None = None  # "rate_limit" | "timeout" | "config" | "schema" | "other"
    attempts: int = 0


def _classify_error(exc: Exception) -> str:
    msg = str(exc).lower()
    if "429" in msg or "rate limit" in msg or "resource_exhausted" in msg:
        return "rate_limit"
    if "timeout" in msg or "deadline" in msg:
        return "timeout"
    if "401" in msg or "403" in msg or "api key" in msg or "permission" in msg:
        return "config"
    if "validation" in msg or "schema" in msg or "parse" in msg:
        return "schema"
    return "other"


def _backoff_seconds(error_type: str, attempt: int) -> float:
    if error_type == "rate_limit":
        return min(60, 5 * (2 ** (attempt - 1)))
    if error_type == "timeout":
        return 3 * attempt
    if error_type == "config":
        return 0  # không retry — key sai thì retry cũng vô ích
    return 2 * attempt


def generate_mcqs(
    context: str,
    num_questions: int = 2,
    max_retries: int = 3,
) -> GenerationResult:
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        response_mime_type="application/json",
        response_schema=MCQList,
        temperature=0.7,
    )

    total_in = total_out = 0
    last_error: str | None = None

    for attempt in range(1, max_retries + 1):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=build_prompt(context, num_questions),
                config=config,
            )

            # Lấy token usage
            usage = getattr(response, "usage_metadata", None)
            if usage:
                total_in += getattr(usage, "prompt_token_count", 0) or 0
                total_out += getattr(usage, "candidates_token_count", 0) or 0

            parsed = response.parsed
            if parsed is None:
                raise RuntimeError("response.parsed = None (schema mismatch?)")

            # Kiểm tra số câu thực tế
            n = len(parsed.questions)
            if n == 0:
                raise RuntimeError("Gemini trả về 0 câu hỏi")
            if n < num_questions:
                print(f"[WARN] Yêu cầu {num_questions} câu, chỉ nhận {n}")
            if n > num_questions:
                parsed.questions = parsed.questions[:num_questions]

            return GenerationResult(
                parsed=parsed,
                tokens_in=total_in,
                tokens_out=total_out,
                attempts=attempt,
            )

        except Exception as e:
            err_type = _classify_error(e)
            last_error = err_type
            print(f"[ERROR attempt {attempt}] {err_type}: {e}")

            if err_type == "config":
                break
            if attempt < max_retries:
                wait = _backoff_seconds(err_type, attempt)
                if wait > 0:
                    time.sleep(wait)

    return GenerationResult(
        parsed=None,
        tokens_in=total_in,
        tokens_out=total_out,
        error_type=last_error,
        attempts=max_retries,
    )