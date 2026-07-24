## 2024-05-18 - Jinja2 Email Template HTML Injection / XSS
**Vulnerability:** The Jinja2 environment in `src/auth/utils/email_utils.py` was initialized without `autoescape=True`. User-controlled inputs, such as the `User-Agent` header passed to `suspicious_activity.html`, were rendered directly into the email body without HTML escaping, creating a Cross-Site Scripting (XSS) / HTML Injection vulnerability in transactional emails.
**Learning:** Default Jinja2 environments do not automatically escape HTML unless specifically configured. In email systems, where user inputs like `User-Agent` or `IP-Address` are logged or sent to users, failure to escape can lead to phishing attacks or execution of malicious scripts within the email client.
**Prevention:** Always initialize Jinja2 environments with `autoescape=select_autoescape(['html', 'xml'])` when generating HTML emails to ensure all variables are automatically escaped.

## 2024-05-18 - Email Change Logic / Ownership Verification Gap
**Vulnerability:** The email change flow (at `/auth/email/change`) only verified ownership of the existing email account. It did not require verification of the new email address being set. This allowed the possibility of typos locking users out or session hijackers assigning an email they couldn't verify.
**Learning:** Any operation that transfers or changes core identity credentials (like email addresses or phone numbers) must require mutual verification. The old credential must authorize the transfer, and the new credential must verify ownership.
**Prevention:** Implement a "two-code" verification flow. When an email change is requested, generate two separate codes and send one to the old email and one to the new email. Only change the email in the database if both codes are confirmed.
