from datetime import date

from app.services.analytics import build_funnel, weak_spots, week_start, weekly_counts

STAGE_ORDER = ["saved", "applied", "online_assessment", "interview", "offer"]


def test_week_start_is_the_monday_of_that_week():
    assert week_start(date(2025, 1, 15)) == date(2025, 1, 13)  # a Wednesday
    assert week_start(date(2025, 1, 13)) == date(2025, 1, 13)  # a Monday
    assert week_start(date(2025, 1, 19)) == date(2025, 1, 13)  # a Sunday
    assert week_start(date(2025, 1, 20)) == date(2025, 1, 20)  # next Monday


def test_weekly_counts_fills_empty_weeks_oldest_first():
    dates = [date(2025, 1, 14), date(2025, 1, 13), date(2024, 12, 31)]
    result = weekly_counts(dates, weeks=4, today=date(2025, 1, 15))
    assert result == [
        {"week_start": date(2024, 12, 23), "applications": 0},
        {"week_start": date(2024, 12, 30), "applications": 1},
        {"week_start": date(2025, 1, 6), "applications": 0},
        {"week_start": date(2025, 1, 13), "applications": 2},
    ]


def test_weekly_counts_ignores_dates_outside_the_window():
    dates = [date(2024, 11, 1), date(2025, 1, 27)]  # far past, and a future week
    result = weekly_counts(dates, weeks=2, today=date(2025, 1, 15))
    assert [week["applications"] for week in result] == [0, 0]


def test_weekly_counts_returns_the_requested_number_of_weeks():
    result = weekly_counts([], weeks=12, today=date(2025, 1, 15))
    assert len(result) == 12
    assert result[-1]["week_start"] == date(2025, 1, 13)
    assert result[0]["week_start"] < result[-1]["week_start"]


def test_funnel_counts_percentages_and_response_rate():
    reached = {
        "saved": 10, "applied": 8, "online_assessment": 3,
        "interview": 3, "offer": 1, "rejected": 2,
    }
    current = {
        "saved": 2, "applied": 3, "online_assessment": 1,
        "interview": 1, "offer": 1, "rejected": 2,
    }
    funnel = build_funnel(reached, current)

    assert funnel["total"] == 10
    assert [s["stage"].value for s in funnel["stages"]] == STAGE_ORDER
    assert [s["count"] for s in funnel["stages"]] == [10, 8, 3, 3, 1]
    assert [s["percent_of_total"] for s in funnel["stages"]] == [100.0, 80.0, 30.0, 30.0, 10.0]
    assert funnel["rejected"] == 2
    assert funnel["response_rate"] == 62.5  # 5 of the 8 sent applications got a reply
    assert funnel["current"]["applied"] == 3
    assert sum(funnel["current"].values()) == 10


def test_funnel_with_no_data_is_all_zeros():
    funnel = build_funnel({}, {})
    assert funnel["total"] == 0
    assert [s["count"] for s in funnel["stages"]] == [0, 0, 0, 0, 0]
    assert [s["percent_of_total"] for s in funnel["stages"]] == [0.0] * 5
    assert funnel["rejected"] == 0
    assert funnel["response_rate"] is None
    assert set(funnel["current"].values()) == {0}
    assert len(funnel["current"]) == 6


def test_response_rate_needs_at_least_one_sent_application():
    assert build_funnel({"saved": 2}, {"saved": 2})["response_rate"] is None


def test_response_rate_is_zero_when_nobody_has_replied():
    funnel = build_funnel({"saved": 2, "applied": 2}, {"applied": 2})
    assert funnel["response_rate"] == 0.0


def test_a_rejection_counts_as_a_response():
    funnel = build_funnel(
        {"saved": 1, "applied": 1, "rejected": 1}, {"rejected": 1}
    )
    assert funnel["response_rate"] == 100.0


def test_weak_spots_counts_each_job_once_using_its_best_match():
    rows = [
        (1, 80.0, ["docker", "redis"]),
        (1, 40.0, ["docker", "redis", "aws"]),  # a worse resume for the same job
        (2, 50.0, ["docker"]),
        (3, 10.0, []),
    ]
    result = weak_spots(rows, limit=10)
    assert result["jobs_analysed"] == 3
    assert result["skills"] == [
        {"skill": "docker", "missing_in_jobs": 2, "percent_of_jobs": 66.7},
        {"skill": "redis", "missing_in_jobs": 1, "percent_of_jobs": 33.3},
    ]


def test_weak_spots_ties_are_sorted_by_name_and_limited():
    rows = [(1, 50.0, ["b", "a", "c"]), (2, 50.0, ["c"])]
    result = weak_spots(rows, limit=2)
    assert [s["skill"] for s in result["skills"]] == ["c", "a"]


def test_weak_spots_with_equal_scores_keeps_the_first_match():
    rows = [(1, 50.0, ["a"]), (1, 50.0, ["b"])]
    result = weak_spots(rows, limit=10)
    assert [s["skill"] for s in result["skills"]] == ["a"]


def test_weak_spots_with_no_matches():
    assert weak_spots([], limit=10) == {"jobs_analysed": 0, "skills": []}