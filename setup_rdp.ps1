# setup_rdp
Write-Host "=== Web Automaton RDP Setup ==="

#  install Chrome and Python (non-interactive if available)
$winget = Get-Command winget -ErrorAction SilentlyContinue
if ($winget) {
    Write-Host "winget found — installing Google Chrome and Python 3..."
    try {
        winget install --id Google.Chrome -e --silent --accept-package-agreements --accept-source-agreements
    } catch {
        Write-Host "[!] winget Chrome install failed or requires user interaction. Please install Chrome manually."
    }
    try {
        winget install --id Python.Python.3 -e --silent --accept-package-agreements --accept-source-agreements
    } catch {
        Write-Host "[!] winget Python install failed. Please install Python 3.12+ manually and ensure 'Add to PATH' is checked."
    }
} else {
    Write-Host "winget not found. Please install Google Chrome and Python manually from their official sites."
}


$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
    Write-Host "Python not found in PATH. After installing Python, re-run this script. Exiting."
    exit 1
}

# Upgrade pip and install python
Write-Host "Upgrading pip and installing Python dependencies..."
python -m pip install --upgrade pip
if (Test-Path "requirements.txt") {
    pip install -r "requirements.txt"
} else {
    Write-Host "requirements.txt not found in current folder. Please ensure you run this script from the project root."
}

# Create chrome_profile directory
$profileDir = Join-Path (Get-Location) "chrome_profile"
if (-not (Test-Path $profileDir)) {
    New-Item -ItemType Directory -Path $profileDir | Out-Null
    Write-Host "Created chrome_profile directory: $profileDir"
} else {
    Write-Host "chrome_profile already exists: $profileDir"
}

Write-Host "Setup script finished. IMPORTANT: Keep the RDP session unlocked during runs (pyautogui needs an active desktop)."
Write-Host "If Chrome/Chromedriver mismatches occur, open modules/browser_setup.py and adjust the fallback version_main value or update Chrome to the matching version."
