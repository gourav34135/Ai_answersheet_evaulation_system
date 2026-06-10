import unittest

from demo_data import DEMO_MARKING_POINTS, DEMO_REFERENCE_ANSWERS
from evaluator import evaluate_answer


NOISY_SAMPLE_OCR = """What is Machine learning
Machine training is a branch artificial intelligence that enables computers learn data improve
performance without explicitly programmed. Uses algorithms identify patterns make predictions
and decisions. Used in recommendation, image recognition and speech.

Artificial intelligence broad field human intelligence. Machine learning subset AI allows systems
learn from data improve automatically. AI includes reasoning and rule based systems.

A dataset is a collection of data used training testing models. Contains examples, features and
labels. Quality quantity affect performance. Training validation testing sets.

Supervised learning type machine learning using labeled data. Input and correct output. Model
learns relationship and predicts unseen data. Examples spam detection and house price prediction.

Overfitting model learns training data too well including noise. Accurate training but poor unseen
data. Reduces generalize. Cross validation regularization and more training data reduce overfitting."""


class EvaluatorRegressionTests(unittest.TestCase):
    def test_noisy_handwriting_ocr_still_scores_correct_concepts(self):
        result = evaluate_answer(
            student_answer=NOISY_SAMPLE_OCR,
            reference_answer=DEMO_REFERENCE_ANSWERS,
            marking_points_text=DEMO_MARKING_POINTS,
            max_score=10,
        )

        self.assertGreaterEqual(result.score, 7.5)
        self.assertGreaterEqual(result.metrics["concept_coverage"], 0.65)
        self.assertEqual(len(result.missing_points), 0)


if __name__ == "__main__":
    unittest.main()
