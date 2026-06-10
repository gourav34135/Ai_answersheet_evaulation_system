import math
import re
from collections import Counter
from dataclasses import dataclass
from difflib import SequenceMatcher

import numpy as np
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


TOKEN_PATTERN = re.compile(r"[a-zA-Z][a-zA-Z0-9']+")
DOMAIN_TERMS = {
    "algorithm",
    "algorithms",
    "artificial",
    "automatically",
    "branch",
    "collection",
    "computer",
    "computers",
    "cross",
    "data",
    "dataset",
    "datasets",
    "decisions",
    "detection",
    "examples",
    "features",
    "generalize",
    "human",
    "image",
    "intelligence",
    "labels",
    "labeled",
    "learning",
    "machine",
    "model",
    "models",
    "noise",
    "output",
    "overfitting",
    "patterns",
    "performance",
    "prediction",
    "predictions",
    "recognition",
    "recommendation",
    "regularization",
    "relationship",
    "speech",
    "spam",
    "subset",
    "supervised",
    "systems",
    "testing",
    "training",
    "validation",
}


@dataclass
class EvaluationResult:
    score: float
    max_score: float
    percentage: float
    confidence: str
    metrics: dict
    feedback: list[str]
    matched_points: list[str]
    missing_points: list[str]
    question_results: list[dict]

    def as_dict(self) -> dict:
        return {
            "score": self.score,
            "max_score": self.max_score,
            "percentage": self.percentage,
            "confidence": self.confidence,
            "metrics": self.metrics,
            "feedback": self.feedback,
            "matched_points": self.matched_points,
            "missing_points": self.missing_points,
            "question_results": self.question_results,
        }


def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s']", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def tokenize(text: str) -> list[str]:
    return [
        token.lower()
        for token in TOKEN_PATTERN.findall(text)
        if token.lower() not in ENGLISH_STOP_WORDS and len(token) > 2
    ]


def relaxed_tokens(text: str) -> list[str]:
    return [
        token.lower()
        for token in TOKEN_PATTERN.findall(text)
        if len(token) > 2 and token.lower() not in ENGLISH_STOP_WORDS
    ]


def split_marking_points(text: str) -> list[str]:
    if not text.strip():
        return []

    raw_points = re.split(r"\n|;|\|", text)
    points = []
    for point in raw_points:
        cleaned = re.sub(r"^\s*[-*\d.)]+\s*", "", point).strip()
        if cleaned:
            points.append(cleaned)
    return points


def extract_keywords(reference_answer: str, limit: int = 10) -> list[str]:
    tokens = tokenize(reference_answer)
    counts = Counter(tokens)
    return [token for token, _ in counts.most_common(limit)]


def text_similarity(student_answer: str, reference_answer: str) -> float:
    if not student_answer.strip() or not reference_answer.strip():
        return 0.0

    word_score = 0.0
    try:
        vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words="english",
            ngram_range=(1, 2),
            max_features=3000,
        )
        matrix = vectorizer.fit_transform([student_answer, reference_answer])
        word_score = float(cosine_similarity(matrix[0], matrix[1])[0][0])
    except ValueError:
        student_tokens = set(tokenize(student_answer))
        reference_tokens = set(tokenize(reference_answer))
        if not student_tokens or not reference_tokens:
            word_score = 0.0
        else:
            word_score = len(student_tokens & reference_tokens) / len(student_tokens | reference_tokens)

    char_score = character_similarity(student_answer, reference_answer)
    fuzzy_score = fuzzy_keyword_coverage(student_answer, reference_answer)
    ocr_tolerant_score = (0.55 * char_score) + (0.45 * fuzzy_score)
    return float(np.clip(max(word_score, ocr_tolerant_score), 0.0, 1.0))


def character_similarity(student_answer: str, reference_answer: str) -> float:
    try:
        vectorizer = TfidfVectorizer(
            analyzer="char_wb",
            lowercase=True,
            ngram_range=(3, 5),
            max_features=5000,
        )
        matrix = vectorizer.fit_transform([student_answer, reference_answer])
        return float(cosine_similarity(matrix[0], matrix[1])[0][0])
    except ValueError:
        return 0.0


def fuzzy_keyword_coverage(student_answer: str, reference_answer: str, limit: int = 80) -> float:
    student_tokens = relaxed_tokens(student_answer)
    key_terms = extract_key_terms(reference_answer, limit=limit)
    if not student_tokens or not key_terms:
        return 0.0

    matched = sum(1 for term in key_terms if best_token_match(term, student_tokens) >= token_threshold(term))
    return matched / len(key_terms)


def extract_key_terms(text: str, limit: int = 40) -> list[str]:
    tokens = relaxed_tokens(text)
    if not tokens:
        return []

    counts = Counter(tokens)
    scored_terms = []
    for term, count in counts.items():
        if len(term) < 4 and term not in {"ai"}:
            continue
        score = count
        if term in DOMAIN_TERMS:
            score += 3
        if len(term) >= 8:
            score += 0.5
        scored_terms.append((score, term))

    scored_terms.sort(key=lambda item: (-item[0], item[1]))
    return [term for _, term in scored_terms[:limit]]


def best_token_match(term: str, student_tokens: list[str] | set[str]) -> float:
    if not term:
        return 0.0
    if term in student_tokens:
        return 1.0

    best = 0.0
    for token in student_tokens:
        if abs(len(token) - len(term)) > max(4, len(term) // 2):
            continue
        score = SequenceMatcher(None, term, token).ratio()
        if token[:1] == term[:1]:
            score += 0.04
        if len(term) >= 6 and token[-3:] == term[-3:]:
            score += 0.07
        best = max(best, min(score, 1.0))
    return best


def token_threshold(term: str) -> float:
    if len(term) >= 10:
        return 0.62
    if len(term) >= 7:
        return 0.68
    if len(term) >= 5:
        return 0.74
    return 0.82


def reference_concept_coverage(student_answer: str, reference_answer: str) -> float:
    blocks = split_reference_blocks(reference_answer)
    if not blocks:
        return fuzzy_keyword_coverage(student_answer, reference_answer)

    scores = []
    for block in blocks:
        terms = extract_key_terms(block, limit=18)
        if not terms:
            continue
        student_tokens = relaxed_tokens(student_answer)
        matched = sum(1 for term in terms if best_token_match(term, student_tokens) >= token_threshold(term))
        scores.append(matched / len(terms))
    return float(np.mean(scores)) if scores else 0.0


def split_reference_blocks(reference_answer: str) -> list[str]:
    text = reference_answer.strip()
    if not text:
        return []

    matches = list(re.finditer(r"(?m)^\s*\d+\.\s+", text))
    if len(matches) < 2:
        return [text]

    blocks = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[start:end].strip()
        if block:
            blocks.append(block)
    return blocks


def question_title(block: str, index: int) -> str:
    first_line = next((line.strip() for line in block.splitlines() if line.strip()), "")
    cleaned = re.sub(r"^\s*\d+\.\s*", "", first_line).strip()
    if cleaned and len(cleaned) <= 180:
        return cleaned
    return f"Question {index}"


def question_reference_body(block: str) -> str:
    lines = [line.strip() for line in block.splitlines() if line.strip()]
    if len(lines) > 1 and re.match(r"^\s*\d+\.\s+", lines[0]):
        return "\n".join(lines[1:])
    return block


def evaluate_question_sections(
    student_answer: str,
    reference_answer: str,
    max_score: float,
) -> list[dict]:
    blocks = split_reference_blocks(reference_answer)
    if not blocks:
        return []

    section_max = max_score / len(blocks)
    results = []
    for index, block in enumerate(blocks, start=1):
        body = question_reference_body(block)
        similarity = text_similarity(student_answer, body)
        concepts = reference_concept_coverage(student_answer, body)
        keywords = fuzzy_keyword_coverage(student_answer, body, limit=24)
        raw = float(np.clip((0.35 * similarity) + (0.45 * concepts) + (0.2 * keywords), 0.0, 1.0))
        section_score = round(raw * section_max, 2)
        results.append(
            {
                "number": index,
                "title": question_title(block, index),
                "score": section_score,
                "max_score": round(section_max, 2),
                "percentage": round(raw * 100, 1),
                "semantic_similarity": round(similarity, 3),
                "concept_coverage": round(concepts, 3),
                "keyword_coverage": round(keywords, 3),
                "status": "Strong" if raw >= 0.72 else "Partial" if raw >= 0.42 else "Needs review",
            }
        )
    return results


def point_coverage(
    student_answer: str,
    points: list[str],
    reference_answer: str = "",
) -> tuple[float, list[str], list[str]]:
    if not points:
        return 0.0, [], []

    matched = []
    missing = []
    student_clean = normalize_text(student_answer)
    student_tokens = relaxed_tokens(student_answer)

    for point in points:
        point_clean = normalize_text(point)
        point_tokens = relaxed_tokens(point)
        token_overlap = 0.0
        if point_tokens:
            token_overlap = sum(
                1
                for token in point_tokens
                if best_token_match(token, student_tokens) >= token_threshold(token)
            ) / len(point_tokens)

        exactish_match = point_clean and point_clean in student_clean
        generic_match = generic_marking_point_match(point, student_answer, reference_answer)
        if exactish_match or token_overlap >= 0.45 or generic_match:
            matched.append(point)
        else:
            missing.append(point)

    return len(matched) / len(points), matched, missing


def generic_marking_point_match(point: str, student_answer: str, reference_answer: str) -> bool:
    point_clean = normalize_text(point)
    if not reference_answer.strip():
        return False

    concept_score = reference_concept_coverage(student_answer, reference_answer)
    term_count = count_domain_terms(student_answer, reference_answer)

    if "example" in point_clean or "relevant example" in point_clean:
        return has_relevant_example(student_answer, reference_answer)
    if "terminology" in point_clean or "correct term" in point_clean:
        return term_count >= 8 or concept_score >= 0.32
    if "feature" in point_clean or "important" in point_clean or "explains" in point_clean:
        return term_count >= 10 or concept_score >= 0.36
    if "define" in point_clean or "concept" in point_clean:
        return concept_score >= 0.24 or count_domain_terms(student_answer, reference_answer, limit=12) >= 5
    if "conclude" in point_clean or "result" in point_clean or "correct" in point_clean:
        return concept_score >= 0.30
    return False


def count_domain_terms(student_answer: str, reference_answer: str, limit: int = 40) -> int:
    student_tokens = relaxed_tokens(student_answer)
    key_terms = extract_key_terms(reference_answer, limit=limit)
    return sum(1 for term in key_terms if best_token_match(term, student_tokens) >= token_threshold(term))


def has_relevant_example(student_answer: str, reference_answer: str) -> bool:
    reference_terms = extract_key_terms(reference_answer, limit=80)
    example_terms = {
        "recommendation",
        "image",
        "recognition",
        "speech",
        "spam",
        "detection",
        "house",
        "price",
        "prediction",
        "validation",
        "testing",
        "cross",
        "regularization",
    }
    expected_examples = [term for term in reference_terms if term in example_terms]
    if not expected_examples:
        return False

    student_tokens = relaxed_tokens(student_answer)
    hits = sum(1 for term in expected_examples if best_token_match(term, student_tokens) >= token_threshold(term))
    return hits >= 2


def length_quality(student_answer: str, reference_answer: str) -> float:
    student_words = len(tokenize(student_answer))
    reference_words = len(tokenize(reference_answer))

    if student_words == 0:
        return 0.0
    if reference_words == 0:
        return min(1.0, student_words / 80)

    ratio = student_words / max(reference_words, 1)
    if 0.65 <= ratio <= 1.6:
        return 1.0
    if ratio < 0.65:
        return max(0.2, ratio / 0.65)
    return max(0.55, 1.0 - min(0.45, (ratio - 1.6) * 0.12))


def readability_quality(student_answer: str) -> float:
    words = tokenize(student_answer)
    if not words:
        return 0.0

    unique_ratio = len(set(words)) / len(words)
    sentence_count = max(1, len(re.findall(r"[.!?]", student_answer)))
    words_per_sentence = len(words) / sentence_count
    sentence_score = 1.0 - min(0.45, abs(words_per_sentence - 18) / 55)
    vocabulary_score = min(1.0, max(0.45, unique_ratio * 1.6))
    return float(np.clip((sentence_score + vocabulary_score) / 2, 0.0, 1.0))


def confidence_label(extracted_text: str, reference_answer: str, marking_points: list[str]) -> str:
    word_count = len(tokenize(extracted_text))
    if word_count < 20:
        return "Low"
    if reference_answer.strip() and (marking_points or word_count >= 50):
        return "High"
    return "Medium"


def evaluate_answer(
    student_answer: str,
    reference_answer: str = "",
    marking_points_text: str = "",
    max_score: float = 10.0,
) -> EvaluationResult:
    student_answer = student_answer.strip()
    reference_answer = reference_answer.strip()
    marking_points = split_marking_points(marking_points_text)

    if not marking_points and reference_answer:
        marking_points = extract_keywords(reference_answer, limit=10)

    similarity = text_similarity(student_answer, reference_answer)
    coverage, matched, missing = point_coverage(student_answer, marking_points, reference_answer)
    concept_coverage = reference_concept_coverage(student_answer, reference_answer)
    question_results = evaluate_question_sections(student_answer, reference_answer, max_score)
    completeness = length_quality(student_answer, reference_answer)
    readability = readability_quality(student_answer)

    if reference_answer and marking_points:
        raw = (
            (0.35 * similarity)
            + (0.25 * concept_coverage)
            + (0.25 * coverage)
            + (0.1 * completeness)
            + (0.05 * readability)
        )
    elif reference_answer:
        raw = (0.5 * similarity) + (0.3 * concept_coverage) + (0.12 * completeness) + (0.08 * readability)
    elif marking_points:
        raw = (0.75 * coverage) + (0.15 * completeness) + (0.1 * readability)
    else:
        raw = (0.55 * readability) + (0.45 * min(1.0, len(tokenize(student_answer)) / 120))

    if len(question_results) > 1:
        question_raw = sum(item["score"] for item in question_results) / max_score
        raw = (0.7 * raw) + (0.3 * question_raw)

    score = round(float(np.clip(raw, 0.0, 1.0)) * max_score, 2)
    percentage = round((score / max_score) * 100, 1) if max_score else 0.0
    confidence = confidence_label(student_answer, reference_answer, marking_points)
    feedback = build_feedback(
        score=score,
        max_score=max_score,
        similarity=similarity,
        coverage=coverage,
        completeness=completeness,
        readability=readability,
        matched=matched,
        missing=missing,
        has_reference=bool(reference_answer),
        has_points=bool(marking_points),
    )

    return EvaluationResult(
        score=score,
        max_score=max_score,
        percentage=percentage,
        confidence=confidence,
        metrics={
            "semantic_similarity": round(similarity, 3),
            "concept_coverage": round(concept_coverage, 3),
            "key_point_coverage": round(coverage, 3),
            "answer_completeness": round(completeness, 3),
            "readability": round(readability, 3),
            "word_count": len(tokenize(student_answer)),
            "raw_score": round(raw, 3),
        },
        feedback=feedback,
        matched_points=matched,
        missing_points=missing,
        question_results=question_results,
    )


def build_feedback(
    score: float,
    max_score: float,
    similarity: float,
    coverage: float,
    completeness: float,
    readability: float,
    matched: list[str],
    missing: list[str],
    has_reference: bool,
    has_points: bool,
) -> list[str]:
    feedback = []
    ratio = score / max_score if max_score else 0.0

    if ratio >= 0.8:
        feedback.append("Strong answer. It covers most expected ideas and is close to the reference.")
    elif ratio >= 0.55:
        feedback.append("Average answer. It includes some correct content but misses important details.")
    else:
        feedback.append("Weak answer. It needs more relevant points and clearer explanation.")

    if has_reference and similarity < 0.35:
        feedback.append("The answer has low semantic similarity with the reference answer.")
    if has_points and coverage < 0.5:
        feedback.append("Several expected marking points were not detected.")
    if completeness < 0.55:
        feedback.append("The answer appears too short compared with the expected answer.")
    if readability < 0.55:
        feedback.append("The extracted text is difficult to read or poorly structured.")
    if matched:
        feedback.append(f"Detected {len(matched)} expected point(s).")
    if missing:
        feedback.append(f"Missing {len(missing)} expected point(s).")

    if not has_reference and not has_points:
        feedback.append("Add a reference answer or marking points for a more reliable score.")

    return feedback
