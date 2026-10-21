from app.models import ApplicationStatus as S
from app.services.workflow import allowed_next, can_transition

VALID_MOVES = {
    (S.SAVED, S.APPLIED),
    (S.APPLIED, S.ONLINE_ASSESSMENT),
    (S.APPLIED, S.INTERVIEW),
    (S.APPLIED, S.REJECTED),
    (S.ONLINE_ASSESSMENT, S.INTERVIEW),
    (S.ONLINE_ASSESSMENT, S.REJECTED),
    (S.INTERVIEW, S.OFFER),
    (S.INTERVIEW, S.REJECTED),
}


def test_every_pair_of_statuses():
    """Check all 36 combinations against the rules, written out independently."""
    for current in S:
        for new in S:
            expected = (current, new) in VALID_MOVES
            assert can_transition(current.value, new) == expected, f"{current.value} -> {new.value}"


def test_cannot_jump_from_saved_to_offer():
    assert not can_transition("saved", S.OFFER)


def test_final_statuses_have_no_next_step():
    assert allowed_next("offer") == []
    assert allowed_next("rejected") == []


def test_allowed_next_lists_the_options_in_order():
    assert allowed_next("applied") == [S.ONLINE_ASSESSMENT, S.INTERVIEW, S.REJECTED]