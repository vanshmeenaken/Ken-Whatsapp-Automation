"""
Validation utilities
"""
import re

PHONE_REGEX = re.compile(r"^\+?[1-9]\d{7,14}$")
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

def is_valid_phone(phone: str) -> bool:
    """Check if phone number is valid E.164 format."""
    return bool(PHONE_REGEX.match(str(phone).strip() if phone else ""))

def is_valid_email(email: str) -> bool:
    """Check if email is valid."""
    return bool(EMAIL_REGEX.match(str(email).strip() if email else ""))
