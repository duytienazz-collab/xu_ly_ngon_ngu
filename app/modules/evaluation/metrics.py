"""
Module đánh giá chất lượng bộ câu hỏi sinh ra theo chuẩn học thuật NLP:
1. Lexical Diversity (Distinct-1, Distinct-2)
2. Distractor Quality (Độ tách biệt của phương án nhiễu)
"""
from collections import Counter
from underthesea import word_tokenize
from difflib import SequenceMatcher


def calculate_distinct_n(questions: list[str], n: int = 1) -> float:
    """
    Đo lường độ phong phú từ vựng (Distinct-N metric trong NLP):
    Tỷ lệ số n-gram độc nhất trên tổng số n-gram xuất hiện.
    Giá trị càng gần 1.0 -> câu hỏi càng đa dạng, không bị sinh lặp mẫu câu.
    """
    total_ngrams = 0
    unique_ngrams = set()

    for q in questions:
        words = word_tokenize(q, format="text").split()
        if len(words) < n:
            continue
        ngrams = [tuple(words[i : i + n]) for i in range(len(words) - n + 1)]
        total_ngrams += len(ngrams)
        unique_ngrams.update(ngrams)

    if total_ngrams == 0:
        return 0.0
    return round(len(unique_ngrams) / total_ngrams, 4)


def evaluate_distractor_quality(options: dict, correct_label: str) -> dict:
    """
    Đo độ chất lượng của phương án nhiễu:
    - Distractors không được quá giống đáp án đúng (gây tranh cãi).
    - Distractors không được quá giống nhau.
    """
    correct_text = options.get(correct_label, "")
    distractors = [text for label, text in options.items() if label != correct_label]

    # Tính độ tương đồng trung bình giữa distractor và correct answer
    sim_to_correct = [
        SequenceMatcher(None, correct_text.lower(), d.lower()).ratio()
        for d in distractors
    ]
    avg_sim_to_correct = sum(sim_to_correct) / len(sim_to_correct) if sim_to_correct else 0.0

    return {
        "avg_distractor_correct_overlap": round(avg_sim_to_correct, 3),
        "distractor_quality_score": round(1.0 - avg_sim_to_correct, 3),
    }


def evaluate_dataset(questions: list[dict]) -> dict:
    """
    Tổng hợp báo cáo chất lượng NLP cho toàn bộ bộ câu hỏi đã tạo.
    """
    if not questions:
        return {}

    q_texts = [q["question"] for q in questions]
    d1 = calculate_distinct_n(q_texts, n=1)
    d2 = calculate_distinct_n(q_texts, n=2)

    distractor_scores = [
        evaluate_distractor_quality(q["options"], q["correct_answer_label"])["distractor_quality_score"]
        for q in questions
    ]
    avg_distractor_quality = sum(distractor_scores) / len(distractor_scores) if distractor_scores else 0.0

    return {
        "total_evaluated": len(questions),
        "lexical_diversity_distinct_1": d1,
        "lexical_diversity_distinct_2": d2,
        "avg_distractor_quality": round(avg_distractor_quality, 3),
    }


if __name__ == "__main__":
    import json
    from pathlib import Path

    print("==========================================================")
    print("   BÁO CÁO ĐÁNH GIÁ CHẤT LƯỢNG BỘ CÂU HỎI TRẮC NGHIỆM")
    print("          (NLP EVALUATION METRICS BENCHMARK)             ")
    print("==========================================================")

    # Thử đọc từ data/output/mcq.json nếu có
    mcq_file = Path("data/output/mcq.json")
    if mcq_file.exists():
        data = json.loads(mcq_file.read_text(encoding="utf-8"))
        questions = data.get("questions", [])
        print(f"[*] Đọc dữ liệu từ file thực tế: {mcq_file} ({len(questions)} câu)")
    else:
        # Dữ liệu mẫu minh họa thực nghiệm
        print("[*] Chưa có data/output/mcq.json. Đang chạy trên tập dữ liệu mẫu:")
        questions = [
            {
                "question": "Thủ đô của nước Cộng hòa Xã hội Chủ nghĩa Việt Nam là thành phố nào?",
                "options": {"A": "Hà Nội", "B": "TP. Hồ Chí Minh", "C": "Đà Nẵng", "D": "Hải Phòng"},
                "correct_answer_label": "A"
            },
            {
                "question": "Ai là vị vua đầu tiên sáng lập nên triều đại nhà Lý vào năm 1009?",
                "options": {"A": "Lý Thái Tổ", "B": "Lý Thái Tông", "C": "Lê Hoàn", "D": "Đinh Tiên Hoàng"},
                "correct_answer_label": "A"
            },
            {
                "question": "Chiến thắng Bạch Đằng lịch sử chống quân Nguyên Mông diễn ra vào năm nào?",
                "options": {"A": "1288", "B": "1285", "C": "1279", "D": "1290"},
                "correct_answer_label": "A"
            }
        ]

    results = evaluate_dataset(questions)

    print("\n------------------- KẾT QUẢ ĐO LƯỜNG -------------------")
    print(f"1. Tổng số câu hỏi được đánh giá (Total Questions): {results.get('total_evaluated', 0)}")
    print(f"2. Độ phong phú từ vựng đơn (Distinct-1):           {results.get('lexical_diversity_distinct_1', 0.0)}")
    print(f"3. Độ phong phú từ vựng ghép (Distinct-2):          {results.get('lexical_diversity_distinct_2', 0.0)}")
    print(f"4. Chỉ số chất lượng phương án nhiễu (Distractor): {results.get('avg_distractor_quality', 0.0)}")
    print("----------------------------------------------------------")
    print("Ý NGHĨA KHOA HỌC:")
    print(" - Distinct-1/2 > 0.70: Câu hỏi có vốn từ vựng rất đa dạng, không bị lặp khuôn mẫu.")
    print(" - Distractor Quality > 0.60: Phương án sai có độ phân tách tốt, không gây tranh cãi.")
    print("==========================================================\n")
