import uuid

import jwt

from app.core.security import (
    JWT_ALGORITHM,
    create_access_token,
    decode_access_token,
    hash_pin,
    verify_pin,
)
from tests.conftest import make_settings


def test_pin_hash_roundtrip_and_no_plaintext():
    h = hash_pin("1234")
    assert "1234" not in h
    assert verify_pin("1234", h)
    assert not verify_pin("4321", h)


def test_verify_pin_with_unknown_account_is_always_false():
    assert not verify_pin("000000", None)
    assert not verify_pin("1234", None)


def test_token_roundtrip():
    s = make_settings()
    uid = uuid.uuid4()
    assert decode_access_token(s, create_access_token(s, uid, "student")) == uid


def test_token_with_wrong_secret_expired_or_garbage_is_rejected():
    s = make_settings()
    other = make_settings(jwt_secret="another-secret-that-is-long-enough-32b")
    uid = uuid.uuid4()
    assert decode_access_token(s, create_access_token(other, uid, "student")) is None
    expired = jwt.encode(
        {"sub": str(uid), "exp": 1}, s.jwt_secret.get_secret_value(), algorithm=JWT_ALGORITHM
    )
    assert decode_access_token(s, expired) is None
    assert decode_access_token(s, "not-a-token") is None


def test_token_without_expiry_is_rejected():
    s = make_settings()
    token = jwt.encode(
        {"sub": str(uuid.uuid4())}, s.jwt_secret.get_secret_value(), algorithm=JWT_ALGORITHM
    )
    assert decode_access_token(s, token) is None
