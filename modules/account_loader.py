import csv
import io
import os
import re
import urllib.parse
import urllib.request


SENSITIVE_KEYWORDS = ("password", "pass", "2fa", "totp", "otp", "secret", "recovery")


ACCOUNT_ALIASES = {
    "email": (
        "email",
        "gmail",
        "gmail_email",
        "account_email",
        "sender_email",
        "login_email",
        "username",
    ),
    "password": (
        "password",
        "pass",
        "gmail_password",
        "account_password",
        "login_password",
    ),
    "two_factor": (
        "2fa",
        "two_factor",
        "two_factor_code",
        "otp",
        "otp_code",
        "verification_code",
        "auth_code",
    ),
    "two_factor_secret": (
        "2fa_secret",
        "two_factor_secret",
        "totp_secret",
        "authenticator_secret",
    ),
    "recovery_email": (
        "recovery",
        "recovery_email",
        "recovery_mail",
        "recoveryemail",
        "backup_email",
    ),
    "send_limit": (
        "send_limit",
        "limit",
        "daily_limit",
        "account_limit",
        "sending_limit",
        "max_emails",
    ),
    "sender_name": (
        "sender_name",
        "profile_name",
        "from_name",
        "display_name",
        "gmail_name",
    ),
    "profile_dir": (
        "profile_dir",
        "chrome_profile",
        "browser_profile",
    ),
}


def _clean_key(value):
    return re.sub(r"[^a-z0-9]+", "_", (value or "").strip().lower()).strip("_")


def _normalize_row(row):
    normalized = {}
    for key, value in row.items():
        if key is None:
            continue
        normalized[_clean_key(key)] = (value or "").strip()
    return normalized


def _pick(row, aliases, default=""):
    for alias in aliases:
        value = row.get(_clean_key(alias), "")
        if value:
            return value.strip()
    return default


def _parse_int(value, default=0):
    try:
        return max(0, int(str(value).strip()))
    except Exception:
        return default


def _safe_profile_name(email):
    safe = re.sub(r"[^a-zA-Z0-9_.-]+", "_", email or "default").strip("._")
    return safe or "default"


def _sheet_url_to_csv_url(url):
    if not url:
        return ""
    url = url.strip()
    if "docs.google.com/spreadsheets" not in url:
        return url

    match = re.search(r"/spreadsheets/d/([^/]+)", url)
    if not match:
        return url

    sheet_id = match.group(1)
    parsed = urllib.parse.urlparse(url)
    query = urllib.parse.parse_qs(parsed.query)
    gid = ""
    if "gid" in query and query["gid"]:
        gid = query["gid"][0]
    if not gid and parsed.fragment:
        fragment_qs = urllib.parse.parse_qs(parsed.fragment)
        if "gid" in fragment_qs and fragment_qs["gid"]:
            gid = fragment_qs["gid"][0]

    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    if gid:
        csv_url += f"&gid={urllib.parse.quote(gid)}"
    return csv_url


def _read_csv_text_from_url(url):
    csv_url = _sheet_url_to_csv_url(url)
    with urllib.request.urlopen(csv_url, timeout=30) as response:
        raw = response.read()
    return raw.decode("utf-8-sig")


def _read_csv_rows_from_text(text):
    reader = csv.DictReader(io.StringIO(text))
    return [_normalize_row(row) for row in reader]


def _read_csv_rows_from_file(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as file:
        return [_normalize_row(row) for row in csv.DictReader(file)]


def _normalize_account(row, config_defaults, current_dir, source):
    account = {
        "email": _pick(row, ACCOUNT_ALIASES["email"]),
        "password": _pick(row, ACCOUNT_ALIASES["password"]),
        "two_factor": _pick(row, ACCOUNT_ALIASES["two_factor"]),
        "two_factor_secret": _pick(row, ACCOUNT_ALIASES["two_factor_secret"]),
        "recovery_email": _pick(row, ACCOUNT_ALIASES["recovery_email"]),
        "send_limit": _parse_int(
            _pick(row, ACCOUNT_ALIASES["send_limit"]),
            config_defaults.get("default_send_limit", 0),
        ),
        "sender_name": _pick(row, ACCOUNT_ALIASES["sender_name"]),
        "profile_dir": _pick(row, ACCOUNT_ALIASES["profile_dir"]),
        "source": source,
    }

    if not account["profile_dir"]:
        profile_root = config_defaults.get("profile_root", "chrome_profiles")
        if account["email"]:
            account["profile_dir"] = os.path.join(profile_root, _safe_profile_name(account["email"]))
        else:
            account["profile_dir"] = "chrome_profile"

    if not os.path.isabs(account["profile_dir"]):
        account["profile_dir"] = os.path.join(current_dir, account["profile_dir"])

    return account


def _dedupe_accounts(accounts):
    seen = set()
    unique = []
    for account in accounts:
        key = (account.get("email") or account.get("profile_dir") or "").lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(account)
    return unique


def _accounts_from_contacts(contacts, config_defaults, current_dir):
    rows = []
    for contact in contacts:
        account_email = (contact.get("account_email") or "").strip()
        account_password = (contact.get("account_password") or "").strip()
        if not account_email and not account_password:
            continue
        rows.append(
            {
                "account_email": account_email,
                "account_password": account_password,
                "2fa": contact.get("two_factor", ""),
                "2fa_secret": contact.get("two_factor_secret", ""),
                "recovery_email": contact.get("recovery_email", ""),
                "send_limit": contact.get("send_limit", ""),
                "sender_name": contact.get("account_sender_name", ""),
            }
        )
    return [
        _normalize_account(row, config_defaults, current_dir, "contacts_csv")
        for row in rows
    ]


def load_accounts(config, contacts, current_dir):
    settings = config.get("account_settings") or config.get("accounts") or {}
    if isinstance(settings, list):
        settings = {"accounts": settings}

    defaults = {
        "default_send_limit": _parse_int(settings.get("default_send_limit", 0), 0),
        "profile_root": settings.get("profile_root", "chrome_profiles"),
    }

    accounts = []
    inline_accounts = settings.get("accounts", [])
    if isinstance(inline_accounts, list):
        for row in inline_accounts:
            if isinstance(row, dict):
                accounts.append(
                    _normalize_account(
                        _normalize_row(row),
                        defaults,
                        current_dir,
                        "config",
                    )
                )

    sheet_url = (
        settings.get("google_sheet_csv_url")
        or settings.get("google_sheet_url")
        or settings.get("sheet_csv_url")
        or ""
    ).strip()
    if sheet_url:
        try:
            rows = _read_csv_rows_from_text(_read_csv_text_from_url(sheet_url))
            accounts.extend(
                _normalize_account(row, defaults, current_dir, "google_sheet")
                for row in rows
            )
            print(f"[+] Loaded {len(rows)} account row(s) from Google Sheet CSV.")
        except Exception as exc:
            print(f"[!] Could not load accounts from Google Sheet CSV: {exc}")

    csv_path = settings.get("accounts_csv_path", os.path.join("input_data", "accounts.csv"))
    if csv_path and not os.path.isabs(csv_path):
        csv_path = os.path.join(current_dir, csv_path)
    if csv_path and os.path.exists(csv_path):
        try:
            rows = _read_csv_rows_from_file(csv_path)
            accounts.extend(
                _normalize_account(row, defaults, current_dir, "accounts_csv")
                for row in rows
            )
            print(f"[+] Loaded {len(rows)} account row(s) from {csv_path}.")
        except Exception as exc:
            print(f"[!] Could not load accounts CSV: {exc}")

    accounts.extend(_accounts_from_contacts(contacts, defaults, current_dir))
    accounts = _dedupe_accounts([account for account in accounts if account.get("email") or account.get("profile_dir")])

    if not accounts:
        accounts = [
            {
                "email": "",
                "password": "",
                "two_factor": "",
                "two_factor_secret": "",
                "recovery_email": "",
                "send_limit": defaults["default_send_limit"],
                "sender_name": "",
                "profile_dir": os.path.join(current_dir, "chrome_profile"),
                "source": "existing_profile",
            }
        ]
        print("[*] No account sheet/CSV configured. Using the existing Chrome profile.")
    else:
        print(f"[+] Total {len(accounts)} sending account(s) available.")

    return accounts


def redacted_account_label(account):
    email = account.get("email", "")
    if not email:
        return "existing Chrome profile"
    name, _, domain = email.partition("@")
    if not domain:
        return "***"
    return f"{name[:2]}***@{domain}"
