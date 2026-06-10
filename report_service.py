from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from config import DATA_DIR


INK = colors.HexColor("#193238")
ACCENT = colors.HexColor("#0F766E")
ACCENT_SOFT = colors.HexColor("#DDF3EE")
WARM = colors.HexColor("#C47B25")
LINE = colors.HexColor("#D6E0DE")
MUTED = colors.HexColor("#66767A")


def create_evaluation_report(item: dict) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    report_path = DATA_DIR / f"evaluation_report_{item['id']}.pdf"
    styles = _styles()
    result = item["result"]

    document = SimpleDocTemplate(
        str(report_path),
        pagesize=A4,
        rightMargin=17 * mm,
        leftMargin=17 * mm,
        topMargin=17 * mm,
        bottomMargin=16 * mm,
        title=f"Evaluation Report - {item['student_name']}",
        author="AI Answer Sheet Evaluator",
    )
    story = []

    story.extend(_cover_block(item, result, styles))
    story.append(Spacer(1, 7 * mm))
    story.extend(_metric_section(result, styles))
    story.append(Spacer(1, 6 * mm))
    story.extend(_question_section(result, styles))
    story.append(Spacer(1, 6 * mm))
    story.extend(_rubric_section(result, styles))
    story.append(Spacer(1, 6 * mm))
    story.extend(_feedback_section(result, styles))
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph("OCR Review Appendix", styles["section_heading"]))
    story.append(
        Paragraph(
            "This appendix contains the OCR transcription used by the evaluator. "
            "Handwriting OCR can contain character-level errors; scoring also uses fuzzy concept matching.",
            styles["note"],
        )
    )
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(_safe(item["extracted_text"]).replace("\n", "<br/>"), styles["ocr"]))

    document.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return report_path


def _styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="report_title",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=23,
            leading=27,
            textColor=INK,
            alignment=TA_CENTER,
            spaceAfter=4 * mm,
        )
    )
    styles.add(
        ParagraphStyle(
            name="score",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=31,
            leading=34,
            textColor=ACCENT,
            alignment=TA_CENTER,
        )
    )
    styles.add(
        ParagraphStyle(
            name="section_heading",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=18,
            textColor=INK,
            spaceBefore=1 * mm,
            spaceAfter=3 * mm,
        )
    )
    styles.add(
        ParagraphStyle(
            name="table_header",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.white,
        )
    )
    styles.add(
        ParagraphStyle(
            name="body_compact",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13,
            textColor=INK,
        )
    )
    styles.add(
        ParagraphStyle(
            name="small",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=MUTED,
        )
    )
    styles.add(
        ParagraphStyle(
            name="note",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=INK,
            backColor=ACCENT_SOFT,
            borderColor=ACCENT,
            borderWidth=0.6,
            borderPadding=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ocr",
            parent=styles["BodyText"],
            fontName="Courier",
            fontSize=7.5,
            leading=10,
            textColor=INK,
        )
    )
    return styles


def _cover_block(item, result, styles):
    score = result.get("score", item["score"])
    max_score = result.get("max_score", item["max_score"])
    meta = Table(
        [
            [Paragraph("<b>Student</b>", styles["small"]), Paragraph(_safe(item["student_name"]), styles["body_compact"])],
            [Paragraph("<b>Answer sheet</b>", styles["small"]), Paragraph(_safe(item["file_name"]), styles["body_compact"])],
            [Paragraph("<b>Evaluated</b>", styles["small"]), Paragraph(_safe(item["created_at"]), styles["body_compact"])],
            [Paragraph("<b>Confidence</b>", styles["small"]), Paragraph(_safe(item["confidence"]), styles["body_compact"])],
        ],
        colWidths=[34 * mm, 120 * mm],
    )
    meta.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), ACCENT_SOFT),
                ("GRID", (0, 0), (-1, -1), 0.4, LINE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return [
        Paragraph("AI Answer Sheet Evaluation Report", styles["report_title"]),
        Paragraph(f"{score:g} / {max_score:g}", styles["score"]),
        Paragraph("OCR-tolerant semantic and rubric evaluation", styles["small"]),
        Spacer(1, 6 * mm),
        meta,
    ]


def _metric_section(result, styles):
    metrics = result.get("metrics", {})
    rows = [
        ["Metric", "Value", "Interpretation"],
        ["Semantic similarity", _percent(metrics.get("semantic_similarity", 0)), "Meaning alignment with expected answers"],
        ["Concept coverage", _percent(metrics.get("concept_coverage", 0)), "Expected subject concepts detected"],
        ["Rubric coverage", _percent(metrics.get("key_point_coverage", 0)), "Teacher marking points satisfied"],
        ["Completeness", _percent(metrics.get("answer_completeness", 0)), "Answer length and response completeness"],
        ["Recognized words", str(metrics.get("word_count", 0)), "OCR words used during evaluation"],
    ]
    table = _styled_table(rows, [46 * mm, 28 * mm, 80 * mm], styles)
    return [Paragraph("Evaluation Breakdown", styles["section_heading"]), table]


def _question_section(result, styles):
    question_results = result.get("question_results", [])
    if not question_results:
        return []

    rows = [["#", "Question", "Score", "Concepts", "Status"]]
    for question in question_results:
        rows.append(
            [
                str(question["number"]),
                Paragraph(_safe(question["title"]), styles["body_compact"]),
                f"{question['score']:g} / {question['max_score']:g}",
                _percent(question["concept_coverage"]),
                question["status"],
            ]
        )
    table = _styled_table(rows, [10 * mm, 84 * mm, 25 * mm, 22 * mm, 27 * mm], styles)
    return [Paragraph("Question-Level Results", styles["section_heading"]), table]


def _rubric_section(result, styles):
    matched = result.get("matched_points", [])
    missing = result.get("missing_points", [])
    rows = [["Status", "Rubric point"]]
    rows.extend([["Matched", Paragraph(_safe(point), styles["body_compact"])] for point in matched])
    rows.extend([["Review", Paragraph(_safe(point), styles["body_compact"])] for point in missing])
    if len(rows) == 1:
        rows.append(["Not supplied", "No marking points were provided."])
    table = _styled_table(rows, [28 * mm, 140 * mm], styles)
    return [Paragraph("Rubric Findings", styles["section_heading"]), table]


def _feedback_section(result, styles):
    feedback = result.get("feedback", [])
    blocks = [Paragraph("Feedback", styles["section_heading"])]
    for index, item in enumerate(feedback, start=1):
        blocks.append(
            KeepTogether(
                [
                    Paragraph(f"<b>{index}.</b> {_safe(item)}", styles["body_compact"]),
                    Spacer(1, 1.5 * mm),
                ]
            )
        )
    return blocks


def _styled_table(rows, widths, styles):
    normalized = []
    for row_index, row in enumerate(rows):
        normalized.append(
            [
                cell
                if isinstance(cell, Paragraph)
                else Paragraph(_safe(cell), styles["table_header" if row_index == 0 else "body_compact"])
                for cell in row
            ]
        )
    table = Table(normalized, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), INK),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.4, LINE),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAF9")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _footer(canvas, document):
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.line(17 * mm, 12 * mm, A4[0] - 17 * mm, 12 * mm)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(17 * mm, 8 * mm, "Generated locally by AI Answer Sheet Evaluator")
    canvas.drawRightString(A4[0] - 17 * mm, 8 * mm, f"Page {document.page}")
    canvas.restoreState()


def _safe(value) -> str:
    return escape(str(value or ""))


def _percent(value) -> str:
    try:
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return "0.0%"
