from argon2 import PasswordHasher


ph = PasswordHasher()


def hash_password(password: str) -> str:
    return ph.hash(password)


def verify_password(stored_hash: str, password: str) -> bool:
    return ph.verify(stored_hash, password)