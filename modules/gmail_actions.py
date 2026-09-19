from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoAlertPresentException, UnexpectedAlertPresentException
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
import time
import os
import base64
import hashlib
import hmac
import re
import struct

# --- UPDATED HELPER FUNCTIONS ---
def wait_and_click(driver, xpath, timeout=15):
    """Wait until the specified element is clickable and then click it."""
    element = WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((By.XPATH, xpath))
    )
    time.sleep(0.2)
    try:
        element.click()
    except:
        driver.execute_script("arguments[0].click();", element)
    return element

def js_send_keys(driver, xpath, text, timeout=15, human_type=False, char_delay=0.0):
    """Set text quickly using JS for speed; falls back to send_keys if needed.
    human_type: if True, simulate typing with small delays (char_delay seconds per char).
    """
    element = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.XPATH, xpath))
    )
    # Focus element
    try:
        driver.execute_script("arguments[0].focus();", element)
    except:
        pass

    # Try fast JS set for inputs/textarea or contenteditable
    try:
        tag = element.tag_name.lower()
        is_contenteditable = (element.get_attribute("contenteditable") or "").lower()
        if tag in ("input", "textarea"):
            driver.execute_script("arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input'));", element, text)
        elif is_contenteditable == "true":
            driver.execute_script("arguments[0].innerText = arguments[1]; arguments[0].dispatchEvent(new Event('input'));", element, text)
        else:
            driver.execute_script("arguments[0].innerText = arguments[1]; arguments[0].dispatchEvent(new Event('input'));", element, text)
        # Quick verification (best-effort)
        try:
            if tag in ("input", "textarea"):
                WebDriverWait(driver, 2).until(lambda d: (element.get_attribute("value") or "").startswith(text[:10]))
            else:
                WebDriverWait(driver, 2).until(lambda d: text[:10] in (element.get_attribute("innerText") or element.text or ""))
        except:
            pass
        return element
    except Exception:
        # Fallback to send_keys (optionally human-like)
        try:
            element.clear()
        except:
            try:
                driver.execute_script("arguments[0].innerText = '';", element)
            except:
                pass
        if human_type and char_delay > 0:
            for ch in text:
                element.send_keys(ch)
                time.sleep(char_delay)
        else:
            element.send_keys(text)
        return element


def type_text(element, text, clear=True):
    """Type through Selenium key events so Gmail registers the field changes."""
    element.click()
    time.sleep(0.15)
    if clear:
        try:
            element.send_keys(Keys.CONTROL, "a")
            element.send_keys(Keys.BACKSPACE)
        except Exception:
            try:
                element.clear()
            except Exception:
                pass
    if text:
        element.send_keys(text)
    return element


def type_and_submit(driver, xpath, text, timeout=15, submit=True):
    element = WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((By.XPATH, xpath))
    )
    type_text(element, text)
    if submit:
        element.send_keys(Keys.ENTER)
    return element


def click_google_next(driver, timeout=12):
    next_xpath = (
        "//button[.//span[normalize-space()='Next'] or normalize-space()='Next'] | "
        "//*[@role='button' and (.//span[normalize-space()='Next'] or normalize-space()='Next')]"
    )
    return wait_and_click(driver, next_xpath, timeout=timeout)


def gmail_is_ready(driver):
    try:
        url = (driver.current_url or "").lower()
        title = (driver.title or "").lower()
        if "mail.google.com" in url and ("inbox" in title or "/mail/" in url):
            compose_or_nav = driver.find_elements(
                By.XPATH,
                "//*[@aria-label='Compose' or text()='Compose' or @gh='cm' or contains(@aria-label,'Main menu')]",
            )
            if compose_or_nav:
                return True
        return False
    except Exception:
        return False


def wait_for_gmail_ready(driver, timeout=30):
    try:
        WebDriverWait(driver, timeout).until(lambda d: gmail_is_ready(d))
        return True
    except Exception:
        return False


def _body_text(driver):
    try:
        return driver.find_element(By.TAG_NAME, "body").text.lower()
    except Exception:
        return ""


def _current_totp(secret, digits=6, period=30):
    cleaned = re.sub(r"\s+", "", secret or "").upper()
    cleaned += "=" * ((8 - len(cleaned) % 8) % 8)
    key = base64.b32decode(cleaned, casefold=True)
    counter = int(time.time() // period)
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(code % (10**digits)).zfill(digits)


def _account_code(account):
    fixed_code = (account.get("two_factor") or "").strip().replace(" ", "")
    if fixed_code.isdigit() and 4 <= len(fixed_code) <= 10:
        return fixed_code

    secret = (account.get("two_factor_secret") or "").strip()
    if not secret and fixed_code and not fixed_code.isdigit():
        secret = fixed_code
    if secret:
        try:
            return _current_totp(secret)
        except Exception as exc:
            print(f"[!] Could not generate TOTP code: {exc}")
    return ""


def _click_recovery_email_option(driver):
    option_xpath = (
        "//*[(@role='link' or @role='button' or @role='listitem') and "
        "contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'recovery email')] | "
        "//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'confirm your recovery email')]"
    )
    try:
        wait_and_click(driver, option_xpath, timeout=5)
        return True
    except Exception:
        return False


def _submit_recovery_email(driver, recovery_email):
    if not recovery_email:
        return False
    input_xpath = (
        "//input[@type='email'] | "
        "//input[@name='knowledgePreregisteredEmailResponse'] | "
        "//input[contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'recovery')]"
    )
    try:
        type_and_submit(driver, input_xpath, recovery_email, timeout=8, submit=False)
        click_google_next(driver, timeout=8)
        print("[+] Recovery email challenge submitted.")
        return True
    except Exception as exc:
        print(f"[!] Recovery email challenge could not be submitted: {exc}")
        return False


def _submit_otp_code(driver, code):
    if not code:
        return False
    code_xpath = (
        "//input[@type='tel'] | "
        "//input[@name='totpPin'] | "
        "//input[@name='idvPin'] | "
        "//input[contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'code')]"
    )
    try:
        type_and_submit(driver, code_xpath, code, timeout=8, submit=False)
        click_google_next(driver, timeout=8)
        print("[+] 2FA code submitted.")
        return True
    except Exception as exc:
        print(f"[!] 2FA code could not be submitted automatically: {exc}")
        return False


def _handle_login_challenges(driver, account, timeout=75):
    end_time = time.time() + timeout
    used_otp = False
    used_recovery = False
    while time.time() < end_time:
        if wait_for_gmail_ready(driver, timeout=3):
            return True

        text = _body_text(driver)
        if "wrong password" in text or "couldn" in text and "sign you in" in text:
            print("[!] Google reported a login problem. Check the account credentials.")
            return False

        if not used_recovery and ("recovery email" in text or "confirm your recovery email" in text):
            _click_recovery_email_option(driver)
            if _submit_recovery_email(driver, account.get("recovery_email", "")):
                used_recovery = True
                time.sleep(2)
                continue

        code = _account_code(account)
        if not used_otp and code and ("verification code" in text or "2-step" in text or "2-step verification" in text or "enter the code" in text):
            if _submit_otp_code(driver, code):
                used_otp = True
                time.sleep(2)
                continue

        if "try another way" in text and account.get("recovery_email") and not used_recovery:
            try:
                wait_and_click(
                    driver,
                    "//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'try another way')]",
                    timeout=5,
                )
                time.sleep(1)
                _click_recovery_email_option(driver)
                continue
            except Exception:
                pass

        time.sleep(2)

    if wait_for_gmail_ready(driver, timeout=3):
        return True
    print("[!] Login did not finish automatically. Unsupported Google challenge may need manual approval.")
    return False


def ensure_gmail_login(driver, account=None, page_load_time=30, manual_wait=90):
    """Open Gmail and sign in with account credentials when the profile is not already logged in."""
    account = account or {}
    driver.get("https://mail.google.com")
    if wait_for_gmail_ready(driver, timeout=page_load_time):
        print("[+] Gmail is already open and ready.")
        return True

    email = (account.get("email") or "").strip()
    password = (account.get("password") or "").strip()
    if not email or not password:
        print("[!] No login credentials configured for this account. Waiting for existing/manual Gmail login...")
        return wait_for_gmail_ready(driver, timeout=manual_wait)

    print("[*] Signing in to Gmail with configured account credentials...")
    driver.get(
        "https://accounts.google.com/signin/v2/identifier?service=mail"
        "&continue=https%3A%2F%2Fmail.google.com%2Fmail%2F"
    )

    try:
        type_and_submit(driver, "//input[@type='email' or @id='identifierId']", email, timeout=25, submit=False)
        click_google_next(driver, timeout=12)
    except Exception as exc:
        print(f"[!] Could not enter Gmail email: {exc}")
        return False

    try:
        password_xpath = "//input[@type='password']"
        password_element = WebDriverWait(driver, 35).until(
            EC.element_to_be_clickable((By.XPATH, password_xpath))
        )
        type_text(password_element, password)
        click_google_next(driver, timeout=12)
    except Exception as exc:
        print(f"[!] Could not enter Gmail password: {exc}")
        return False

    if _handle_login_challenges(driver, account, timeout=max(45, page_load_time + manual_wait)):
        print("[+] Gmail login completed.")
        return True
    return False

def _visible_text_inputs(driver):
    inputs = driver.find_elements(
        By.XPATH,
        "//input[not(@type='hidden') and not(@type='password') and not(@type='email')] | //textarea",
    )
    usable = []
    for element in inputs:
        try:
            if element.is_displayed() and element.is_enabled():
                usable.append(element)
        except Exception:
            continue
    return usable


def _set_sender_name_in_current_window(driver, full_name):
    try:
        radios = driver.find_elements(By.XPATH, "//input[@type='radio']")
        if len(radios) >= 2:
            driver.execute_script("arguments[0].click();", radios[-1])
            time.sleep(0.2)
    except Exception:
        pass

    input_elem = None
    name_xpaths = [
        "//input[@name='name' and not(@type='hidden')]",
        "//input[contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'name')]",
        "//input[contains(translate(@placeholder, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'name')]",
    ]
    for xpath in name_xpaths:
        elems = driver.find_elements(By.XPATH, xpath)
        elems = [elem for elem in elems if elem.is_displayed() and elem.is_enabled()]
        if elems:
            input_elem = elems[-1]
            break

    if not input_elem:
        usable = _visible_text_inputs(driver)
        if usable:
            input_elem = usable[-1]

    if not input_elem:
        return False

    type_text(input_elem, full_name)
    try:
        driver.execute_script(
            "arguments[0].dispatchEvent(new Event('input', {bubbles:true}));"
            "arguments[0].dispatchEvent(new Event('change', {bubbles:true}));"
            "arguments[0].blur();",
            input_elem,
        )
    except Exception:
        pass

    save_xpath = (
        "//input[@type='submit' and (contains(@value,'Save') or contains(@value,'Save Changes'))] | "
        "//button[contains(., 'Save') or contains(., 'Save Changes')] | "
        "//*[@role='button' and (contains(., 'Save') or contains(., 'Save Changes'))]"
    )
    try:
        save_btn = WebDriverWait(driver, 8).until(
            EC.element_to_be_clickable((By.XPATH, save_xpath))
        )
        driver.execute_script("arguments[0].click();", save_btn)
        return True
    except Exception as exc:
        print(f"    [!] Could not click sender-name save button: {exc}")
    return False


def _find_edit_info_control(driver, candidate_xpaths):
    for xpath in candidate_xpaths:
        elems = driver.find_elements(By.XPATH, xpath)
        elems = [elem for elem in elems if elem.is_displayed()]
        if elems:
            return elems[0]

    try:
        return driver.execute_script(
            """
            function ownText(el) {
                let text = '';
                for (const node of el.childNodes) {
                    if (node.nodeType === Node.TEXT_NODE) text += node.textContent;
                }
                return text.trim().toLowerCase();
            }
            const selectors = '[role="link"], a, span, td, div';
            const candidates = [...document.querySelectorAll(selectors)];
            return candidates.find(el => {
                const own = ownText(el);
                const all = (el.textContent || '').trim().toLowerCase();
                const visible = !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
                return visible && (own === 'edit info' || all === 'edit info');
            }) || null;
            """
        )
    except Exception:
        return None


def update_profile_name(driver, full_name, account_email=""):
    """Update Gmail's Send mail as display name for the active account."""
    attempts = 3
    main_handle = driver.current_window_handle
    for attempt in range(1, attempts + 1):
        try:
            print(f"[~] update_profile_name attempt {attempt}: setting display name to '{full_name}'")
            driver.get("https://mail.google.com/mail/u/0/#settings/accounts")
            WebDriverWait(driver, 25).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'send mail as')]",
                    )
                )
            )
            time.sleep(1.5)

            candidates_xpaths = []
            if account_email:
                candidates_xpaths.extend(
                    [
                        f"//tr[.//*[contains(., '{account_email}')]]//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'edit info')]",
                        f"//*[contains(., '{account_email}')]/ancestor::tr[1]//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'edit')]",
                    ]
                )
            candidates_xpaths.extend(
                [
                    "//*[@role='link' and contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'edit info')]",
                    "//*[self::span or self::td or self::div][contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'edit info') and @role='link']",
                    "//a[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'edit info')]",
                    "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'edit info')]",
                    "//*[contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'edit info')]",
                    "//table//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'edit')]",
                ]
            )

            edit_elem = _find_edit_info_control(driver, candidates_xpaths)

            if not edit_elem:
                print(f"    [!] attempt {attempt}: edit control not found; will retry")
                time.sleep(2)
                continue

            before = set(driver.window_handles)
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", edit_elem)
            time.sleep(0.2)
            try:
                driver.execute_script("arguments[0].click();", edit_elem)
            except Exception:
                edit_elem.click()

            time.sleep(1.5)
            handles = driver.window_handles
            if not handles:
                raise Exception("No browser window handles remain after clicking edit info")

            new_handles = [handle for handle in handles if handle not in before]
            target_handle = new_handles[0] if new_handles else handles[-1]
            updated = False

            try:
                driver.switch_to.window(target_handle)
            except Exception:
                driver.switch_to.window(handles[-1])
                target_handle = handles[-1]

            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located(
                        (
                            By.XPATH,
                            "//body | (//div[@role='dialog'])[last()] | //input[@name='name'] | //input[@type='submit']",
                        )
                    )
                )
            except Exception:
                pass

          
            try:
                # XPath ko broad kar diya hy (koi bhi text input ya name field)
                name_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//input[@type='text' or contains(@name, 'name') or contains(@name, 'nvp_bu_name')]"))
                )
                # Javascript ke zariye jabran (forcefully) focus aur click karwa rahe hen
                driver.execute_script("arguments[0].focus();", name_input)
                time.sleep(0.5)
                name_input.send_keys(Keys.CONTROL + "a") 
                time.sleep(0.5)
                name_input.send_keys(Keys.BACKSPACE)     
                time.sleep(0.5)
                name_input.send_keys(full_name)          
                time.sleep(1)
                
                save_button = driver.find_element(By.XPATH, "//input[@type='submit' or @name='nvp_bu_save'] | //button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), 'save')]")
                driver.execute_script("arguments[0].click();", save_button) # Javascript click
                updated = True
            except Exception as e:
                print(f"    [-] Error typing new name inline: {e}")
                updated = False
            # =====================================================================

            time.sleep(1)

            try:
                if target_handle != main_handle and target_handle in driver.window_handles:
                    driver.close()
            except Exception:
                pass

            remaining_handles = driver.window_handles
            if remaining_handles:
                driver.switch_to.window(main_handle if main_handle in remaining_handles else remaining_handles[0])

            driver.get("https://mail.google.com/mail/u/0/#inbox")
            wait_for_gmail_ready(driver, timeout=12)

            if updated:
                print(f"[+] Profile name updated to: {full_name}")
                return True

            print(f"    [!] attempt {attempt}: sender-name form was not updated; will retry")
            time.sleep(2)

        except Exception as e:
            print(f"    [!] update_profile_name attempt {attempt} failed: {e}")
            try:
                if main_handle in driver.window_handles:
                    driver.switch_to.window(main_handle)
                driver.get("https://mail.google.com/mail/u/0/#inbox")
            except Exception:
                pass
            time.sleep(2)

    print("[!] update_profile_name: all attempts failed")
    try:
        driver.get("https://mail.google.com/mail/u/0/#inbox")
    except Exception:
        pass
    return False
def draft_email(driver, full_name, to_email, cc_email, subject_template, body_template):
    """Compose an email using JavaScript to focus fields and fill templates (subject and body)."""
    print(f"[*] Drafting email for: {full_name}")
    
    try:
        driver.switch_to.alert.dismiss()
    except:
        pass

    try:
        print("    -> Clicking Compose...")
        compose_xpath = (
            '//div[text()="Compose"] | //button[normalize-space()="Compose"] | '
            '//*[@aria-label="Compose"] | //div[@role="button" and contains(@class, "T-I-KE")] | '
            '//div[contains(@aria-label, "Compose")] | //div[@gh="cm"]'
        )
        try:
            wait_and_click(driver, compose_xpath, timeout=15)
        except Exception as click_err:
            print(f"    [!] Compose initial click failed: {click_err}. Will try fallbacks.")
        time.sleep(2.5)

        print("    -> Waiting for compose window...")
        try:
            WebDriverWait(driver, 18).until(
                EC.presence_of_element_located((By.XPATH, '(//div[@role="dialog"])[last()]//input[@type="email"] | (//div[@role="dialog"])[last()]//input[contains(@aria-label, "To")] | (//div[@role="dialog"])[last()]//div[@role="textbox"] | (//div[@role="dialog"])[last()]//textarea'))
            )
        except Exception as wait_err:
            print(f"    [!] Compose dialog not found after click: {wait_err}. Trying fallbacks...")
            try:
                driver.execute_script("""var el=document.querySelector('[gh="cm"]')||document.querySelector('[aria-label="Compose"]')||document.querySelector('div[role="button"][gh]'); if(el){el.click();}""")
                print("    -> JS click fallback attempted")
            except Exception as js_err:
                print(f"    [!] JS click fallback failed: {js_err}")
            time.sleep(1.0)
            try:
                body = driver.find_element(By.TAG_NAME, "body")
                body.send_keys('c')
                print("    -> Sent 'c' keyboard shortcut")
            except Exception as kb_err:
                print(f"    [!] Keyboard fallback failed: {kb_err}")
            time.sleep(1.0)
            try:
                driver.get("https://mail.google.com/mail/?view=cm&fs=1&tf=1")
                print("    -> Opened compose via direct URL")
            except Exception as url_err:
                print(f"    [!] Direct URL fallback failed: {url_err}")
            try:
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '(//div[@role="dialog"])[last()]')))
            except Exception as final_err:
                print(f"    [!] Final fallback did not find compose dialog: {final_err}")
                raise
        time.sleep(0.5)

        print("    -> Step 2: Filling 'To' and 'Cc'...")
        
        to_input_xpath = (
            '(//div[@role="dialog"])[last()]//input[@type="email"] | '
            '(//div[@role="dialog"])[last()]//textarea[contains(@aria-label, "To")] | '
            '(//div[@role="dialog"])[last()]//input[contains(@aria-label, "To")] | '
            '(//div[@role="dialog"])[last()]//input[contains(@placeholder, "To")] | '
            '(//div[@role="dialog"])[last()]//input[@role="combobox" and contains(@aria-label, "recipient")]'
        )

        to_elem = WebDriverWait(driver, 12).until(
            EC.element_to_be_clickable((By.XPATH, to_input_xpath))
        )
        type_text(to_elem, to_email)
        to_elem.send_keys(Keys.ENTER)
        time.sleep(0.5)
        
        # FIX 2: Check if CC is not empty
        if cc_email and cc_email.strip():
            print("    -> Adding CC...")
            try:
                # ==========================================
                # STEP 1: PEHLE 'Cc' BUTTON KO CLICK KARO
                # ==========================================
                cc_buttons = driver.find_elements(By.XPATH, "//*[@aria-label='Add Cc recipients' or @aria-label='Add Cc' or text()='Cc' or text()=' Cc ']")
                
                button_clicked = False
                for btn in cc_buttons:
                    if btn.is_displayed():
                        # JS Click: Yeh kabhi fail nahi hota, exact nishane par lagta hy
                        driver.execute_script("arguments[0].click();", btn) 
                        time.sleep(1.5) # Dabba khulne ka wait
                        print("    -> [DEBUG] 'Cc' button clicked successfully!")
                        button_clicked = True
                        break
                
                if not button_clicked:
                    print("    -> [!] Could not find the 'Cc' button to click.")

                # ==========================================
                # STEP 2: AB DABBA KHUL GAYA HY, USME TYPE KARO
                # ==========================================
                cc_boxes = driver.find_elements(By.XPATH, "//input[contains(@aria-label, 'Cc') or @name='cc']")
                
                cc_success = False
                for box in cc_boxes:
                    if box.is_displayed(): 
                        print("    -> [DEBUG] Visible CC field found")
                        
                        box.send_keys(cc_email)
                        print(f"    -> [DEBUG] Typed CC Email: {cc_email}")
                        
                        time.sleep(3) # Wait taake Gmail parh le
                        
                        box.send_keys(Keys.TAB) # Chip/Bubble banao
                        time.sleep(1.5)
                        
                        print(f"    -> CC ({cc_email}) locked successfully!")
                        cc_success = True
                        break
                
                # Fallback: Agar phir bhi dabba na mile
                if not cc_success:
                    print("    -> [!] Backup method: Using active cursor...")
                    active_box = driver.switch_to.active_element
                    active_box.send_keys(cc_email)
                    time.sleep(3)
                    active_box.send_keys(Keys.TAB)
                    time.sleep(1)
                    print(f"    -> CC ({cc_email}) locked via backup!")

            except Exception as cc_err:
                print(f"    [!] Error typing CC: {type(cc_err).__name__}: {cc_err}")
        print("    -> Step 1: Filling Subject and Body from Notepad...")
        
        final_subject = subject_template.replace("{full_name}", full_name).replace("{{full_name}}", full_name)
        # Better subject selector
        subject_input_xpath = (
            '(//div[@role="dialog"])[last()]//input[@placeholder="Subject"] | '
            '(//div[@role="dialog"])[last()]//input[contains(@aria-label, "Subject")] | '
            '(//div[@role="dialog"])[last()]//input[@name="subjectbox"]'
        )
        try:
            subject_elem = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, subject_input_xpath))
            )
            type_text(subject_elem, final_subject)
            print("    -> Subject filled")
        except Exception as subject_err:
            print(f"    [!] Error filling subject: {subject_err}")

        final_body = body_template.replace("{{full_name}}", full_name).replace("{full_name}", full_name).replace("{{fullname}}", full_name)
        body_input_xpath = (
            '(//div[@role="dialog"])[last()]//div[@aria-label="Message Body" and @role="textbox"] | '
            '(//div[@role="dialog"])[last()]//div[contains(@aria-label, "Message Body") and @contenteditable="true"] | '
            '(//div[@role="dialog"])[last()]//div[@role="textbox" and @contenteditable="true"]'
        )
        try:
            body_elem = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, body_input_xpath))
            )
            type_text(body_elem, final_body)
            print("    -> Message body filled")
        except Exception as body_err:
            print(f"    [!] Error filling message body: {body_err}")

        print("[+] Email draft ready with To, Cc, Subject, and Body.")
        
    except Exception as e:
        # --- IMPROVED DEBUGGING CODE ---
        print("\n================== 🔴 DEBUG INFO ==================")
        print(f"Current URL: {driver.current_url}")
        print(f"Window Handles: {driver.window_handles}")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")
        print(f"Full Exception: {repr(e)}")
        
        try:
            print(f"Current Page Title: {driver.title}")
        except:
            print("Could not retrieve page title")
            
        print("===================================================\n")
        raise


def wait_for_attachments(driver, timeout=30, poll_interval=0.8):
    """Wait until there are no active upload indicators inside the most recent compose dialog.
    Returns True if no uploads detected or uploads finished within timeout, else False.
    """
    try:
        dialog = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "(//div[@role='dialog'])[last()]"))
        )
    except Exception:
        # No compose dialog visible
        return True

    end_time = time.time() + timeout
    while time.time() < end_time:
        try:
            # Look for common upload indicators inside the dialog
            uploading_items = dialog.find_elements(By.XPATH, 
                ".//*[contains(text(),'Uploading') or contains(text(),'uploading') or @role='progressbar' or contains(@aria-label,'Uploading') or contains(@aria-label,'Uploading')]")
            if not uploading_items:
                # No active upload indicators found
                return True
        except Exception:
            return True
        time.sleep(poll_interval)
    return False


def attach_files_via_input(driver, file_paths, timeout=10):
    """Attach files using a hidden <input type='file'> inside Gmail compose if available.
    This is faster and more reliable than using the OS file dialog + pyautogui.
    Returns True if at least one file was attached, False otherwise.
    """
    try:
        # Prefer input inside the most recent compose dialog, fallback to any file input on page
        input_xpath = "(//div[@role='dialog'])[last()]//input[@type='file'] | //input[@type='file']"
        file_input = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, input_xpath))
        )
        # Ensure the input is visible/interactable
        try:
            driver.execute_script("arguments[0].style.display = 'block'; arguments[0].style.visibility='visible'; arguments[0].style.opacity=1;", file_input)
        except Exception:
            pass

        attached = False
        for fp in file_paths:
            if not os.path.exists(fp):
                print(f"[!] attach_files_via_input: file not found: {fp}")
                continue
            abs_fp = os.path.abspath(fp)
            try:
                # send_keys requires an absolute path on Windows
                file_input.send_keys(abs_fp)
                attached = True
            except Exception as send_err:
                print(f"[!] attach_files_via_input send failed for {abs_fp}: {send_err}")
                # try to make input visible and retry
                try:
                    driver.execute_script("arguments[0].style.display = 'block'; arguments[0].style.visibility='visible'; arguments[0].style.opacity=1;", file_input)
                    file_input.send_keys(abs_fp)
                    attached = True
                except Exception as send_err2:
                    print(f"[!] attach_files_via_input retry failed for {abs_fp}: {send_err2}")
                    continue
            # small pause to let the upload start
            time.sleep(0.5)
        return attached
    except Exception as e:
        print(f"[!] attach_files_via_input failed: {e}")
        return False



def send_current_draft(driver, timeout=20):
    """Click Send on the active compose dialog and wait for it to close.
    Tries multiple fallbacks and requires Gmail's "Message sent" confirmation.
    Returns True if sent, False otherwise.
    """
    try:
        dialog = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, "(//div[@role='dialog'])[last()]"))
        )
    except Exception as e:
        print(f"[!] send_current_draft: no compose dialog found: {e}")
        return False

    send_xpaths = [
        "(//div[@role='dialog'])[last()]//*[@role='button' and (normalize-space(.)='Send' or @aria-label='Send' or contains(@aria-label,'Send'))]",
        "(//div[@role='dialog'])[last()]//button[normalize-space()='Send']",
        "//div[@role='button' and normalize-space()='Send']",
        "//div[text()='Send' and @role='button']",
        "//button[@aria-label='Send']"
    ]

    clicked = False
    for xp in send_xpaths:
        try:
            send_btn = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.XPATH, xp)))
            try:
                driver.execute_script("arguments[0].click();", send_btn)
            except Exception:
                try:
                    send_btn.click()
                except Exception as click_err:
                    print(f"    [!] send click failed for xpath {xp}: {click_err}")
                    continue
            clicked = True
            break
        except Exception:
            continue

    if not clicked:
        print("[!] send_current_draft: no clickable Send button found; trying Ctrl+Enter fallback")
        try:
            body_elem = None
            try:
                body_elem = driver.find_element(By.XPATH, "(//div[@role='dialog'])[last()]//div[@role='textbox'] | //div[@role='textbox']")
            except Exception:
                pass
            if body_elem:
                try:
                    body_elem.send_keys(Keys.CONTROL, Keys.ENTER)
                    print("    -> Ctrl+Enter fallback sent")
                except Exception as send_err:
                    print(f"    [!] Ctrl+Enter send failed: {send_err}")
            else:
                try:
                    subj = driver.find_element(By.XPATH, "(//div[@role='dialog'])[last()]//input[@name='subjectbox'] | (//div[@role='dialog'])[last()]//input[contains(@placeholder,'Subject')]")
                    subj.send_keys(Keys.CONTROL, Keys.ENTER)
                    print("    -> Ctrl+Enter fallback sent via subject")
                except Exception:
                    print("    [!] Ctrl+Enter fallback could not find body/subject")
        except Exception as final_err:
            print(f"[!] send_current_draft Ctrl+Enter fallback error: {final_err}")

    try:
        alert = driver.switch_to.alert
        print(f"[!] Unexpected alert present: {alert.text} - accepting.")
        alert.accept()
    except Exception:
        pass

    confirmation_xpath = (
        "//*[contains(text(),'Message sent') or "
        "contains(text(),'Your message has been sent') or "
        "contains(@aria-label,'Message sent')]"
    )
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, confirmation_xpath))
        )
        try:
            WebDriverWait(driver, 8).until(EC.staleness_of(dialog))
        except Exception:
            pass
        return True
    except Exception as confirm_err:
        pass

    try:
        visible_errors = driver.find_elements(
            By.XPATH,
            "//*[contains(text(),'invalid') or contains(text(),'required') or contains(text(),'could not be sent') or contains(text(),'Message not sent')]",
        )
        for err in visible_errors[:3]:
            if err.is_displayed():
                print(f"[!] Gmail send error: {err.text}")
    except Exception:
        pass

    try:
        if dialog.is_displayed():
            print("[!] send_current_draft: compose is still open; message was not confirmed sent.")
        else:
            print("[!] send_current_draft: compose closed without a send confirmation; not counting as sent.")
    except Exception:
        print("[!] send_current_draft: compose disappeared without a send confirmation; not counting as sent.")
    return False
