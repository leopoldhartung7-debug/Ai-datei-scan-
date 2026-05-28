"""Static application constants: categories, extension maps, defaults.

These values are intentionally kept free of any runtime dependency so they can
be imported from anywhere (tests, CLI, GUI, background workers) without side
effects.
"""

from __future__ import annotations

from enum import Enum

APP_NAME = "SmartFolders"
APP_ID = "smartfolders"
ORG_NAME = "SmartFolders"
APP_VERSION = "1.0.0"


class Category(str, Enum):
    """High level file categories produced by the classifier."""

    INVOICE = "invoice"
    CONTRACT = "contract"
    APPLICATION = "application"          # Bewerbung / CV / cover letter
    TAX = "tax"
    UNIVERSITY = "university"
    WORK = "work"
    DOCUMENT = "document"               # generic document fallback
    SCREENSHOT = "screenshot"
    MEME = "meme"
    PHOTO = "photo"
    WALLPAPER = "wallpaper"
    VIDEO = "video"
    MUSIC = "music"
    CODE = "code"
    ARCHIVE = "archive"
    INSTALLER = "installer"
    SPREADSHEET = "spreadsheet"
    PRESENTATION = "presentation"
    EBOOK = "ebook"
    OTHER = "other"

    @property
    def label(self) -> str:
        """Human-readable label for the UI (English)."""
        return _CATEGORY_LABELS.get(self, self.value.title())


_CATEGORY_LABELS: dict[Category, str] = {
    Category.INVOICE: "Invoice",
    Category.CONTRACT: "Contract",
    Category.APPLICATION: "Application",
    Category.TAX: "Tax Document",
    Category.UNIVERSITY: "University",
    Category.WORK: "Work",
    Category.DOCUMENT: "Document",
    Category.SCREENSHOT: "Screenshot",
    Category.MEME: "Meme",
    Category.PHOTO: "Photo",
    Category.WALLPAPER: "Wallpaper",
    Category.VIDEO: "Video",
    Category.MUSIC: "Music",
    Category.CODE: "Code",
    Category.ARCHIVE: "Archive",
    Category.INSTALLER: "Installer",
    Category.SPREADSHEET: "Spreadsheet",
    Category.PRESENTATION: "Presentation",
    Category.EBOOK: "E-Book",
    Category.OTHER: "Other",
}


# Default destination sub-folder (relative to the organized root) per category.
DEFAULT_CATEGORY_FOLDERS: dict[Category, str] = {
    Category.INVOICE: "Documents/Invoices",
    Category.CONTRACT: "Documents/Contracts",
    Category.APPLICATION: "Documents/Applications",
    Category.TAX: "Documents/Tax",
    Category.UNIVERSITY: "Documents/University",
    Category.WORK: "Documents/Work",
    Category.DOCUMENT: "Documents/Other",
    Category.SCREENSHOT: "Pictures/Screenshots",
    Category.MEME: "Pictures/Memes",
    Category.PHOTO: "Pictures/Photos",
    Category.WALLPAPER: "Pictures/Wallpapers",
    Category.VIDEO: "Videos",
    Category.MUSIC: "Music",
    Category.CODE: "Code",
    Category.ARCHIVE: "Archives",
    Category.INSTALLER: "Installers",
    Category.SPREADSHEET: "Documents/Spreadsheets",
    Category.PRESENTATION: "Documents/Presentations",
    Category.EBOOK: "Documents/E-Books",
    Category.OTHER: "Other",
}


# Extension -> category mapping. The classifier uses this as a strong prior,
# then refines it with filename keywords and (optionally) content/OCR.
EXTENSION_CATEGORY: dict[str, Category] = {
    # documents
    ".pdf": Category.DOCUMENT,
    ".doc": Category.DOCUMENT,
    ".docx": Category.DOCUMENT,
    ".odt": Category.DOCUMENT,
    ".rtf": Category.DOCUMENT,
    ".txt": Category.DOCUMENT,
    ".md": Category.DOCUMENT,
    # spreadsheets
    ".xls": Category.SPREADSHEET,
    ".xlsx": Category.SPREADSHEET,
    ".ods": Category.SPREADSHEET,
    ".csv": Category.SPREADSHEET,
    # presentations
    ".ppt": Category.PRESENTATION,
    ".pptx": Category.PRESENTATION,
    ".odp": Category.PRESENTATION,
    # ebooks
    ".epub": Category.EBOOK,
    ".mobi": Category.EBOOK,
    ".azw3": Category.EBOOK,
    # images
    ".png": Category.PHOTO,
    ".jpg": Category.PHOTO,
    ".jpeg": Category.PHOTO,
    ".gif": Category.MEME,
    ".bmp": Category.PHOTO,
    ".tiff": Category.PHOTO,
    ".webp": Category.PHOTO,
    ".heic": Category.PHOTO,
    ".svg": Category.PHOTO,
    # video
    ".mp4": Category.VIDEO,
    ".mkv": Category.VIDEO,
    ".mov": Category.VIDEO,
    ".avi": Category.VIDEO,
    ".webm": Category.VIDEO,
    ".flv": Category.VIDEO,
    # audio
    ".mp3": Category.MUSIC,
    ".wav": Category.MUSIC,
    ".flac": Category.MUSIC,
    ".aac": Category.MUSIC,
    ".ogg": Category.MUSIC,
    ".m4a": Category.MUSIC,
    # code
    ".py": Category.CODE,
    ".js": Category.CODE,
    ".ts": Category.CODE,
    ".jsx": Category.CODE,
    ".tsx": Category.CODE,
    ".html": Category.CODE,
    ".css": Category.CODE,
    ".scss": Category.CODE,
    ".json": Category.CODE,
    ".xml": Category.CODE,
    ".yaml": Category.CODE,
    ".yml": Category.CODE,
    ".toml": Category.CODE,
    ".c": Category.CODE,
    ".cpp": Category.CODE,
    ".h": Category.CODE,
    ".hpp": Category.CODE,
    ".java": Category.CODE,
    ".cs": Category.CODE,
    ".go": Category.CODE,
    ".rs": Category.CODE,
    ".rb": Category.CODE,
    ".php": Category.CODE,
    ".sh": Category.CODE,
    ".sql": Category.CODE,
    ".ipynb": Category.CODE,
    # archives
    ".zip": Category.ARCHIVE,
    ".rar": Category.ARCHIVE,
    ".7z": Category.ARCHIVE,
    ".tar": Category.ARCHIVE,
    ".gz": Category.ARCHIVE,
    ".bz2": Category.ARCHIVE,
    ".xz": Category.ARCHIVE,
    # installers
    ".exe": Category.INSTALLER,
    ".msi": Category.INSTALLER,
    ".dmg": Category.INSTALLER,
    ".deb": Category.INSTALLER,
    ".rpm": Category.INSTALLER,
    ".appimage": Category.INSTALLER,
}

IMAGE_EXTENSIONS = frozenset(
    {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp", ".heic"}
)
TEXT_EXTENSIONS = frozenset({".txt", ".md", ".csv", ".log", ".json", ".xml", ".yaml", ".yml"})
PDF_EXTENSIONS = frozenset({".pdf"})
OCR_EXTENSIONS = IMAGE_EXTENSIONS | PDF_EXTENSIONS
CODE_EXTENSIONS = frozenset(
    ext for ext, cat in EXTENSION_CATEGORY.items() if cat == Category.CODE
)


# Keyword hints used by the lightweight (offline) classifier. Lower-case,
# matched against the filename and any extracted text. German + English so the
# product works for the target (German) audience out of the box.
CATEGORY_KEYWORDS: dict[Category, tuple[str, ...]] = {
    Category.INVOICE: (
        "rechnung", "invoice", "faktura", "quittung", "receipt", "beleg",
        "zahlung", "payment", "betrag", "amount", "mwst", "ust", "vat",
        "amazon", "paypal", "bestellung", "order",
    ),
    Category.CONTRACT: (
        "vertrag", "contract", "mietvertrag", "agreement", "kündigung",
        "lease", "agb", "terms", "vereinbarung", "nda",
    ),
    Category.APPLICATION: (
        "bewerbung", "lebenslauf", "cv", "resume", "anschreiben",
        "cover letter", "motivation", "zeugnis", "certificate",
    ),
    Category.TAX: (
        "steuer", "tax", "finanzamt", "elster", "lohnsteuer",
        "einkommensteuer", "steuerbescheid", "irs",
    ),
    Category.UNIVERSITY: (
        "uni", "university", "vorlesung", "lecture", "klausur", "exam",
        "seminar", "thesis", "bachelor", "master", "hausarbeit", "skript",
        "übung", "assignment", "professor",
    ),
    Category.WORK: (
        "meeting", "projekt", "project", "report", "bericht", "präsentation",
        "protokoll", "minutes", "arbeit", "work", "client", "kunde",
    ),
    Category.SCREENSHOT: ("screenshot", "bildschirmfoto", "capture", "snip", "screen shot"),
    Category.MEME: ("meme", "funny", "lustig", "9gag", "reddit"),
    Category.WALLPAPER: ("wallpaper", "hintergrund", "background", "4k", "1920x1080", "3840x2160"),
    Category.CODE: ("error", "traceback", "exception", "code", "bug", "stacktrace"),
}


# Filenames suggesting a screenshot, used in addition to keyword matching.
SCREENSHOT_NAME_PATTERNS = (
    "screenshot",
    "bildschirmfoto",
    "screen shot",
    "screen_shot",
    "capture",
    "snip",
)


class FileAction(str, Enum):
    """Actions recorded in the history table."""

    DETECTED = "detected"
    CLASSIFIED = "classified"
    RENAMED = "renamed"
    MOVED = "moved"
    OCR = "ocr"
    INDEXED = "indexed"
    DUPLICATE = "duplicate"
    DELETED = "deleted"
    SKIPPED = "skipped"
    ERROR = "error"


class ScanIntensity(str, Enum):
    """How aggressively the background workers consume the machine."""

    ECO = "eco"          # minimal footprint, single worker, throttled
    BALANCED = "balanced"
    PERFORMANCE = "performance"
    TURBO = "turbo"      # use everything, for one-off bulk organizing


# Folders we never touch / index automatically.
IGNORED_DIR_NAMES = frozenset(
    {
        ".git", ".svn", "node_modules", "__pycache__", ".venv", "venv",
        "$RECYCLE.BIN", "System Volume Information", "AppData", ".cache",
        "site-packages", ".smartfolders",
    }
)

# Temporary / partial download files that should be ignored until finished.
IGNORED_SUFFIXES = (".tmp", ".crdownload", ".part", ".partial", ".download", "~")

# Maximum size (bytes) of a text file we will read fully for indexing.
MAX_TEXT_INDEX_BYTES = 1_000_000
