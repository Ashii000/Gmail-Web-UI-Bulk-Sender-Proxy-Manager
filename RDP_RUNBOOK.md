RDP Deployment & Runbook

1) Connect to RDP (Windows Remote Desktop)
- Open Remote Desktop Connection (mstsc.exe), enter IP, click Connect, provide credentials.
- Keep the session unlocked while running the bot (pyautogui requires an active desktop).

2) Install prerequisites on the remote machine
- Install Google Chrome (stable) and ensure version number (Help > About Chrome).
- Install Python 3.12+ and check "Add Python to PATH" during installer.
- Open PowerShell as Administrator and run:
    python -m pip install --upgrade pip
    pip install -r requirements.txt

3) Copy project files
- Copy the entire project folder (Web Automaton) to the remote Desktop (e.g., C:\Users\<User>\Desktop\Web Automaton)
- Ensure the following folders exist and are set in config.json: attachment_folders.w9_folder_path and invoice_folder_path. Use %USERPROFILE% or ~ to make paths portable.

4) Configure ChromeDriver compatibility
- The script uses undetected-chromedriver which tries to auto-download a matching driver.
- If Chrome update mismatch occurs, edit modules/browser_setup.py fallback version_main (e.g., 148) or upgrade Chrome to match the driver.

5) Configure environment and secrets securely
- Put sensitive values (if any) as Windows Environment Variables or use Windows Credential Manager.
- Do NOT put API keys or passwords into config.json stored on disk in plain text.

6) Adjust config.json for the remote user
- Use paths with %USERPROFILE% or ~ to avoid hardcoding usernames, e.g. "%USERPROFILE%\\Desktop\\text"
- Example: "w9_folder_path": "%USERPROFILE%\\Desktop\\text"

7) Running the bot
- Keep RDP session active and unlocked during runs.
- From project folder run:
    python "d:\Web Automaton\main.py"
- Watch the console logs. If pyautogui is used for attachments, the RDP session must be the active desktop.
To close the RDP without stopping the bot, DO NOT click the X button. Instead, run the Disconnect_RDP_Safely.bat file as Administrator.

8) Troubleshooting
- If browser fails to start, check Chrome version and adjust version_main in modules/browser_setup.py.
- If attachments fail, ensure files exist and permissions allow read access.
- For stability and higher throughput consider replacing UI automation with Gmail API (server-side sending) to avoid GUI fragility.

9) Optional: Creating a scheduled task (run when user is logged in)
- Use Windows Task Scheduler to run the script only when a specific user session is active (required for pyautogui). Use "Run only when user is logged on".

Notes:
- pyautogui-based attachments require an interactive desktop. For headless or unattended servers, prefer DOM file-input attach or Gmail API.
- Keep Chrome up-to-date and adjust undetected-chromedriver fallback if necessary.
