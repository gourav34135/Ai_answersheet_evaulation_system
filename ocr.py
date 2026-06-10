from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter


class OCRDependencyError(RuntimeError):
    pass


def _import_pytesseract():
    try:
        import pytesseract

        return pytesseract
    except ImportError as exc:
        raise OCRDependencyError(
            "pytesseract is not installed. Run: pip install -r requirements.txt"
        ) from exc


def _preprocess_image(image: Image.Image) -> Image.Image:
    image = image.convert("L")
    image = ImageEnhance.Contrast(image).enhance(1.8)
    image = image.filter(ImageFilter.SHARPEN)
    return image


def extract_text_from_image(path: Path) -> str:
    pytesseract = _import_pytesseract()
    try:
        image = Image.open(path)
    except Exception as exc:
        raise OCRDependencyError(f"Could not open image file: {exc}") from exc

    processed = _preprocess_image(image)
    try:
        return pytesseract.image_to_string(processed, config="--psm 6").strip()
    except Exception as exc:
        if exc.__class__.__name__ == "TesseractNotFoundError":
            raise OCRDependencyError("Tesseract is not installed. On Mac, run: brew install tesseract") from exc
        raise


def extract_text_from_pdf(path: Path) -> str:
    pytesseract = _import_pytesseract()
    try:
        import fitz
    except ImportError as exc:
        raise OCRDependencyError("PyMuPDF is not installed. Run: pip install -r requirements.txt") from exc

    texts: list[str] = []
    try:
        document = fitz.open(path)
    except Exception as exc:
        raise OCRDependencyError(f"Could not open PDF file: {exc}") from exc

    for page in document:
        digital_text = page.get_text("text").strip()
        if len(digital_text) > 30:
            texts.append(digital_text)
            continue

        pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
        processed = _preprocess_image(image)
        try:
            page_text = pytesseract.image_to_string(processed, config="--psm 6").strip()
        except Exception as exc:
            if exc.__class__.__name__ == "TesseractNotFoundError":
                raise OCRDependencyError("Tesseract is not installed. On Mac, run: brew install tesseract") from exc
            raise
        if page_text:
            texts.append(page_text)

    return "\n\n".join(texts).strip()


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_text_from_pdf(path)
    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff"}:
        return extract_text_from_image(path)
    raise OCRDependencyError("Unsupported file type. Please upload PDF, JPG, PNG, WEBP, or TIFF.")
