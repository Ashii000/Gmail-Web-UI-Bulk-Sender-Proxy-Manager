import glob
import json
import os
import random
import time

from selenium.webdriver.common.by import By


from modules import account_loader, browser_setup, csv_processor, file_handler, gmail_actions

def _as_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes", "y", "on")


def _as_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def _resolve_path(path):
    if not path:
        return ""
    return os.path.abspath(os.path.expandvars(os.path.expanduser(path)))


def _load_templates(config, current_dir):
    email_settings = config.get("email_settings", {})
    subject_template = email_settings.get("subject_template", "")
    body_template = email_settings.get("body_template", "")

    subject_file = os.path.join(current_dir, "subject.txt")
    message_file = os.path.join(current_dir, "message.txt")

    if os.path.exists(subject_file):
        with open(subject_file, "r", encoding="utf-8") as file:
            subject_template = file.read().strip()

    if os.path.exists(message_file):
        with open(message_file, "r", encoding="utf-8") as file:
            body_template = file.read().strip()

    return subject_template, body_template


def _list_optional_files(folder_path, label):
    folder_path = _resolve_path(folder_path)
    if not folder_path or not os.path.isdir(folder_path):
        print(f"[*] No {label} folder found at {folder_path or '(not configured)'}; {label} attachment will be skipped.")
        return []

    files = [
        os.path.abspath(path)
        for path in glob.glob(os.path.join(folder_path, "*"))
        if os.path.isfile(path)
    ]
    if not files:
        print(f"[*] No {label} files found at {folder_path}; {label} attachment will be skipped.")
    else:
        print(f"[*] Found {len(files)} {label} file(s).")
    return files


def _attachment_paths(config):
    folders = config.get("attachment_folders", {})
    w9_files = _list_optional_files(folders.get("w9_folder_path", ""), "W9")
    invoice_files = _list_optional_files(folders.get("invoice_folder_path", ""), "invoice")

    selected = []
    if w9_files:
        selected.append(("W9", w9_files[0]))
    if invoice_files:
        selected.append(("Invoice", invoice_files[0]))
    return selected


def _discard_visible_composes(driver):
    dialogs = driver.find_elements(By.XPATH, "//div[@role='dialog']")
    for _ in range(len(dialogs)):
        try:
            discard_xpath = (
                "(//div[@role='dialog'])[last()]//*[@aria-label='Discard draft' or "
                "@data-tooltip='Discard draft' or contains(@aria-label,'Discard')]"
            )
            gmail_actions.wait_and_click(driver, discard_xpath, timeout=3)
            time.sleep(0.5)
        except Exception as exc:
            print(f"    [!] Could not discard an existing compose dialog: {exc}")
            break


def _contact_belongs_to_account(contact, account):
    assigned_email = (contact.get("account_email") or "").strip().lower()
    account_email = (account.get("email") or "").strip().lower()
    if assigned_email:
        return assigned_email == account_email
    return True


def _next_account_batch(remaining_contacts, account, limit):
    batch = []
    for contact in remaining_contacts:
        if len(batch) >= limit:
            break
        if _contact_belongs_to_account(contact, account):
            batch.append(contact)
    return batch


def _delay_between_emails(wait_time):
    if wait_time and wait_time > 0:
        jitter = random.uniform(0.4 * wait_time, 0.8 * wait_time)
        time.sleep(max(0.5, min(jitter, 5.0)))
    else:
        time.sleep(0.5)


def _send_one_email(driver, person, account, config, templates, row_number):
    email_settings = config.get("email_settings", {})
    features = config.get("features", {})
    print(f"\n[DEBUG] CSV Row Data: {person}")
    
    # === THE FINAL FIX ===
    raw_data = person.get("raw", {})
    cc_email = (raw_data.get("cc_email") or raw_data.get("cc") or person.get("cc_email") or email_settings.get("cc_email") or "").strip()
    # =====================
    
    subject_template, body_template = templates
    wait_time = _as_int(config.get("bot_delays", {}).get("wait_between_emails_seconds", 0), 0)
    update_sender_name = _as_bool(features.get("update_sender_name", True), True)

    full_name = person["full_name"]
    to_email = person["email"]
    sender_name = (
        (person.get("sender_name") or "").strip()
        or (account.get("sender_name") or "").strip()
        or full_name
    )

    print(f"\n--- Processing Row {row_number}: {full_name} ---")
    _discard_visible_composes(driver)

    if update_sender_name and sender_name:
        try:
            print(f"    -> Step 0: Updating sender profile name to {sender_name}...")
            ok = gmail_actions.update_profile_name(driver, sender_name, account_email=account.get("email", ""))
            if ok:
                print("    -> Profile name updated successfully.")
            else:
                print("    -> Profile name update failed; continuing.")
        except Exception as exc:
            print(f"    [!] update_profile_name exception: {exc}")
    else:
        print("[*] Step 0 (profile update) is disabled by configuration.")

    gmail_actions.draft_email(driver, full_name, to_email, cc_email, subject_template, body_template)
    attachments = _attachment_paths(config)
    if not attachments:
        print("    -> No attachments present. Sending without attachments...")
        time.sleep(1)
    else:
        attach_icon_xpath = '//div[@command="Files" or @aria-label="Attach files"]'
        for label, file_path in attachments:
            print(f"    -> Step 3: Attaching {label} ({file_path})...")
            attached = gmail_actions.attach_files_via_input(driver, [file_path])
            if not attached:
                gmail_actions.wait_and_click(driver, attach_icon_xpath)
                attached = file_handler.attach_local_file(file_path)
            if not attached:
                print(f"    [!] {label} attachment failed; continuing with remaining send flow.")

        print("    -> Waiting for attachments to finish uploading...")
        uploads_ok = gmail_actions.wait_for_attachments(driver, timeout=60)
        if not uploads_ok:
            print("    [!] Attachments may still be uploading. Waiting extra 15s...")
            time.sleep(15)

    print("    -> Step 4: Clicking Send button...")
    sent_ok = gmail_actions.send_current_draft(driver)
    if sent_ok:
        print(f"[+] SUCCESS: Email sent to {to_email}")
    else:
        print(f"[-] ERROR: Email was not confirmed sent to {to_email}. It may still be open as a draft.")

    _delay_between_emails(wait_time)
    return sent_ok


def main():
    print("==================================================")
    print("GMAIL WEB UI AUTOMATION BOT - STARTED")
    print("==================================================")

    current_dir = os.getcwd()
    config_path = os.path.join(current_dir, "config.json")
    if not os.path.exists(config_path):
        print("[-] Error: config.json file not found!")
        return

    with open(config_path, "r", encoding="utf-8") as file:
        config = json.load(file)

    subject_template, body_template = _load_templates(config, current_dir)
    if not subject_template:
        print("[-] ERROR: Subject template is empty! Check subject.txt or config.json")
        return
    if not body_template:
        print("[-] ERROR: Message body template is empty! Check message.txt or config.json")
        return
    print("[+] Templates loaded successfully")

    csv_path = os.path.join(current_dir, "input_data", "contacts.csv")
    contacts = csv_processor.get_contacts(csv_path)
    if not contacts:
        return

    accounts = account_loader.load_accounts(config, contacts, current_dir)
    account_settings = config.get("account_settings", {})
    page_load_time = _as_int(config.get("bot_delays", {}).get("page_load_wait_seconds", 30), 30)
    manual_login_wait = _as_int(account_settings.get("manual_login_wait_seconds", 90), 90)
    force_fresh_login = _as_bool(account_settings.get("force_fresh_login", False), False)

    remaining_contacts = contacts[:]
    total_sent = 0
    total_attempted = 0

    try:
        for account_index, account in enumerate(accounts, start=1):
            if not remaining_contacts:
                break

            configured_limit = _as_int(account.get("send_limit", 0), 0)
            limit = configured_limit if configured_limit > 0 else len(remaining_contacts)
            batch = _next_account_batch(remaining_contacts, account, limit)
            if not batch:
                continue

            label = account_loader.redacted_account_label(account)
            print(f"\n=== Account {account_index}: {label} | limit {limit} | queued {len(batch)} ===")
            driver = browser_setup.setup_browser(
                profile_path=account.get("profile_dir"),
                fresh_profile=force_fresh_login,
            )
            if not driver:
                print("[-] Could not start browser for this account; moving to next account.")
                continue

            try:
                login_ok = gmail_actions.ensure_gmail_login(
                    driver,
                    account,
                    page_load_time=page_load_time,
                    manual_wait=manual_login_wait,
                )
                if not login_ok:
                    print("[-] Gmail login did not complete for this account; moving to next account.")
                    continue

                sent_for_account = 0
                for person in batch:
                    if configured_limit > 0 and sent_for_account >= configured_limit:
                        print("[*] Account sending limit reached. Switching account.")
                        break

                    row_number = contacts.index(person) + 1
                    total_attempted += 1
                    try:
                        sent = _send_one_email(driver, person, account, config, (subject_template, body_template), row_number)
                        if sent:
                            sent_for_account += 1
                            total_sent += 1
                    except Exception as row_error:
                        print(f"\n[-] ERROR on Row {row_number}: {row_error}")
                        print(f"[!] Exception Type: {type(row_error).__name__}")
                        time.sleep(5)
                    finally:
                        if person in remaining_contacts:
                            remaining_contacts.remove(person)

                print(f"[*] Account finished. Confirmed sent: {sent_for_account}/{len(batch)}")
            finally:
                print("[*] Closing browser for this account...")
                try:
                    driver.quit()
                    print("[+] Browser closed successfully")
                except Exception as quit_err:
                    print(f"[!] Error closing browser: {quit_err}")

    except Exception as exc:
        print(f"[-] Critical Error: {exc}")
    finally:
        print("\n==================================================")
        print(f"TASKS STOPPED. Attempted: {total_attempted}, confirmed sent: {total_sent}, remaining: {len(remaining_contacts)}")
        print("==================================================")


if __name__ == "__main__":
    main()
