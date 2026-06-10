from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
APP_VERSION = "3.0.0"
UPLOAD_DIR = BASE_DIR / "uploads"
DATA_DIR = BASE_DIR / "data"
DATABASE_PATH = DATA_DIR / "evaluations.db"

ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "webp", "tif", "tiff"}
MAX_CONTENT_LENGTH = 25 * 1024 * 1024

DEFAULT_MAX_SCORE = 10.0
