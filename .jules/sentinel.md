## 2024-07-24 - Cryptographically Weak PRNG for Security Codes
**Vulnerability:** The application used Python's built-in `random` module (specifically `random.randint`) to generate email verification and password reset codes.
**Learning:** `random` uses the Mersenne Twister algorithm, which is completely deterministic and predictable if enough output is observed. It is not designed for cryptographic security and should never be used to generate security tokens, codes, or passwords.
**Prevention:** Always use the `secrets` module (e.g., `secrets.randbelow` or `secrets.token_urlsafe`) for any values that require cryptographic unpredictability, such as session tokens, API keys, or verification codes.

## 2024-07-24 - Timing Attack in Login Endpoint
**Vulnerability:** The `login_user_request_service` endpoint immediately returned a "User Not Found" error if the email did not exist, without performing a password hash verification. However, if the user *did* exist, it performed a computationally expensive Argon2 hash verification.
**Learning:** This discrepancy in response times allows an attacker to enumerate which email addresses are registered in the system by timing how long the login request takes. A fast response means the email is not registered; a slow response means it is.
**Prevention:** Ensure that authentication endpoints perform a dummy hash verification (taking roughly the same amount of time as a real verification) even when the user is not found, to mask whether the user exists or not.
