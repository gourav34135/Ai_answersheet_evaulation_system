import shutil
from pathlib import Path
from uuid import uuid4

from flask import Flask, jsonify, render_template, request, send_file
from werkzeug.utils import secure_filename

from config import ALLOWED_EXTENSIONS, APP_VERSION, DATA_DIR, DEFAULT_MAX_SCORE, MAX_CONTENT_LENGTH, UPLOAD_DIR
from database import clear_history, delete_evaluation, get_evaluation, init_db, list_evaluations, save_evaluation
from demo_data import as_dict as demo_rubric
from evaluator import evaluate_answer
from ocr import OCRDependencyError, correct_text_with_context, extract_text


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def startup() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    init_db()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/history", methods=["GET"])
def history():
    return jsonify({"items": list_evaluations()})


@app.route("/api/history", methods=["DELETE"])
def history_clear():
    clear_history()
    return jsonify({"ok": True})


@app.route("/api/demo-rubric", methods=["GET"])
def get_demo_rubric():
    return jsonify(demo_rubric())


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify(
        {
            "status": "ok",
            "version": APP_VERSION,
            "tesseract_available": shutil.which("tesseract") is not None,
            "scoring_mode": "OCR-tolerant concept and rubric evaluation",
        }
    )


@app.route("/api/history/<int:evaluation_id>", methods=["GET"])
def history_detail(evaluation_id: int):
    item = get_evaluation(evaluation_id)
    if item is None:
        return jsonify({"error": "Evaluation not found"}), 404
    return jsonify(item)


@app.route("/api/history/<int:evaluation_id>", methods=["DELETE"])
def history_delete(evaluation_id: int):
    deleted = delete_evaluation(evaluation_id)
    if not deleted:
        return jsonify({"error": "Evaluation not found"}), 404
    return jsonify({"ok": True})


@app.route("/api/evaluate", methods=["POST"])
def evaluate():
    upload = request.files.get("answer_sheet")
    if not upload or not upload.filename:
        return jsonify({"error": "Please upload a PDF or image answer sheet."}), 400
    if not allowed_file(upload.filename):
        return jsonify({"error": "Unsupported file type. Use PDF, JPG, PNG, WEBP, or TIFF."}), 400

    original_name = secure_filename(upload.filename)
    saved_name = f"{uuid4().hex}_{original_name}"
    saved_path = UPLOAD_DIR / saved_name
    upload.save(saved_path)

    try:
        extracted_text = extract_text(saved_path)
    except OCRDependencyError as exc:
        return jsonify({"error": str(exc), "setup_hint": "Install Tesseract and Python packages first."}), 500
    except Exception as exc:
        return jsonify({"error": f"OCR failed: {exc}"}), 500

    student_name = request.form.get("student_name", "Unknown Student").strip() or "Unknown Student"
    question = request.form.get("question", "").strip()
    reference_answer = request.form.get("reference_answer", "").strip()
    marking_points = request.form.get("marking_points", "").strip()
    correction_context = " ".join([question, reference_answer, marking_points])
    extracted_text = correct_text_with_context(extracted_text, correction_context)

    if len(extracted_text.strip()) < 5:
        return jsonify(
            {
                "error": "No readable text was detected. Try a clearer scan, higher resolution image, or typed PDF.",
                "extracted_text": extracted_text,
            }
        ), 422

    try:
        max_score = float(request.form.get("max_score", DEFAULT_MAX_SCORE))
    except ValueError:
        max_score = DEFAULT_MAX_SCORE
    max_score = min(max(max_score, 1.0), 100.0)

    result = evaluate_answer(
        student_answer=extracted_text,
        reference_answer=reference_answer,
        marking_points_text=marking_points,
        max_score=max_score,
    )

    payload = {
        "student_name": student_name,
        "question": question,
        "reference_answer": reference_answer,
        "marking_points": marking_points,
        "file_name": original_name,
        "extracted_text": extracted_text,
        "score": result.score,
        "max_score": result.max_score,
        "confidence": result.confidence,
        "result": result.as_dict(),
    }
    evaluation_id = save_evaluation(payload)

    return jsonify(
        {
            "id": evaluation_id,
            "student_name": student_name,
            "file_name": original_name,
            "extracted_text": extracted_text,
            "result": result.as_dict(),
        }
    )


@app.route("/api/rescore", methods=["POST"])
def rescore():
    data = request.get_json(silent=True) or {}
    extracted_text = str(data.get("extracted_text", "")).strip()
    if len(extracted_text) < 5:
        return jsonify({"error": "Please enter readable extracted text before re-scoring."}), 400

    student_name = str(data.get("student_name", "Edited OCR")).strip() or "Edited OCR"
    question = str(data.get("question", "")).strip()
    reference_answer = str(data.get("reference_answer", "")).strip()
    marking_points = str(data.get("marking_points", "")).strip()

    try:
        max_score = float(data.get("max_score", DEFAULT_MAX_SCORE))
    except (TypeError, ValueError):
        max_score = DEFAULT_MAX_SCORE
    max_score = min(max(max_score, 1.0), 100.0)

    result = evaluate_answer(
        student_answer=extracted_text,
        reference_answer=reference_answer,
        marking_points_text=marking_points,
        max_score=max_score,
    )
    payload = {
        "student_name": student_name,
        "question": question,
        "reference_answer": reference_answer,
        "marking_points": marking_points,
        "file_name": "edited_ocr_text",
        "extracted_text": extracted_text,
        "score": result.score,
        "max_score": result.max_score,
        "confidence": result.confidence,
        "result": result.as_dict(),
    }
    evaluation_id = save_evaluation(payload)
    return jsonify(
        {
            "id": evaluation_id,
            "student_name": student_name,
            "file_name": "edited_ocr_text",
            "extracted_text": extracted_text,
            "result": result.as_dict(),
        }
    )


@app.route("/api/report/<int:evaluation_id>", methods=["GET"])
def report(evaluation_id: int):
    item = get_evaluation(evaluation_id)
    if item is None:
        return jsonify({"error": "Evaluation not found"}), 404

    report_path = DATA_DIR / f"evaluation_report_{evaluation_id}.txt"
    lines = [
        "AI Answer Sheet Evaluation Report",
        "=" * 36,
        f"Student: {item['student_name']}",
        f"File: {item['file_name']}",
        f"Score: {item['score']} / {item['max_score']}",
        f"Confidence: {item['confidence']}",
        f"Date: {item['created_at']}",
        "",
        "Feedback:",
        *[f"- {point}" for point in item["result"]["feedback"]],
        "",
        "Extracted Answer:",
        item["extracted_text"],
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return send_file(report_path, as_attachment=True)


startup()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
