import math
import re
from collections import Counter
from dataclasses import dataclass

import numpy as np
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


TOKEN_PATTERN = re.compile(r"[a-zA-Z][a-zA-Z0-9']+")


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

    try:
        vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words="english",
            ngram_range=(1, 2),
            max_features=3000,
        )
        matrix = vectorizer.fit_transform([student_answer, reference_answer])
        return float(cosine_similarity(matrix[0], matrix[1])[0][0])
    except ValueError:
        student_tokens = set(tokenize(student_answer))
        reference_tokens = set(tokenize(reference_answer))
        if not student_tokens or not reference_tokens:
            return 0.0
        return len(student_tokens & reference_tokens) / len(student_tokens | reference_tokens)


def point_coverage(student_answer: str, points: list[str]) -> tuple[float, list[str], list[str]]:
    if not points:
        return 0.0, [], []

    matched = []
    missing = []
    student_clean = normalize_text(student_answer)
    student_tokens = set(tokenize(student_answer))

    for point in points:
        point_clean = normalize_text(point)
        point_tokens = set(tokenize(point))
        token_overlap = 0.0
        if point_tokens:
            token_overlap = len(student_tokens & point_tokens) / len(point_tokens)

        exactish_match = point_clean and point_clean in student_clean
        if exactish_match or token_overlap >= 0.45:
            matched.append(point)
        else:
            missing.append(point)

    return len(matched) / len(points), matched, missing


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
    coverage, matched, missing = point_coverage(student_answer, marking_points)
    completeness = length_quality(student_answer, reference_answer)
    readability = readability_quality(student_answer)

    if reference_answer and marking_points:
        raw = (0.5 * similarity) + (0.35 * coverage) + (0.1 * completeness) + (0.05 * readability)
    elif reference_answer:
        raw = (0.75 * similarity) + (0.15 * completeness) + (0.1 * readability)
    elif marking_points:
        raw = (0.75 * coverage) + (0.15 * completeness) + (0.1 * readability)
    else:
        raw = (0.55 * readability) + (0.45 * min(1.0, len(tokenize(student_answer)) / 120))

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
            "key_point_coverage": round(coverage, 3),
            "answer_completeness": round(completeness, 3),
            "readability": round(readability, 3),
            "word_count": len(tokenize(student_answer)),
            "raw_score": round(raw, 3),
        },
        feedback=feedback,
        matched_points=matched,
        missing_points=missing,
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
