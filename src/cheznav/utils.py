from pathlib import Path

BINARY_EXTENSIONS = frozenset(
    {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".bmp",
        ".ico",
        ".webp",
        ".svg",
        ".mp3",
        ".mp4",
        ".wav",
        ".flac",
        ".ogg",
        ".avi",
        ".mkv",
        ".mov",
        ".zip",
        ".gz",
        ".tar",
        ".bz2",
        ".xz",
        ".7z",
        ".rar",
        ".pdf",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".so",
        ".dll",
        ".dylib",
        ".exe",
        ".bin",
        ".o",
        ".a",
        ".ttf",
        ".otf",
        ".woff",
        ".woff2",
        ".pyc",
        ".class",
    }
)


def is_binary(filename: str) -> bool:
    return Path(filename).suffix.lower() in BINARY_EXTENSIONS


def is_binary_content(path: Path) -> bool:
    """Check if file content looks binary (null bytes or fails UTF-8 decode)."""
    try:
        chunk = path.read_bytes()[:8192]
    except OSError:
        return False
    if not chunk:
        return False
    if b"\x00" in chunk:
        return True
    try:
        chunk.decode("utf-8")
    except UnicodeDecodeError:
        return True
    return False
