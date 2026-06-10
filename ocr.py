import re
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np
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


def _import_cv2():
    try:
        import cv2

        return cv2
    except ImportError as exc:
        raise OCRDependencyError("OpenCV is not installed. Run: pip install -r requirements.txt") from exc


def _to_cv_image(image: Image.Image):
    cv2 = _import_cv2()
    rgb = image.convert("RGB")
    return cv2.cvtColor(np.array(rgb), cv2.COLOR_RGB2BGR)


def _to_pil_image(cv_image) -> Image.Image:
    cv2 = _import_cv2()
    if len(cv_image.shape) == 2:
        return Image.fromarray(cv_image)
    rgb = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
    return Image.fromarray(rgb)


def _trim_border(cv_image, border_ratio: float = 0.015):
    height, width = cv_image.shape[:2]
    top = int(height * border_ratio)
    bottom = int(height * (1 - border_ratio))
    left = int(width * border_ratio)
    right = int(width * (1 - border_ratio))
    return cv_image[top:bottom, left:right]


def _upscale(cv_image, scale: float = 2.5):
    cv2 = _import_cv2()
    height, width = cv_image.shape[:2]
    return cv2.resize(
        cv_image,
        (int(width * scale), int(height * scale)),
        interpolation=cv2.INTER_CUBIC,
    )


def _deskew_binary(binary_image):
    cv2 = _import_cv2()
    coords = np.column_stack(np.where(binary_image < 220))
    if coords.size == 0:
        return binary_image

    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    if abs(angle) < 0.25 or abs(angle) > 8:
        return binary_image

    height, width = binary_image.shape[:2]
    center = (width // 2, height // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(
        binary_image,
        matrix,
        (width, height),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )


def _blue_ink_variant(image: Image.Image) -> Image.Image:
    cv2 = _import_cv2()
    cv_image = _upscale(_trim_border(_to_cv_image(image)), scale=2.7)
    hsv = cv2.cvtColor(cv_image, cv2.COLOR_BGR2HSV)

    # Handwritten answers are commonly blue/purple ink. This mask removes most
    # low-saturation notebook lines and paper shadows before OCR.
    lower_blue = np.array([85, 35, 20])
    upper_blue = np.array([165, 255, 230])
    mask = cv2.inRange(hsv, lower_blue, upper_blue)

    kernel = np.ones((2, 2), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)
    mask = cv2.dilate(mask, kernel, iterations=1)

    binary = np.full(mask.shape, 255, dtype=np.uint8)
    binary[mask > 0] = 0
    binary = _deskew_binary(binary)
    return _to_pil_image(binary)


def _adaptive_threshold_variant(image: Image.Image) -> Image.Image:
    cv2 = _import_cv2()
    cv_image = _upscale(_trim_border(_to_cv_image(image)), scale=2.4)
    gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
    gray = cv2.fastNlMeansDenoising(gray, None, 18, 7, 21)
    gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
    binary = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        35,
        15,
    )
    binary = _remove_ruled_lines(binary)
    binary = _deskew_binary(binary)
    return _to_pil_image(binary)


def _remove_ruled_lines(binary_image):
    cv2 = _import_cv2()
    inverted = 255 - binary_image
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (55, 1))
    detected_lines = cv2.morphologyEx(inverted, cv2.MORPH_OPEN, horizontal_kernel, iterations=1)
    cleaned = inverted - detected_lines
    return 255 - cleaned


def _ocr_text(pytesseract, image: Image.Image, psm: int) -> str:
    config = f"--oem 1 --psm {psm} -c preserve_interword_spaces=1"
    try:
        return pytesseract.image_to_string(image, config=config).strip()
    except Exception as exc:
        if exc.__class__.__name__ == "TesseractNotFoundError":
            raise OCRDependencyError("Tesseract is not installed. On Mac, run: brew install tesseract") from exc
        raise


def _clean_ocr_text(text: str) -> str:
    replacements = {
        "|": " ",
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
        "—": "-",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)

    lines = []
    for line in text.splitlines():
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines).strip()


def correct_text_with_context(text: str, context: str) -> str:
    """Correct likely OCR word errors using reference/rubric vocabulary."""
    if not text.strip() or not context.strip():
        return text

    vocabulary = _context_vocabulary(context)
    if not vocabulary:
        return text

    def replace_token(match: re.Match) -> str:
        token = match.group(0)
        lower_token = token.lower()
        if len(lower_token) < 4 or lower_token in vocabulary:
            return token

        best_word = ""
        best_score = 0.0
        for word in vocabulary:
            if abs(len(word) - len(lower_token)) > max(3, len(word) // 2):
                continue
            score = SequenceMatcher(None, lower_token, word).ratio()
            if lower_token[0] == word[0]:
                score += 0.04
            if len(lower_token) >= 6 and lower_token[-3:] == word[-3:]:
                score += 0.08
            if score > best_score:
                best_score = score
                best_word = word

        threshold = 0.62 if len(lower_token) >= 6 else 0.74
        if best_word and best_score >= threshold:
            return _match_case(token, best_word)
        return token

    return re.sub(r"[A-Za-z]{4,}", replace_token, text)


def _context_vocabulary(context: str) -> set[str]:
    words = re.findall(r"[A-Za-z]{4,}", context.lower())
    blocked = {
        "this",
        "that",
        "with",
        "from",
        "they",
        "their",
        "there",
        "then",
        "than",
        "will",
        "also",
        "many",
        "other",
    }
    return {word for word in words if word not in blocked}


def _match_case(source: str, replacement: str) -> str:
    if source.isupper():
        return replacement.upper()
    if source[:1].isupper():
        return replacement.capitalize()
    return replacement


def _quality_score(text: str) -> float:
    cleaned = _clean_ocr_text(text)
    if not cleaned:
        return 0.0

    words = re.findall(r"[A-Za-z]{2,}", cleaned)
    weird = re.findall(r"[^A-Za-z0-9\s.,;:?!'\"()/-]", cleaned)
    lowercase_words = [word.lower() for word in words]
    common_hits = sum(
        word in {
            "the",
            "and",
            "that",
            "what",
            "is",
            "are",
            "from",
            "with",
            "without",
            "machine",
            "learning",
            "data",
            "used",
            "system",
            "image",
            "speech",
        }
        for word in lowercase_words
    )
    avg_word_len = (sum(len(word) for word in words) / len(words)) if words else 0
    natural_length_bonus = 1.0 if 3 <= avg_word_len <= 10 else 0.0
    return (len(words) * 1.8) + (common_hits * 4.0) + natural_length_bonus - (len(weird) * 3.5)


def _best_ocr_result(
    pytesseract,
    variants: list[Image.Image],
    original_image: Image.Image | None = None,
) -> str:
    candidates = []
    for variant in variants:
        for psm in (6, 11, 12):
            text = _ocr_text(pytesseract, variant, psm)
            candidates.append((_quality_score(text), text))
        line_text = _ocr_lines(pytesseract, variant)
        if line_text:
            candidates.append((_quality_score(line_text), line_text))

    if original_image is not None:
        ruled_line_text = _ocr_ruled_paper_lines(pytesseract, original_image)
        if ruled_line_text:
            candidates.append((_quality_score(ruled_line_text), ruled_line_text))

    best = max(candidates, key=lambda item: item[0], default=(0.0, ""))
    return _clean_ocr_text(best[1])


def _fast_pdf_ocr(pytesseract, image: Image.Image) -> str:
    """Fast path for multi-page scanned PDFs used during live demonstrations."""
    try:
        primary = _blue_ink_variant(image)
    except Exception:
        primary = _preprocess_image(image)

    candidates = []
    for psm in (6, 11):
        text = _ocr_text(pytesseract, primary, psm)
        candidates.append((_quality_score(text), text))
    best = max(candidates, key=lambda item: item[0], default=(0.0, ""))
    return _clean_ocr_text(best[1])


def _ocr_ruled_paper_lines(pytesseract, image: Image.Image) -> str:
    line_boxes = _detect_ruled_line_bands(image)
    if len(line_boxes) < 3:
        return ""

    lines = []
    for top, bottom in line_boxes:
        if bottom - top < 24:
            continue

        crop = image.crop((0, top, image.width, bottom))
        try:
            prepared = _blue_ink_variant(crop)
        except Exception:
            prepared = _preprocess_image(crop)

        if _ink_density(prepared) < 0.002:
            continue

        line_candidates = []
        for psm in (7, 13):
            text = _ocr_text(pytesseract, prepared, psm)
            line_candidates.append((_quality_score(text), text))
        best_line = _clean_ocr_text(max(line_candidates, key=lambda item: item[0])[1])
        if best_line and _quality_score(best_line) > 1:
            lines.append(best_line)

    return "\n".join(lines)


def _detect_ruled_line_bands(image: Image.Image) -> list[tuple[int, int]]:
    cv2 = _import_cv2()
    cv_image = _to_cv_image(image)
    gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)

    dark = cv2.threshold(gray, 185, 255, cv2.THRESH_BINARY_INV)[1]
    kernel_width = max(80, image.width // 3)
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_width, 1))
    line_mask = cv2.morphologyEx(dark, cv2.MORPH_OPEN, horizontal_kernel, iterations=1)

    row_counts = line_mask.sum(axis=1) / 255
    threshold = image.width * 0.25
    groups = []
    start = None
    for y, count in enumerate(row_counts):
        if count > threshold and start is None:
            start = y
        elif count <= threshold and start is not None:
            if y - start >= 1:
                groups.append((start, y))
            start = None
    if start is not None:
        groups.append((start, image.height - 1))

    centers = [int((top + bottom) / 2) for top, bottom in groups]
    centers = _dedupe_sorted_positions(centers, min_gap=max(24, image.height // 18))
    if len(centers) < 2:
        centers = _hough_horizontal_line_positions(gray, image.width, image.height)
    if len(centers) < 2:
        return []

    positions = [0, *centers, image.height]
    bands = []
    for upper, lower in zip(positions, positions[1:]):
        top = min(image.height, max(0, upper + 3))
        bottom = min(image.height, max(0, lower - 3))
        if bottom > top:
            bands.append((top, bottom))
    return bands


def _hough_horizontal_line_positions(gray, width: int, height: int) -> list[int]:
    cv2 = _import_cv2()
    edges = cv2.Canny(gray, 30, 110)
    lines = cv2.HoughLinesP(
        edges,
        1,
        np.pi / 180,
        threshold=55,
        minLineLength=int(width * 0.42),
        maxLineGap=70,
    )
    if lines is None:
        return []

    positions = []
    for x1, y1, x2, y2 in lines[:, 0]:
        if abs(y2 - y1) <= max(8, height * 0.026) and abs(x2 - x1) >= width * 0.42:
            positions.append(int((y1 + y2) / 2))
    return _dedupe_sorted_positions(positions, min_gap=max(28, height // 17))


def _dedupe_sorted_positions(values: list[int], min_gap: int) -> list[int]:
    result = []
    for value in sorted(values):
        if not result or value - result[-1] >= min_gap:
            result.append(value)
    return result


def _ink_density(image: Image.Image) -> float:
    gray = np.array(image.convert("L"))
    return float((gray < 210).sum()) / float(gray.size)


def _ocr_lines(pytesseract, image: Image.Image) -> str:
    line_images = _segment_line_images(image)
    if len(line_images) < 2:
        return ""

    lines = []
    for line_image in line_images:
        line_candidates = []
        for psm in (7, 13):
            text = _ocr_text(pytesseract, line_image, psm)
            line_candidates.append((_quality_score(text), text))
        best_line = _clean_ocr_text(max(line_candidates, key=lambda item: item[0])[1])
        if best_line and _quality_score(best_line) > 2:
            lines.append(best_line)

    return "\n".join(lines)


def _segment_line_images(image: Image.Image) -> list[Image.Image]:
    cv2 = _import_cv2()
    gray = np.array(image.convert("L"))
    height, width = gray.shape
    ink = gray < 210
    row_counts = ink.sum(axis=1).astype(np.float32)
    smooth_kernel = np.ones(19, dtype=np.float32) / 19
    smoothed = np.convolve(row_counts, smooth_kernel, mode="same")
    threshold = max(8.0, width * 0.006)

    bands = []
    start = None
    for index, count in enumerate(smoothed):
        if count > threshold and start is None:
            start = index
        elif count <= threshold and start is not None:
            if index - start > 12:
                bands.append([start, index])
            start = None
    if start is not None and height - start > 12:
        bands.append([start, height])

    merged = []
    for top, bottom in bands:
        if merged and top - merged[-1][1] < 20:
            merged[-1][1] = bottom
        else:
            merged.append([top, bottom])

    line_images = []
    for top, bottom in merged:
        top = max(0, top - 12)
        bottom = min(height, bottom + 12)
        line = gray[top:bottom, :]

        ink_cols = np.where((line < 210).sum(axis=0) > 0)[0]
        if ink_cols.size > 0:
            left = max(0, int(ink_cols.min()) - 18)
            right = min(width, int(ink_cols.max()) + 18)
            line = line[:, left:right]

        if line.shape[0] < 18 or line.shape[1] < 60:
            continue

        line = cv2.copyMakeBorder(line, 18, 18, 24, 24, cv2.BORDER_CONSTANT, value=255)
        line_images.append(_to_pil_image(line))

    return line_images


def _preprocessed_variants(image: Image.Image) -> list[Image.Image]:
    variants = []
    try:
        variants.append(_blue_ink_variant(image))
        variants.append(_adaptive_threshold_variant(image))
    except OCRDependencyError:
        raise
    except Exception:
        pass

    variants.append(_preprocess_image(image))
    return variants


def extract_text_from_image(path: Path) -> str:
    pytesseract = _import_pytesseract()
    try:
        image = Image.open(path)
    except Exception as exc:
        raise OCRDependencyError(f"Could not open image file: {exc}") from exc

    return _best_ocr_result(pytesseract, _preprocessed_variants(image), image)


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
        page_text = _fast_pdf_ocr(pytesseract, image)
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
