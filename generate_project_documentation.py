from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Flowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


OUTPUT_PATH = Path("docs") / "AI_Answer_Sheet_Evaluator_Technical_Documentation.pdf"
INK = colors.HexColor("#173237")
ACCENT = colors.HexColor("#087F72")
ACCENT_SOFT = colors.HexColor("#DDF3EE")
WARM = colors.HexColor("#C17A24")
LINE = colors.HexColor("#D6E0DE")
MUTED = colors.HexColor("#66767A")


class WorkflowDiagram(Flowable):
    def __init__(self):
        super().__init__()
        self.width = 480
        self.height = 190

    def draw(self):
        canvas = self.canv
        nodes = [
            (12, 125, 88, 36, "Upload", ACCENT),
            (108, 125, 88, 36, "Preprocess", INK),
            (204, 125, 88, 36, "OCR", WARM),
            (300, 125, 88, 36, "Concepts", ACCENT),
            (396, 125, 72, 36, "Score", INK),
            (80, 48, 130, 38, "SQLite history", INK),
            (270, 48, 130, 38, "PDF report", WARM),
        ]
        for x, y, width, height, label, fill in nodes:
            canvas.setFillColor(fill)
            canvas.setStrokeColor(fill)
            canvas.roundRect(x, y, width, height, 5, fill=1, stroke=1)
            canvas.setFillColor(colors.white)
            canvas.setFont("Helvetica-Bold", 8.5)
            canvas.drawCentredString(x + width / 2, y + 13, label)

        for start_x, end_x in [(100, 108), (196, 204), (292, 300), (388, 396)]:
            self._arrow(canvas, start_x, 143, end_x, 143)
        self._arrow(canvas, 432, 125, 330, 86)
        self._arrow(canvas, 432, 125, 145, 86)

    @staticmethod
    def _arrow(canvas, x1, y1, x2, y2):
        canvas.setStrokeColor(MUTED)
        canvas.setFillColor(MUTED)
        canvas.setLineWidth(1.2)
        canvas.line(x1, y1, x2, y2)
        canvas.circle(x2, y2, 2, fill=1, stroke=0)


class ComponentDiagram(Flowable):
    def __init__(self):
        super().__init__()
        self.width = 480
        self.height = 235

    def draw(self):
        canvas = self.canv
        components = [
            (175, 185, 130, 34, "Flask Application", ACCENT),
            (10, 105, 105, 42, "OCR Engine\nTesseract / TrOCR", INK),
            (130, 105, 105, 42, "OpenCV\nPreprocessor", WARM),
            (250, 105, 105, 42, "NLP Evaluator\nscikit-learn", ACCENT),
            (370, 105, 100, 42, "Report Service\nReportLab", INK),
            (95, 25, 120, 38, "SQLite Database", INK),
            (275, 25, 120, 38, "Web Dashboard", WARM),
        ]
        for x, y, width, height, label, fill in components:
            canvas.setFillColor(fill)
            canvas.setStrokeColor(fill)
            canvas.roundRect(x, y, width, height, 5, fill=1, stroke=1)
            canvas.setFillColor(colors.white)
            canvas.setFont("Helvetica-Bold", 8)
            lines = label.split("\n")
            for index, line in enumerate(lines):
                canvas.drawCentredString(x + width / 2, y + height / 2 + 4 - (index * 10), line)

        for x in (62, 182, 302, 420):
            WorkflowDiagram._arrow(canvas, 240, 185, x, 147)
        WorkflowDiagram._arrow(canvas, 240, 185, 155, 63)
        WorkflowDiagram._arrow(canvas, 240, 185, 335, 63)


def styles():
    result = getSampleStyleSheet()
    result.add(
        ParagraphStyle(
            name="doc_title",
            parent=result["Title"],
            fontName="Helvetica-Bold",
            fontSize=25,
            leading=29,
            textColor=INK,
            alignment=TA_CENTER,
            spaceAfter=5 * mm,
        )
    )
    result.add(
        ParagraphStyle(
            name="doc_subtitle",
            parent=result["BodyText"],
            fontName="Helvetica",
            fontSize=11,
            leading=15,
            textColor=MUTED,
            alignment=TA_CENTER,
            spaceAfter=5 * mm,
        )
    )
    result.add(
        ParagraphStyle(
            name="section",
            parent=result["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=19,
            textColor=INK,
            spaceBefore=3 * mm,
            spaceAfter=3 * mm,
        )
    )
    result.add(
        ParagraphStyle(
            name="subsection",
            parent=result["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11.5,
            leading=14,
            textColor=ACCENT,
            spaceBefore=2 * mm,
            spaceAfter=2 * mm,
        )
    )
    result.add(
        ParagraphStyle(
            name="body_clean",
            parent=result["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13.2,
            textColor=INK,
            spaceAfter=2.4 * mm,
        )
    )
    result.add(
        ParagraphStyle(
            name="note",
            parent=result["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=12.5,
            textColor=INK,
            backColor=ACCENT_SOFT,
            borderColor=ACCENT,
            borderWidth=0.6,
            borderPadding=8,
            spaceBefore=2 * mm,
            spaceAfter=3 * mm,
        )
    )
    result.add(
        ParagraphStyle(
            name="table_header_doc",
            parent=result["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.white,
        )
    )
    result.add(
        ParagraphStyle(
            name="table_body_doc",
            parent=result["BodyText"],
            fontName="Helvetica",
            fontSize=8.2,
            leading=10.5,
            textColor=INK,
        )
    )
    return result


def paragraph(text, style):
    return Paragraph(escape(text), style)


def table(rows, widths, style_sheet):
    formatted = []
    for row_index, row in enumerate(rows):
        row_style = style_sheet["table_header_doc" if row_index == 0 else "table_body_doc"]
        formatted.append([cell if isinstance(cell, Paragraph) else paragraph(str(cell), row_style) for cell in row])
    result = Table(formatted, colWidths=widths, repeatRows=1, hAlign="LEFT")
    result.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), INK),
                ("GRID", (0, 0), (-1, -1), 0.45, LINE),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAF9")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return result


def bullet(text, style_sheet):
    return Paragraph(f"&#8226; {escape(text)}", style_sheet["body_clean"])


def build_document():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    style_sheet = styles()
    document = SimpleDocTemplate(
        str(OUTPUT_PATH),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=17 * mm,
        title="AI Answer Sheet Evaluator Technical Documentation",
        author="AI Answer Sheet Evaluator Project",
    )
    story = []

    story.append(Spacer(1, 25 * mm))
    story.append(Paragraph("AI Answer Sheet Evaluator", style_sheet["doc_title"]))
    story.append(Paragraph("Technical Documentation and Teacher Presentation Guide", style_sheet["doc_subtitle"]))
    story.append(Spacer(1, 8 * mm))
    story.append(
        Paragraph(
            "A local-first system for evaluating handwritten, scanned, and digital answer sheets "
            "against expected answers and teacher marking points.",
            style_sheet["note"],
        )
    )
    story.append(Spacer(1, 10 * mm))
    story.append(
        table(
            [
                ["Project field", "Value"],
                ["Version", "3.0.0"],
                ["Application type", "Local Flask web application"],
                ["Primary goal", "OCR-tolerant automated answer evaluation"],
                ["Primary input", "PDF and image answer sheets"],
                ["Primary output", "Scores, feedback, history, and PDF reports"],
                ["Documentation date", date.today().isoformat()],
                ["Repository", "https://github.com/gourav34135/Ai_answersheet_evaulation_system"],
            ],
            [48 * mm, 118 * mm],
            style_sheet,
        )
    )
    story.append(PageBreak())

    story.append(Paragraph("1. Executive Summary", style_sheet["section"]))
    story.append(
        Paragraph(
            "The AI Answer Sheet Evaluator is designed to reduce the time required to review descriptive "
            "answers while keeping a teacher in control of the expected answer and marking rubric. The user "
            "can upload any supported answer-sheet file, enter any question and expected answer, and receive "
            "an overall score plus per-question evidence.",
            style_sheet["body_clean"],
        )
    )
    story.append(
        Paragraph(
            "The central technical challenge is that handwriting OCR is imperfect. A correct answer may be "
            "transcribed with spelling errors. The project addresses this by combining image preprocessing, "
            "OCR, reference-assisted cleanup, fuzzy concept matching, semantic similarity, character n-gram "
            "similarity, rubric coverage, and completeness analysis.",
            style_sheet["body_clean"],
        )
    )
    story.append(Paragraph("2. Project Objectives", style_sheet["section"]))
    for item in [
        "Accept arbitrary PDF and image answer sheets rather than a fixed sample.",
        "Allow teachers or students to supply their own questions, expected answers, marking points, and maximum score.",
        "Provide fair credit when OCR contains character-level mistakes but the correct concepts remain detectable.",
        "Generate per-question results and a downloadable evidence-based PDF report.",
        "Keep uploaded files and history local for privacy and offline operation.",
    ]:
        story.append(bullet(item, style_sheet))

    story.append(Paragraph("3. End-to-End Workflow", style_sheet["section"]))
    story.append(WorkflowDiagram())
    story.append(
        Paragraph(
            "The uploaded document is validated, rendered when necessary, preprocessed, transcribed, cleaned "
            "using expected-answer vocabulary, evaluated using multiple NLP signals, saved locally, and converted "
            "into a downloadable report.",
            style_sheet["body_clean"],
        )
    )
    story.append(PageBreak())

    story.append(Paragraph("4. Software Architecture", style_sheet["section"]))
    story.append(ComponentDiagram())
    story.append(
        table(
            [
                ["Component", "Responsibility"],
                ["Flask application", "Routes, upload validation, evaluation orchestration, history, and downloads"],
                ["OCR engine", "Digital PDF extraction, Tesseract OCR, and optional TrOCR recognition"],
                ["Image preprocessor", "Upscaling, ink isolation, denoising, thresholding, deskewing, and line cleanup"],
                ["NLP evaluator", "Semantic, fuzzy, concept, rubric, completeness, and per-question scoring"],
                ["SQLite database", "Local persistence of results, feedback, and OCR text"],
                ["Report service", "Professional PDF evaluation report generation"],
                ["Web dashboard", "Interactive input, progress, result analysis, and history review"],
            ],
            [46 * mm, 120 * mm],
            style_sheet,
        )
    )

    story.append(Paragraph("5. Technology Stack", style_sheet["section"]))
    story.append(
        table(
            [
                ["Technology", "Use in project"],
                ["Python", "Core application language and evaluation implementation"],
                ["Flask / Werkzeug", "Local web server, routes, APIs, uploads, and downloads"],
                ["Tesseract / pytesseract", "Default offline OCR engine"],
                ["Microsoft TrOCR", "Optional transformer model for handwritten single-line recognition"],
                ["OpenCV / Pillow / NumPy", "Document-image preprocessing"],
                ["PyMuPDF", "PDF rendering and digital-text extraction"],
                ["scikit-learn", "Word and character TF-IDF cosine similarity"],
                ["difflib", "OCR-tolerant fuzzy token matching"],
                ["SQLite", "Local evaluation history"],
                ["ReportLab", "Evaluation and technical PDF generation"],
                ["HTML / CSS / JavaScript", "Interactive dashboard"],
                ["unittest", "Regression verification"],
            ],
            [48 * mm, 118 * mm],
            style_sheet,
        )
    )
    story.append(Paragraph("6. OCR Models and Image Processing", style_sheet["section"]))
    story.append(Paragraph("Standard OCR", style_sheet["subsection"]))
    story.append(
        Paragraph(
            "The dependable offline path uses Tesseract. Each scanned PDF page is rendered by PyMuPDF and "
            "preprocessed before OCR. The system tries document-appropriate page segmentation modes and selects "
            "the strongest transcription candidate.",
            style_sheet["body_clean"],
        )
    )
    story.append(Paragraph("Optional Transformer OCR", style_sheet["subsection"]))
    story.append(
        Paragraph(
            "The advanced path uses Microsoft's trocr-base-handwritten model through PyTorch and Hugging Face "
            "Transformers. TrOCR is a pretrained vision-encoder-decoder model fine-tuned on IAM handwritten text "
            "and is intended for single text-line images. The system segments candidate lines before inference.",
            style_sheet["body_clean"],
        )
    )
    story.append(
        Paragraph(
            "A model was not trained from scratch because reliable handwriting-model training requires a large "
            "labeled dataset containing line images and exact transcriptions, substantial GPU compute, and careful "
            "evaluation across different writers. Instead, the project uses pretrained OCR models and calibrates "
            "the downstream evaluator with noisy-OCR regression tests. This is more reproducible for a local academic project.",
            style_sheet["note"],
        )
    )
    story.append(Paragraph("Preprocessing Operations", style_sheet["subsection"]))
    for item in [
        "Border trimming and image upscaling.",
        "Blue and purple ink isolation for ruled-paper answers.",
        "Grayscale conversion, contrast enhancement, and sharpening.",
        "Adaptive thresholding for uneven lighting.",
        "Noise reduction and ruled-line removal.",
        "Deskewing and line-region segmentation.",
    ]:
        story.append(bullet(item, style_sheet))

    story.append(Paragraph("7. Evaluation Algorithms", style_sheet["section"]))
    story.append(
        table(
            [
                ["Signal", "Technical method", "Purpose"],
                ["Semantic similarity", "TF-IDF word n-grams and cosine similarity", "Measures meaning and vocabulary overlap"],
                ["Character similarity", "TF-IDF character 3-5 grams", "Tolerates OCR spelling corruption"],
                ["Concept coverage", "Fuzzy expected-term matching per answer section", "Detects required subject concepts"],
                ["Rubric coverage", "Exact, fuzzy, and generic rubric rules", "Checks marking-point satisfaction"],
                ["Completeness", "Student/reference word-length comparison", "Detects incomplete responses"],
                ["Readability", "Vocabulary diversity and sentence structure", "Adds a small presentation-quality signal"],
                ["Question scoring", "Numbered reference-section evaluation", "Produces per-question evidence"],
            ],
            [34 * mm, 66 * mm, 66 * mm],
            style_sheet,
        )
    )
    story.append(
        Paragraph(
            "The final score is a weighted combination of semantic similarity, concept coverage, rubric coverage, "
            "completeness, readability, and aggregated question results. The weights are configurable in evaluator.py.",
            style_sheet["body_clean"],
        )
    )
    story.append(PageBreak())

    story.append(Paragraph("8. Data, Privacy, and Security", style_sheet["section"]))
    for item in [
        "Uploaded answer sheets are stored only inside the local uploads directory.",
        "Evaluation history is stored in a local SQLite database.",
        "No answer sheet is sent to an external API by the standard OCR path.",
        "File extensions and upload size are validated before processing.",
        "The optional TrOCR model download contacts the model repository only during model installation or first use.",
        "Teachers should review generated scores before using them as final academic grades.",
    ]:
        story.append(bullet(item, style_sheet))

    story.append(Paragraph("9. Main API Endpoints", style_sheet["section"]))
    story.append(
        table(
            [
                ["Method", "Endpoint", "Function"],
                ["POST", "/api/evaluate", "OCR and evaluate an uploaded answer sheet"],
                ["POST", "/api/rescore", "Evaluate supplied text"],
                ["GET", "/api/history", "List saved results"],
                ["DELETE", "/api/history", "Clear local result history"],
                ["GET", "/api/history/<id>", "Load one saved evaluation"],
                ["GET", "/api/report/<id>", "Download the final PDF report"],
                ["GET", "/api/health", "Check application version and Tesseract availability"],
            ],
            [22 * mm, 58 * mm, 86 * mm],
            style_sheet,
        )
    )

    story.append(Paragraph("10. Testing and Validation", style_sheet["section"]))
    story.append(
        Paragraph(
            "The project includes an automated noisy-OCR regression test and was validated using both a multi-page "
            "handwritten machine-learning answer sheet and an unrelated digital science answer sheet. The purpose "
            "of this validation is to confirm that evaluation is based on user-provided expected answers rather than "
            "hard-coded sample content.",
            style_sheet["body_clean"],
        )
    )
    story.append(
        table(
            [
                ["Validation", "Observed result"],
                ["Noisy OCR regression test", "Passed"],
                ["Handwritten multi-page PDF", "Five per-question results and complete rubric analysis"],
                ["Unrelated science PDF", "Two per-question results based on separate science references"],
                ["PDF evaluation report", "Generated and visually inspected"],
                ["Browser dashboard", "Desktop and responsive result surfaces verified"],
            ],
            [62 * mm, 104 * mm],
            style_sheet,
        )
    )
    story.append(PageBreak())

    story.append(Paragraph("11. Installation and Execution", style_sheet["section"]))
    story.append(Paragraph("macOS Standard Setup", style_sheet["subsection"]))
    for command in [
        "brew install tesseract",
        "python3 -m venv .venv",
        "source .venv/bin/activate",
        "pip install -r requirements.txt",
        "python app.py",
        "Open http://127.0.0.1:5000",
    ]:
        story.append(Paragraph(escape(command), style_sheet["note"]))
    story.append(Paragraph("Optional Transformer Setup", style_sheet["subsection"]))
    story.append(Paragraph("python3.12 -m venv .venv-transformer", style_sheet["note"]))
    story.append(Paragraph("source .venv-transformer/bin/activate", style_sheet["note"]))
    story.append(Paragraph("pip install -r requirements-advanced.txt", style_sheet["note"]))

    story.append(Paragraph("12. Limitations", style_sheet["section"]))
    for item in [
        "No OCR model can guarantee perfect transcription of every handwriting style.",
        "Heavy shadows, curved pages, low resolution, and overlapping writing reduce OCR quality.",
        "Reference answers and marking points must be academically correct and sufficiently detailed.",
        "The current evaluator grades concepts but does not independently verify every factual claim.",
        "Transformer OCR requires additional memory, disk space, and model-download time.",
    ]:
        story.append(bullet(item, style_sheet))

    story.append(Paragraph("13. Future Scope", style_sheet["section"]))
    for item in [
        "Fine-tune TrOCR on institution-specific handwritten answer-sheet transcriptions.",
        "Add teacher review and score-adjustment workflows.",
        "Add separate answer-region detection for structured exam templates.",
        "Add multilingual OCR and subject-specific scoring profiles.",
        "Add authentication and class-level analytics for multi-user deployment.",
        "Add calibrated factual-consistency checking with a locally hosted language model.",
    ]:
        story.append(bullet(item, style_sheet))

    story.append(Paragraph("14. Viva Summary", style_sheet["section"]))
    story.append(
        Paragraph(
            "This project is not simply an OCR reader. It is an OCR-tolerant evaluation system. Computer vision "
            "prepares the document, OCR transcribes it, NLP compares meaning and concepts, fuzzy matching reduces "
            "the effect of OCR spelling errors, SQLite stores local evidence, and ReportLab generates a professional "
            "report. The teacher remains responsible for the final academic decision.",
            style_sheet["note"],
        )
    )

    document.build(story, onFirstPage=footer, onLaterPages=footer)
    return OUTPUT_PATH


def footer(canvas, document):
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.line(18 * mm, 12 * mm, A4[0] - 18 * mm, 12 * mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 8 * mm, "AI Answer Sheet Evaluator - Technical Documentation")
    canvas.drawRightString(A4[0] - 18 * mm, 8 * mm, f"Page {document.page}")
    canvas.restoreState()


if __name__ == "__main__":
    print(build_document())
