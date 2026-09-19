import undetected_chromedriver as uc
import os
import time
import shutil
import subprocess
import tempfile
import winreg
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
import undetected_chromedriver as uc
import random
import string
from proxy_manager.smartproxy import create_proxy_extension

PROXY_HOST = "as.smartproxy.net"
PROXY_PORT = "3120"
PROXY_BASE_USER = "smart-z0m64h9erqgs_area-US_life-15_session-" 
PROXY_PASS = "rxkzvtMf8JT1rIbz" 

def generate_random_session_id(length=8):
    """Yeh function 8 characters ka ek random code banayega har naye account ke liye"""
    letters_and_digits = string.ascii_letters + string.digits
    return ''.join(random.choice(letters_and_digits) for i in range(length))


def get_installed_chrome_version():
    """Return the installed Chrome version string when it can be detected."""
    registry_roots = (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE)
    for root in registry_roots:
        try:
            with winreg.OpenKey(root, r"Software\Google\Chrome\BLBeacon") as key:
                version, _ = winreg.QueryValueEx(key, "version")
                if version:
                    return version
        except Exception:
            pass

    chrome_paths = [
        os.path.join(os.environ.get("PROGRAMFILES", ""), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "Application", "chrome.exe"),
        shutil.which("chrome") or "",
        shutil.which("google-chrome") or "",
    ]
    for path in chrome_paths:
        if not path or not os.path.exists(path):
            continue
        try:
            output = subprocess.check_output([path, "--version"], text=True, timeout=5).strip()
            parts = output.split()
            if parts:
                return parts[-1]
        except Exception:
            continue
    return ""


def get_installed_chrome_major():
    version = get_installed_chrome_version()
    try:
        return int(version.split(".", 1)[0])
    except Exception:
        return None


def find_local_chromedriver(current_dir):
    """Search common locations for a local chromedriver executable.
    Returns the full path if found, otherwise None.
    """
    candidates = []
    env_path = os.environ.get('CHROMEDRIVER_PATH')
    if env_path:
        candidates.append(env_path)
    candidates.append(os.path.join(current_dir, 'drivers', 'chromedriver.exe'))
    candidates.append(os.path.join(current_dir, 'chromedriver.exe'))
    which_cd = shutil.which('chromedriver')
    if which_cd:
        candidates.append(which_cd)

    for p in candidates:
        try:
            if p and os.path.exists(p):
                return p
        except Exception:
            continue
    return None


def _add_common_options(options, profile_path):
    options.add_argument(f"--user-data-dir={profile_path}")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--password-store=basic")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    return options


def setup_browser(profile_path=None, fresh_profile=False):
    """Initialize browser. Try undetected-chromedriver first, then fall back to a local chromedriver
    (selenium) if network download fails or no driver can be obtained automatically.
    """
    current_dir = os.getcwd()
    if fresh_profile:
        profile_path = tempfile.mkdtemp(prefix="gmail_bot_profile_")
    elif not profile_path:
        profile_path = os.path.join(current_dir, "chrome_profile")
    elif not os.path.isabs(profile_path):
        profile_path = os.path.join(current_dir, profile_path)

    os.makedirs(profile_path, exist_ok=True)
    chrome_major = get_installed_chrome_major()
    chrome_version = get_installed_chrome_version()
    if chrome_version:
        print(f"[*] Detected Chrome version: {chrome_version}")

    # Configure undetected-chromedriver options
    options = uc.ChromeOptions()
    _add_common_options(options, profile_path)
    print("[*] Setting up Smartproxy Extension...")
    random_session = generate_random_session_id()
    dynamic_proxy_user = PROXY_BASE_USER + random_session
    print(f"[*] Assigning New Proxy Session: {dynamic_proxy_user}")
    
    proxy_plugin_path = create_proxy_extension(PROXY_HOST, PROXY_PORT, dynamic_proxy_user, PROXY_PASS)
    options.add_argument(f'--load-extension={proxy_plugin_path}')
    # =========================================================



    print("[*] Initializing undetected-chromedriver...")

    try:
        if chrome_major:
            driver = uc.Chrome(options=options, version_main=chrome_major)
        else:
            driver = uc.Chrome(options=options)
        print("[+] Browser started (undetected-chromedriver) and profile loaded.")
        return driver
    except Exception as e1:
        print(f"[!] Matching-version undetected-chromedriver failed: {e1}")

        print("[*] Trying undetected-chromedriver auto fallback...")
        try:
            fallback_options = uc.ChromeOptions()
            _add_common_options(fallback_options, profile_path)
            driver = uc.Chrome(options=fallback_options)
            print("[+] Browser started with undetected-chromedriver auto fallback.")
            return driver
        except Exception as e_auto:
            print(f"[!] Auto fallback failed: {e_auto}")

        found = find_local_chromedriver(current_dir)
        if found:
            try:
                print(f"[*] Found local chromedriver at: {found}; launching selenium fallback.")
                selenium_options = webdriver.ChromeOptions()
                _add_common_options(selenium_options, profile_path)
                service = Service(found)
                driver = webdriver.Chrome(service=service, options=selenium_options)
                print("[+] Browser started with local chromedriver (selenium).")
                return driver
            except Exception as e_local:
                print(f"[-] Local chromedriver start failed: {e_local}")

        try:
            print("[*] Trying Selenium Manager fallback for a matching driver...")
            selenium_options = webdriver.ChromeOptions()
            _add_common_options(selenium_options, profile_path)
            driver = webdriver.Chrome(options=selenium_options)
            print("[+] Browser started with Selenium Manager.")
            return driver
        except Exception as e_selenium:
            print(f"[-] Browser start error: {e_selenium}")
            return None


# If run directly, open Gmail for manual login
if __name__ == "__main__":
    driver = setup_browser()
    if driver:
        driver.get("https://mail.google.com")
        print("[!] If this is the first run, please log in manually in the browser window.")
        time.sleep(60)
        driver.quit()
