# Saving Group — Loan Management System
### School Project | Built with AI assistance

---

## What this app does

This app replaces the Excel spreadsheet system for managing a saving group.
It stores all data securely in a database (SQLite) and runs as a Windows desktop app.

---

## Features

| Feature | Description |
|---|---|
| 🔐 Login / Password | Username + password login. Only authorised users can access |
| 👥 Members | Add, edit, deactivate members. Search by name |
| 💳 Loans | Issue loans, record repayments, auto-calculate interest (10% p.a. daily) |
| 💵 Savings | Record quarterly savings (Rs 6,000 default). Bulk entry for all members at once |
| 📊 Reports | Export Active Loans, Savings, Quarterly Statement to Excel |
| 📋 Audit Log | Every action (who did what, when) is permanently recorded |
| 📂 Import Excel | Import member names from your old Excel file |
| ⚙️ Settings | Change password, configure the system |

---

## Interest Formula

```
Interest = Principal × 10% × Days / 365
```

This matches exactly how the original Excel was calculating daily interest.

---

## How to build the .exe (Windows)

### Requirements
- Windows 10 or 11
- Python 3.10 or higher installed from https://python.org
  - ⚠️ During install, check "Add Python to PATH"

### Steps
1. Put all files in one folder:
   - `app.py`
   - `BUILD_EXE.bat`
   - `requirements.txt`

2. Double-click `BUILD_EXE.bat`

3. Wait 2–3 minutes. It will say "Done!" when finished.

4. Your app is in the `dist` folder: `SavingGroup_LoanManagement.exe`

5. Copy the `.exe` file anywhere you want. It works standalone.

---

## First Run

1. Open `SavingGroup_LoanManagement.exe`
2. Login with:
   - Username: `admin`
   - Password: `admin123`
3. **Go to Settings → Change Password immediately!**
4. Import your existing members from Excel using Settings → Import Members

---

## Database

The database file (`saving_group.db`) is created in the same folder as the `.exe`.
- **Back it up regularly** — copy it to a USB drive or Google Drive
- All your data is in this one file
- Never delete it unless you want to start fresh

---

## Security Features

- Passwords are stored as SHA-256 hashes (never in plain text)
- Every action is recorded in the Audit Log with timestamp and username
- Database uses foreign key constraints to prevent orphaned data
- No network connection needed — runs completely offline

---

## If you need help

The app was built to match exactly how the Excel file worked:
- 48–50 members
- Quarterly savings of Rs 6,000
- Loans with 10% annual interest, calculated daily
- Quarterly statements showing principal + interest + savings

---

*Built as a school project using Python + CustomTkinter + SQLite*
