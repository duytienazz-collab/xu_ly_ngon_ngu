import argparse
from datetime import datetime
from pathlib import Path

from app.services.pipeline_service import run_pipeline
from app.modules.export.exporter import export_json, export_csv, export_docx


def main():
    parser = argparse.ArgumentParser(description="Text-to-MCQ Generator (Gemini API)")
    parser.add_argument("--input", required=True, help="Đường dẫn file PDF/DOCX/TXT")
    parser.add_argument("--num", type=int, default=2, help="Số câu hỏi mỗi chunk")
    parser.add_argument("--max-chunks", type=int, default=None)
    parser.add_argument("--strict", action="store_true", help="Bật kiểm tra nghiêm ngặt")
    parser.add_argument("--out", default="data/output")
    args = parser.parse_args()

    result = run_pipeline(
        file_path=args.input,
        num_questions_per_chunk=args.num,
        max_chunks=args.max_chunks,
        strict_validation=args.strict,
    )

    if not result["questions"]:
        print("Không có câu hỏi nào được tạo.")
        return

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    metadata = {
        "source_file": Path(args.input).name,
        "generated_at": datetime.now().isoformat(),
        "stats": result["stats"],
    }

    export_json(result["questions"], out_dir / "mcq.json", metadata)
    export_csv(result["questions"], out_dir / "mcq.csv", metadata)
    export_docx(result["questions"], out_dir / "mcq.docx", metadata)

    print(f"\n📁 Đã xuất vào {out_dir.resolve()}")
    print(f"📊 Stats: {result['stats']}")


if __name__ == "__main__":
    main()