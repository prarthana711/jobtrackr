from app.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_is_not_plaintext_and_verifies():
    hashed = hash_password("secret123")
    assert hashed != "secret123"
    assert verify_password("secret123", hashed)
    assert not verify_password("wrong", hashed)


def test_same_password_gives_different_hashes():
    assert hash_password("secret123") != hash_password("secret123")


def test_token_roundtrip_and_tampering():
    token = create_access_token(42)
    assert decode_access_token(token) == 42
    assert decode_access_token(token + "x") is None
    assert decode_access_token("not-a-token") is None