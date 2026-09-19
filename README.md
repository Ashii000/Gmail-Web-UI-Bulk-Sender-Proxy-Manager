# 📧 Gmail Web UI Bulk Sender & Proxy Manager

![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)
![Selenium](https://img.shields.io/badge/Selenium-Undetected-green.svg)
![Automation](https://img.shields.io/badge/Automation-Web%20Scraping-orange.svg)
![License](https://img.shields.io/badge/License-MIT-lightgrey.svg)

An advanced, scalable web automation solution designed to manage bulk email operations securely and efficiently. Built with Python, this tool leverages `undetected-chromedriver` and **Smartproxy** residential IP rotation to bypass anti-bot detections. It provides a robust architecture for automating Gmail UI interactions without triggering security blocks, making it ideal for large-scale email campaign management.

## 🚀 Key Features

*   **🛡️ Anti-Detect Browsing:** Utilizes `undetected-chromedriver` to simulate human-like behavior and bypass Google's automated bot detection systems.
*   **🌐 Dynamic Proxy Management:** Seamlessly integrates with Smartproxy for rotating residential IPs, ensuring each account logs in from a unique, secure network environment.
*   **⚙️ Automated UI Interaction:** Handles the complete flow via Web UI, including secure login, navigating to Compose, attaching subjects/messages, and sending.
*   **📂 Modular Architecture:** Clean, maintainable codebase separated into specific modules (Browser Setup, Account Loading, Gmail Actions, Proxy Management).
*   **☁️ RDP/VPS Ready:** Includes PowerShell scripts (`setup_rdp.ps1`) and runbooks for quick deployment on Windows Servers or remote desktops.

---

## 🛠️ Prerequisites

Before you begin, ensure you have met the following requirements:
*   **Python 3.8+** installed on your machine.
*   **Google Chrome** browser installed (must match the ChromeDriver version).
*   Active **Smartproxy** account (or equivalent) for residential IP rotation.

---

## 💻 Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Ashii000/Gmail-Web-UI-Bulk-Sender-Proxy-Manager.git
   cd Gmail-Web-UI-Bulk-Sender-Proxy-Manager
   ```

2. **Create and activate a virtual environment (Recommended):**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Linux/Mac:
   source venv/bin/activate
   ```

3. **Install the required dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

---

## ⚙️ Configuration & Setup

You need to configure your input files before running the script. **⚠️ Note: Never upload files containing real passwords or proxy credentials to GitHub.**

1. **`config.json`**: Add your proxy provider credentials and general settings.
2. **`input_data/accounts.csv`**: List the target Gmail accounts you wish to automate.
   * Format: `Email,Password,RecoveryEmail`
3. **`subject.txt`**: Enter the subject line for your email campaign.
4. **`message.txt`**: Enter the main body content of your email.

---

## 🚦 Usage

Once configured, simply run the main script to start the automation process:

```bash
python main.py
```

The script will:
1. Read the accounts from `accounts.csv`.
2. Assign a unique proxy to the session via `smartproxy.py`.
3. Launch an undetected Chrome browser.
4. Perform the automated login and email sending tasks.
5. Log the output in `run_log.txt`.

---

## 📁 Project Structure

```text
├── main.py                     # Main execution script
├── requirements.txt            # Python dependencies
├── config.json                 # Global configuration and proxy credentials
├── subject.txt                 # Email subject content
├── message.txt                 # Email body content
├── run_log.txt                 # Execution logs
├── input_data/
│   └── accounts.csv            # Target Gmail accounts (Email, Pass, Recovery)
├── modules/                    # Core functional modules
│   ├── __init__.py
│   ├── account_loader.py       # Handles CSV data parsing
│   ├── browser_setup.py        # Configures undetected-chromedriver
│   ├── csv_processor.py        # Processes bulk data inputs
│   ├── file_handler.py         # Reads text/json files
│   └── gmail_actions.py        # Handles UI element interactions
├── proxy_manager/
│   └── smartproxy.py           # Smartproxy API/Integration handling
├── setup_rdp.ps1               # Automated environment setup for RDPs
└── RDP_RUNBOOK.md              # Deployment guide for RDP/VPS
```

---

## ⚠️ Disclaimer

This project is developed for **educational purposes and authorized testing only**. Automated interaction with Google's services may violate their Terms of Service. The developer assumes no liability and is not responsible for any misuse, account bans, or damages caused by this software. Use at your own risk.

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](https://github.com/Ashii000/Gmail-Web-UI-Bulk-Sender-Proxy-Manager/issues).
