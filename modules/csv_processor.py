import csv
import os
import re


CONTACT_ALIASES = {
    "full_name": ("full_name", "fullname", "name", "full name", "recipient_name", "customer_name"),
    "email": ("email", "e-mail", "recipient_email", "to_email", "to", "email_address"),
    "sender_name": ("sender_name", "profile_name", "from_name", "display_name", "gmail_name"),
    "account_email": ("account_email", "sender_email", "gmail", "gmail_email", "login_email"),
    "account_password": ("account_password", "gmail_password", "login_password", "password", "pass"),
    "two_factor": ("2fa", "two_factor", "otp", "otp_code", "verification_code"),
    "two_factor_secret": ("2fa_secret", "two_factor_secret", "totp_secret", "authenticator_secret"),
    "recovery_email": ("recovery", "recovery_email", "recovery_mail", "backup_email"),
    "send_limit": ("send_limit", "limit", "daily_limit", "account_limit", "sending_limit", "max_emails"),
}


def _clean_key(value):
    return re.sub(r"[^a-z0-9]+", "_", (value or "").strip().lower()).strip("_")


def _normalize_row(row):
    return {
        _clean_key(key): (value or "").strip()
        for key, value in row.items()
        if key is not None
    }


def _pick(row, aliases):
    for alias in aliases:
        value = row.get(_clean_key(alias), "")
        if value:
            return value.strip()
    return ""


def _contact_from_row(row):
    name = _pick(row, CONTACT_ALIASES["full_name"])
    email = _pick(row, CONTACT_ALIASES["email"])
    if not name or not email:
        return None

    contact = {
        "full_name": name,
        "email": email,
        "sender_name": _pick(row, CONTACT_ALIASES["sender_name"]),
        "account_email": _pick(row, CONTACT_ALIASES["account_email"]),
        "account_password": _pick(row, CONTACT_ALIASES["account_password"]),
        "two_factor": _pick(row, CONTACT_ALIASES["two_factor"]),
        "two_factor_secret": _pick(row, CONTACT_ALIASES["two_factor_secret"]),
        "recovery_email": _pick(row, CONTACT_ALIASES["recovery_email"]),
        "send_limit": _pick(row, CONTACT_ALIASES["send_limit"]),
        "raw": row,
    }
    return contact

def get_contacts(file_path):
    """
    Reads the CSV file and converts each row into a dictionary.
    Returns a list of dictionaries representing the contacts.
    Supports CSVs with headers (full_name,email) or no headers (first column=full_name, second=email).
    """
    contacts = []

    # Verify if the specified file path exists
    if not os.path.exists(file_path):
        print(f"[-] Error: CSV file not found at location -> {file_path}")
        return contacts

    try:
        # Open the file in read mode with UTF-8 encoding
        with open(file_path, mode='r', encoding='utf-8', newline='') as file:
            sample = file.read(2048)
            file.seek(0)
            try:
                has_header = csv.Sniffer().has_header(sample)
            except Exception:
                has_header = False

            if has_header:
                csv_reader = csv.DictReader(file)
                for row in csv_reader:
                    contact = _contact_from_row(_normalize_row(row))
                    if contact:
                        contacts.append(contact)
                    else:
                        print("[!] Warning: Row skipped due to missing contact name/email.")
            else:
                reader = csv.reader(file)
                for idx, row in enumerate(reader, start=1):
                    if not row or len(row) < 2:
                        print(f"[!] Warning: Row {idx} skipped (not enough columns): {row}")
                        continue
                    name = row[0].strip()
                    email = row[1].strip()
                    if not name or not email:
                        print(f"[!] Warning: Row {idx} skipped (empty name/email): {row}")
                        continue
                    contacts.append({"full_name": name, "email": email})

        print(f"[+] Total {len(contacts)} contacts loaded successfully.")
        return contacts

    except Exception as e:
        print(f"[-] Error reading the CSV file: {e}")
        return []

# For standalone testing when the script is executed directly
if __name__ == "__main__":
    current_dir = os.getcwd()
    
    # Adjust the file path based on the current execution directory 
    # to reliably locate the 'input_data' folder
    if "modules" not in current_dir:
        test_csv_path = os.path.join(current_dir, "input_data", "contacts.csv")
    else:
        test_csv_path = os.path.join(current_dir, "..", "input_data", "contacts.csv")
    
    print(f"[*] Checking path: {test_csv_path}")
    data = get_contacts(test_csv_path)
    
    # Output the extracted data for verification
    for i, person in enumerate(data, start=1):
        print(f"Row {i}: Name = {person['full_name']}, Email = {person['email']}")
