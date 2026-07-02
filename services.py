import datetime
import hashlib
import os

ANNUAL_RATE = 0.10
QUARTERLY_SAVING = 6000


def calc_interest(principal, issue_date, as_of=None, waive_interest=False, interest_rate=None):
    if as_of is None:
        as_of = datetime.date.today()
    if isinstance(issue_date, str):
        issue_date = datetime.date.fromisoformat(issue_date)
    days = max((as_of - issue_date).days, 0)
    
    if waive_interest:
        return 0, days  # No interest if waived
    
    # Use provided interest_rate, fallback to ANNUAL_RATE if not specified
    # Convert percentage to decimal (e.g., 10.0 -> 0.10)
    if interest_rate is not None:
        rate = interest_rate / 100  # Convert percentage to decimal
    else:
        rate = ANNUAL_RATE  # ANNUAL_RATE is already a decimal (0.10)
    return round(principal * rate * days / 365, 2), days


def parse_iso_date(value, field_name="Date"):
    value = (value or "").strip()
    if not value:
        raise ValueError(f"{field_name} is required")
    try:
        return datetime.date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be YYYY-MM-DD") from exc


def parse_positive_amount(value, field_name="Amount"):
    try:
        amount = float(str(value).replace(",", "").strip())
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a valid number") from exc
    if amount <= 0:
        raise ValueError(f"{field_name} must be greater than zero")
    return amount


def hash_pw_legacy(pw):
    return hashlib.sha256(pw.encode()).hexdigest()


def hash_pw_pbkdf2(pw, salt=None):
    if salt is None:
        salt = os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), 150000).hex()
    return digest, salt


def verify_password(password, stored_hash, stored_salt=None):
    if stored_salt:
        check, _ = hash_pw_pbkdf2(password, stored_salt)
        return check == stored_hash
    return hash_pw_legacy(password) == stored_hash


def quarter_code_for_date(dt):
    return f"{dt.year}-Q{(dt.month - 1) // 3 + 1}"
