from app.models import ApplicationStatus as S

# For each status: the statuses you are allowed to move to next
ALLOWED_TRANSITIONS: dict[S, tuple[S, ...]] = {
    S.SAVED: (S.APPLIED,),
    S.APPLIED: (S.ONLINE_ASSESSMENT, S.INTERVIEW, S.REJECTED),
    S.ONLINE_ASSESSMENT: (S.INTERVIEW, S.REJECTED),
    S.INTERVIEW: (S.OFFER, S.REJECTED),
    S.OFFER: (),
    S.REJECTED: (),
}


def allowed_next(current: str | S) -> list[S]:
    """The statuses an application in `current` may move to."""
    return list(ALLOWED_TRANSITIONS[S(current)])


def can_transition(current: str | S, new: str | S) -> bool:
    return S(new) in ALLOWED_TRANSITIONS[S(current)]