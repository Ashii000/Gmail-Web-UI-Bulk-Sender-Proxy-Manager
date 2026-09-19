import pyautogui
import pyperclip
import time
import os


def attach_local_file(file_path):
    """
    Handle the Windows 'Open File' dialog by pasting the full file path into the dialog
    and pressing Enter to confirm the selection.
    """
    print(f"[*] Attaching file: {os.path.basename(file_path)}")

    if not os.path.exists(file_path):
        print(f"[-] Error: File not found -> {file_path}")
        return False

    try:
        # Short pause to allow the file dialog to open
        time.sleep(0.6)

        # Copy the file path into the clipboard
        pyperclip.copy(file_path)

        # Paste the path into the dialog (Ctrl+V)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.2)
        
        # Confirm selection (Enter)
        pyautogui.press('enter')

        print("[+] File attach command sent. Waiting for upload...")
        # Allow time for the system to begin uploading the file
        time.sleep(1)
        return True
    except Exception as e:
        print(f"[-] Error during file attachment: {e}")
        return False


# Testing block
if __name__ == "__main__":
    print("[!] Testing File Handler...")
    print("Open a Notepad window - script will paste a test file path in 5 seconds...")
    time.sleep(5)
    test_path = r"C:\Users\Desktop\text\w9_form.pdf"
    pyperclip.copy(test_path)
    pyautogui.hotkey('ctrl', 'v')
    pyautogui.press('enter')
    print("[+] Test complete!")