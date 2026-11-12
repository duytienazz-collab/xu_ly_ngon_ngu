from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List

LABELS = ["A", "B", "C", "D"]


class MCQOption(BaseModel):
    label: str = Field(description="Nhãn phương án: A, B, C hoặc D")
    text: str = Field(min_length=1, description="Nội dung của phương án")

    @field_validator("label")
    @classmethod
    def _label_must_be_abcd(cls, v: str) -> str:
        v = v.strip().upper()
        if v not in LABELS:
            raise ValueError(f"Nhãn phương án phải là A/B/C/D, nhận {v!r}")
        return v


class GeneratedMCQ(BaseModel):
    question: str = Field(min_length=10)
    options: List[MCQOption]
    correct_answer_label: str
    source_sentence: str = Field(min_length=1)
    explanation: str = ""

    @field_validator("correct_answer_label")
    @classmethod
    def _correct_label_valid(cls, v: str) -> str:
        v = v.strip().upper()
        if v not in LABELS:
            raise ValueError(f"correct_answer_label phải là A/B/C/D, nhận {v!r}")
        return v

    @model_validator(mode="after")
    def _check_structure(self):
        labels = sorted(o.label for o in self.options)
        if labels != LABELS:
            raise ValueError(
                f"Phải có đúng 4 phương án A, B, C, D; nhận {labels}"
            )
        texts = [o.text.strip().lower() for o in self.options]
        if len(set(texts)) < 4:
            raise ValueError("Có phương án trùng nội dung")
        return self


class MCQList(BaseModel):
    questions: List[GeneratedMCQ]