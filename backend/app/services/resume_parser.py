import io

import pdfplumber

MAX_PAGES = 10
MIN_TEXT_CHARS = 30


class ResumeParseError(Exception):
    """Raised when a PDF cannot be turned into usable text."""


def extract_text_from_pdf(data: bytes) -> str:
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            if len(pdf.pages) > MAX_PAGES:
                raise ResumeParseError(f"PDF has too many pages (max {MAX_PAGES})")
            pages = [page.extract_text() or "" for page in pdf.pages]
    except ResumeParseError:
        raise
    except Exception as exc:  # corrupted, password-protected, malformed...
        raise ResumeParseError(
            "Could not read this PDF. It may be corrupted or password-protected."
        ) from exc

    # PostgreSQL refuses text containing NUL characters, so remove them now
    text = "\n".join(pages).replace("\x00", "").strip()

    if len(text) < MIN_TEXT_CHARS:
        raise ResumeParseError(
            "No readable text found. This looks like a scanned or image-only PDF; "
            "please upload a text-based PDF."
        )
    return text