DEMO_QUESTIONS = """1. What is Machine Learning?
2. What is the difference between Artificial Intelligence and Machine Learning?
3. What is a dataset in Machine Learning?
4. What is supervised learning?
5. What is overfitting in Machine Learning?"""


DEMO_REFERENCE_ANSWERS = """1. What is Machine Learning?

Machine Learning is a branch of Artificial Intelligence (AI) that enables computers to learn from data and improve their performance without being explicitly programmed. Instead of following fixed instructions, machine learning algorithms identify patterns in data and use them to make predictions or decisions. It is widely used in applications such as recommendation systems, image recognition, and speech processing.

2. What is the difference between Artificial Intelligence and Machine Learning?

Artificial Intelligence is a broad field that focuses on creating systems capable of performing tasks that normally require human intelligence. Machine Learning is a subset of AI that allows systems to learn from data and improve automatically over time. While AI includes rule-based systems and reasoning methods, machine learning specifically relies on data-driven learning techniques.

3. What is a dataset in Machine Learning?

A dataset is a collection of data used for training and testing machine learning models. It consists of multiple records or examples, each containing features and sometimes labels. The quality and quantity of a dataset directly affect the performance of a machine learning model. Datasets are usually divided into training, validation, and testing sets.

4. What is supervised learning?

Supervised learning is a type of machine learning where the model is trained using labeled data. Each training example contains both input data and the correct output. The goal of the model is to learn the relationship between inputs and outputs so that it can predict outcomes for new, unseen data. Examples include email spam detection and house price prediction.

5. What is overfitting in Machine Learning?

Overfitting occurs when a machine learning model learns the training data too well, including noise and unnecessary details. As a result, the model performs very accurately on training data but poorly on new or unseen data. Overfitting reduces the model's ability to generalize and can be minimized using techniques such as cross-validation, regularization, and collecting more training data."""


DEMO_MARKING_POINTS = """Defines the main concept clearly
Explains at least two important features
Gives a relevant example
Uses correct terminology
Concludes with the correct result"""


def as_dict() -> dict[str, str]:
    return {
        "questions": DEMO_QUESTIONS,
        "reference_answers": DEMO_REFERENCE_ANSWERS,
        "marking_points": DEMO_MARKING_POINTS,
        "max_score": "10",
    }
