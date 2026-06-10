# AI Answer Sheet Evaluator Version 2.0

A local web project for evaluating handwritten or scanned answer sheets. The user uploads a PDF or image file, the app extracts text using OCR, compares it with a reference answer and marking points, gives a score out of 10 by default, and stores each result in local history.

## Main Features

- Upload answer sheets as PDF, JPG, JPEG, PNG, WEBP, TIFF.
- OCR extraction using Tesseract through `pytesseract`.
- Handwriting-focused preprocessing with OpenCV: upscaling, blue-ink isolation, denoising, thresholding, and ruled-line cleanup.
- Reference-assisted OCR cleanup that uses the question, reference answer, and marking points to fix likely OCR mistakes.
- PDF support using PyMuPDF.
- NLP scoring with TF-IDF semantic similarity, key point coverage, completeness, and readability.
- OCR-tolerant character similarity, fuzzy keyword matching, and reference concept coverage.
- Score can be out of 10 or any custom maximum score.
- Local SQLite history with view, delete, and text report download.
- Interactive first page with drag and drop upload, metrics, feedback, matched points, missing points, and extracted text preview.
- One-click demo rubric containing the five Machine Learning questions and reference answers.
- Fast scanned-PDF mode designed for classroom demonstrations.

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

You can also double-click `run_mac.command` after the first setup.

## Run in PyCharm

1. Open this folder in PyCharm.
2. Go to `Settings` or `Preferences` > `Project` > `Python Interpreter`.
3. Select the `.venv` interpreter from this project.
4. Open `app.py`.
5. Click Run.
6. Open `http://127.0.0.1:5000` in your browser.

## Teacher Demo Steps

1. Start the app with `python app.py`.
2. Open `http://127.0.0.1:5000`.
3. Click `Load Demo Rubric`.
4. Enter the student name.
5. Upload `IMG_20260610_144714.pdf`.
6. Click `Evaluate Answer`.
7. Review the score, concept coverage, rubric coverage, feedback, extracted text, and saved history.

The included sample PDF was verified locally with the Version 2.0 evaluator. It completed in approximately 13 seconds and scored approximately `8.18 / 10`. The exact result may vary slightly by Tesseract and system version.

## Verification

Check that the server and Tesseract are ready:

```text
http://127.0.0.1:5000/api/health
```

Run the evaluator regression tests:

```bash
source .venv/bin/activate
python -m unittest discover -v
```

## Important Notes

- Handwritten OCR quality depends heavily on handwriting clarity, scan brightness, resolution, and page angle.
- For best scoring accuracy, always provide a reference answer or marking points.
- Version 2.0 uses fuzzy concept matching so correct handwritten content is not treated as wrong only because OCR misspelled words.
- For best OCR accuracy, upload a straight, bright photo cropped close to the answer area.
- Blue or black ink on plain paper works best. Ruled paper is supported, but heavy shadows reduce accuracy.
- If no reference answer or marking points are provided, the app can only produce a rough quality-based score.
- This project runs locally. Uploaded answer sheets and history stay on your computer.

## OCR Design Basis

Version 2.0 follows the official Tesseract recommendations for improving OCR output: rescaling, binarization, noise removal, dilation, deskewing, border handling, and testing suitable page segmentation modes.

- Tesseract quality guide: https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html
- Tesseract page segmentation modes: https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html
- OpenCV thresholding guide: https://docs.opencv.org/4.x/d7/d4d/tutorial_py_thresholding.html
- TrOCR handwriting-recognition research: https://arxiv.org/abs/2109.10282

Transformer handwriting OCR such as TrOCR can be added later, but it requires large model downloads and additional runtime dependencies. Version 2.0 keeps the main teacher demonstration fully local and reliable by combining fast Tesseract OCR with OCR-tolerant reference and concept scoring.

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
