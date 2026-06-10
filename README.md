# AI Answer Sheet Evaluator

A local web project for evaluating handwritten or scanned answer sheets. The user uploads a PDF or image file, the app extracts text using OCR, compares it with a reference answer and marking points, gives a score out of 10 by default, and stores each result in local history.

## Main Features

- Upload answer sheets as PDF, JPG, JPEG, PNG, WEBP, TIFF.
- OCR extraction using Tesseract through `pytesseract`.
- PDF support using PyMuPDF.
- NLP scoring with TF-IDF semantic similarity, key point coverage, completeness, and readability.
- Score can be out of 10 or any custom maximum score.
- Local SQLite history with view, delete, and text report download.
- Interactive first page with drag and drop upload, metrics, feedback, matched points, missing points, and extracted text preview.

## Project Structure

```text
.
├── app.py
├── config.py
├── database.py
├── evaluator.py
├── ocr.py
├── requirements.txt
├── README.md
├── templates/
│   └── index.html
├── static/
│   ├── css/
│   │   └── styles.css
│   └── js/
│       └── app.js
├── uploads/
│   └── .gitkeep
└── data/
    └── .gitkeep
```

## How It Works

1. The uploaded answer sheet is saved in `uploads/`.
2. PDF pages or image files are preprocessed for better OCR.
3. Tesseract OCR extracts answer text.
4. The NLP evaluator compares the extracted text with:
   - the reference answer
   - marking points entered by the teacher
   - answer length and readability
5. The final score, feedback, matched points, missing points, and OCR text are saved in SQLite.

## MacBook Setup

Open Terminal in this project folder and run:

```bash
brew install tesseract
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
```

Then open:

```text
http://127.0.0.1:5000
```

## Run in PyCharm

1. Open this folder in PyCharm.
2. Go to `Settings` or `Preferences` > `Project` > `Python Interpreter`.
3. Select the `.venv` interpreter from this project.
4. Open `app.py`.
5. Click Run.
6. Open `http://127.0.0.1:5000` in your browser.

## Important Notes

- Handwritten OCR quality depends heavily on handwriting clarity, scan brightness, resolution, and page angle.
- For best scoring accuracy, always provide a reference answer or marking points.
- If no reference answer or marking points are provided, the app can only produce a rough quality-based score.
- This project runs locally. Uploaded answer sheets and history stay on your computer.

## Suggested Input

Use this format in the marking points box:

```text
Defines the main concept clearly
Explains at least two important features
Gives a relevant example
Uses correct terminology
Concludes with the correct result
```

## Project Description

This project is an AI-based answer sheet evaluation system for local use. It accepts handwritten or scanned answer sheets as images or PDFs, extracts the written content with OCR, evaluates the extracted answer using natural language processing, and produces a score with feedback. It is designed for teachers, students, and exam practice workflows where quick answer checking and result history are useful.
