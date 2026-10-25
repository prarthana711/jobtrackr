from collections import Counter
from datetime import date, datetime, timedelta, timezone

from app.models import ApplicationStatus as S

# The stages shown in the funnel, in order. "rejected" is reported separately,
# because an application can be rejected at any stage.
FUNNEL_STAGES = (S.SAVED, S.APPLIED, S.ONLINE_ASSESSMENT, S.INTERVIEW, S.OFFER)


def today_utc() -> date:
    return datetime.now(timezone.utc).date()


def percent(part: int, whole: int) -> float:
    return 0.0 if whole == 0 else round(100 * part / whole, 1)


def build_funnel(reached: dict[str, int], current: dict[str, int]) -> dict:
    """
    reached: for each status, how many applications EVER entered it (status_history)
    current: for each status, how many applications are in it RIGHT NOW
    """
    total = sum(current.values())

    stages = [
        {
            "stage": stage,
            "count": reached.get(stage.value, 0),
            "percent_of_total": percent(reached.get(stage.value, 0), total),
        }
        for stage in FUNNEL_STAGES
    ]

    sent = reached.get(S.APPLIED.value, 0)
    waiting = current.get(S.APPLIED.value, 0)  # sent, but no reply yet
    response_rate = None if sent == 0 else percent(sent - waiting, sent)

    return {
        "total": total,
        "stages": stages,
        "rejected": reached.get(S.REJECTED.value, 0),
        "response_rate": response_rate,
        "current": {status.value: current.get(status.value, 0) for status in S},
    }


def week_start(day: date) -> date:
    """The Monday of the week that contains `day`."""
    return day - timedelta(days=day.weekday())


def weekly_counts(applied_dates: list[date], weeks: int, today: date) -> list[dict]:
    """One entry per week, oldest first, including weeks with zero applications."""
    this_week = week_start(today)
    starts = [this_week - timedelta(weeks=i) for i in range(weeks - 1, -1, -1)]
    per_week = Counter(week_start(day) for day in applied_dates)
    return [
        {"week_start": start, "applications": per_week.get(start, 0)}
        for start in starts
    ]


def weak_spots(rows, limit: int) -> dict:
    """
    rows: (job_id, score, missing_skills) for every saved match, oldest first.
    Each job counts once, using its best-scoring match, so matching one job
    against five resumes doesn't count its missing skills five times.
    """
    best: dict[int, tuple[float, list[str]]] = {}
    for job_id, score, missing in rows:
        if job_id not in best or score > best[job_id][0]:
            best[job_id] = (score, missing)

    counts: Counter = Counter()
    for _, missing in best.values():
        counts.update(set(missing))

    jobs_analysed = len(best)
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]
    return {
        "jobs_analysed": jobs_analysed,
        "skills": [
            {
                "skill": skill,
                "missing_in_jobs": count,
                "percent_of_jobs": percent(count, jobs_analysed),
            }
            for skill, count in ranked
        ],
    }