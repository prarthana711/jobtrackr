import pytest

from app.services.matcher import (
    SKILL_WEIGHT,
    TEXT_WEIGHT,
    match_texts,
    skill_overlap,
    text_similarity,
)

RESUME = "Python developer with SQL, Docker and FastAPI. Built REST APIs on AWS with PostgreSQL."
JOB = "Backend Engineer. Needs Python, SQL, Docker, Kubernetes and Redis. REST APIs a plus."


def test_skill_overlap_finds_matched_and_missing():
    matched, missing, score = skill_overlap(
        ["python", "sql", "aws"], ["python", "sql", "docker", "redis"]
    )
    assert matched == ["python", "sql"]
    assert missing == ["docker", "redis"]
    assert score == 50.0


def test_skill_overlap_is_a_percentage_of_the_jobs_skills():
    _, _, score = skill_overlap(["python"], ["python", "sql", "docker", "redis"])
    assert score == 25.0


def test_skill_overlap_without_job_skills_has_no_score():
    assert skill_overlap(["python"], []) == ([], [], None)


def test_skill_overlap_with_empty_resume_scores_zero():
    matched, missing, score = skill_overlap([], ["python", "sql"])
    assert matched == []
    assert missing == ["python", "sql"]
    assert score == 0.0


def test_extra_resume_skills_do_not_raise_the_score():
    job = ["python", "sql"]
    focused = skill_overlap(["python", "sql"], job)[2]
    broad = skill_overlap(["python", "sql", "aws", "docker", "react"], job)[2]
    assert focused == broad == 100.0


def test_identical_texts_are_a_perfect_text_match():
    assert text_similarity(RESUME, RESUME) == pytest.approx(100.0)


def test_unrelated_texts_have_no_text_match():
    assert text_similarity(RESUME, "Baking sourdough bread needs flour, water and patience.") == 0.0


def test_related_texts_score_in_between():
    assert 0 < text_similarity(RESUME, JOB) < 100


def test_text_similarity_is_symmetric():
    assert text_similarity(RESUME, JOB) == pytest.approx(text_similarity(JOB, RESUME))


def test_text_made_only_of_stop_words_scores_zero():
    assert text_similarity(RESUME, "the and of") == 0.0
    assert text_similarity("the and of", "to be or not") == 0.0


def test_match_texts_combines_skill_and_text_scores():
    outcome = match_texts(RESUME, JOB)
    assert outcome.matched_skills == ["docker", "python", "rest api", "sql"]
    assert outcome.missing_skills == ["kubernetes", "redis"]
    assert outcome.skill_score == pytest.approx(66.7, abs=0.1)
    assert 0 < outcome.text_score < 100
    expected = SKILL_WEIGHT * outcome.skill_score + TEXT_WEIGHT * outcome.text_score
    assert outcome.score == pytest.approx(expected, abs=0.2)


def test_without_job_skills_the_text_score_is_the_score():
    outcome = match_texts(RESUME, "Warehouse associate. Lift boxes and load trucks safely.")
    assert outcome.skill_score is None
    assert outcome.score == outcome.text_score
    assert outcome.missing_skills == []


def test_scores_stay_between_0_and_100():
    for job in (JOB, RESUME, "Marketing executive for social media campaigns"):
        outcome = match_texts(RESUME, job)
        assert 0 <= outcome.score <= 100


def test_weights_add_up_to_one():
    assert SKILL_WEIGHT + TEXT_WEIGHT == pytest.approx(1.0)


def test_better_resume_scores_higher():
    strong = match_texts(RESUME, JOB).score
    weak = match_texts("Hobbies: cooking, painting and gardening every weekend.", JOB).score
    assert strong > weak