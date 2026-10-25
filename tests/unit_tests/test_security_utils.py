from src.auth.utils.security_utils import hash_password, verify_password


def test_hash_password_returns_different_strings():
    password = "123123231"
    hashed = hash_password(password)

    assert hashed != password
    assert hashed.startswith("$argon2")


def test_verify_password_returns_true_for_correct_password():
    password = "123123231"
    hashed = hash_password(password)

    assert verify_password(hashed, password) is True


def test_verify_password_returns_false_for_incorrect_password():
    password = "123123231"
    hashed = hash_password(password)

    assert verify_password(hashed, "123123") is False