# Credentials service
from enum import StrEnum


class EmailJob(StrEnum):
    PASSWORD_RESET = "send_mail_change_password"
    EMAIL_CHANGE = "send_mail_change_email"
    CREDENTIOALS = "send_mail_creditionals_change_notification"
    CHANGE_CREDENTIALS_NOTIFY = "send_mail_creditionals_change_notification"
    VERIFICATION = "send_mail_verification"
    SUSPICIOUS_ACTIVITY = "send_mail_suspicious_activity"


class CodeTypes(StrEnum):
    PASSWORD_RESET = "password_reset"
    VERIFICATION = "verification"
    CHANGE_EMAIL_OLD = "change_email_old"
    CHANGE_EMAIL_NEW = "change_email_new"


class UpdateFieldNames(StrEnum):
    PASSWORD_HASH = "password_hash"
    EMAIL = "email"


ALLOWED_UPDATE_FIELD_NAMES = {
    'email', 'password_hash'
}