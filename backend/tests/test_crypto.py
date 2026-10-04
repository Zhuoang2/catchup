import pytest

from catchup.crypto import decrypt_key, encrypt_key
from catchup.errors import AppError


def test_encrypt_decrypt_round_trip() -> None:
    value = "test-only-provider-key"
    encrypted = encrypt_key(value, "local-test-secret")
    assert value not in encrypted
    assert decrypt_key(encrypted, "local-test-secret") == value
    assert encrypt_key(value, "local-test-secret") != encrypted


def test_saving_without_secret_explains_fix() -> None:
    with pytest.raises(AppError) as error:
        encrypt_key("test-only-provider-key", None)
    assert error.value.code == "secret_not_configured"
    assert "CATCHUP_SECRET_KEY" in error.value.message
