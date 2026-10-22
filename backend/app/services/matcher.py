from dataclasses import dataclass

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.services.skills import extract_skills

# How much each part counts towards the final score (must add up to 1)
SKILL_WEIGHT = 0.7
TEXT_WEIGHT = 0.3

# A resume and a job posting rarely exceed ~0.3 cosine similarity, even when they
# fit well. A cosine of this value or higher counts as a 100% text match.
# This is a judgement call: tune it using your own evaluation table.
TEXT_SIMILARITY_CAP = 0.4


@dataclass
class MatchOutcome:
    score: float
    skill_score: float | None  # None when the job lists no skills we recognise
    text_score: float
    matched_skills: list[str]
    missing_skills: list[str]


def skill_overlap(
    resume_skills: list[str], job_skills: list[str]
) -> tuple[list[str], list[str], float | None]:
    """Which of the job's skills does the resume cover?"""
    resume_set, job_set = set(resume_skills), set(job_skills)
    matched = sorted(resume_set & job_set)
    missing = sorted(job_set - resume_set)
    score = None if not job_set else 100 * len(matched) / len(job_set)
    return matched, missing, score


def text_similarity(resume_text: str, job_text: str) -> float:
    """TF-IDF + cosine similarity, scaled to 0-100."""
    vectorizer = TfidfVectorizer(
        stop_words="english",  # ignore words like "the", "and", "with"
        ngram_range=(1, 2),  # count single words and pairs of words
        sublinear_tf=True,  # saying "python" 20 times doesn't count 20x
    )
    try:
        matrix = vectorizer.fit_transform([resume_text, job_text])
    except ValueError:  # nothing left after removing stop words
        return 0.0
    cosine = float(cosine_similarity(matrix[0], matrix[1])[0][0])
    return 100 * min(cosine / TEXT_SIMILARITY_CAP, 1.0)


def match_texts(resume_text: str, job_text: str) -> MatchOutcome:
    matched, missing, skill_score = skill_overlap(
        extract_skills(resume_text), extract_skills(job_text)
    )
    text_score = text_similarity(resume_text, job_text)

    if skill_score is None:
        score = text_score  # no skills to compare, so rely on the text alone
    else:
        score = SKILL_WEIGHT * skill_score + TEXT_WEIGHT * text_score

    return MatchOutcome(
        score=round(score, 1),
        skill_score=None if skill_score is None else round(skill_score, 1),
        text_score=round(text_score, 1),
        matched_skills=matched,
        missing_skills=missing,
    )