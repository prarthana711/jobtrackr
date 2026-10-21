import pytest

from app.services.resume_parser import ResumeParseError, extract_text_from_pdf


def test_extracts_text_from_pdf(make_pdf):
    pdf = make_pdf(
        ["Asha Rao - Information Science Engineering", "Skills: Python, SQL and Docker"]
    )
    text = extract_text_from_pdf(pdf)
    assert "Asha Rao" in text
    assert "Skills: Python, SQL and Docker" in text


def test_rejects_corrupt_pdf():
    with pytest.raises(ResumeParseError):
        extract_text_from_pdf(b"%PDF-1.4 this is not really a pdf")


def test_rejects_pdf_without_text(make_pdf):
    with pytest.raises(ResumeParseError, match="scanned"):
        extract_text_from_pdf(make_pdf([]))


def test_rejects_too_many_pages(make_pdf):
    pdf = make_pdf(["Asha Rao - Information Science Engineering"], pages=11)
    with pytest.raises(ResumeParseError, match="too many pages"):
        extract_text_from_pdf(pdf)