# Saving Group — Loan Management System

> A Windows desktop app that replaces the Excel spreadsheet for managing a
> 48–50 member saving group — loans, daily interest, quarterly savings, audits,
> and statements, all in one secure local database.
>
> _School project · Built with AI assistance._

## Features

| Feature | Description |
| --- | --- |
| 🔐 Login / Password | Authorized-access only; PBKDF2-SHA256 password hashing |
| 👥 Members | Add, edit, deactivate members; search by name; inline cell editing |
| 💳 Loans | Issue loans with per-loan interest (10% p.a. default), daily interest, principal/interest repayment split, "interest waived" flag |
| 💵 Savings | Quarterly records (Rs 6,000 default), one-click bulk entry, auto-transfer from repayments |
| 📊 Reports | Export Active Loans, Savings, Quarterly Statement to Excel |
| 📋 Audit Log | Every action (who / what / when) permanently recorded |
| 📂 Import Excel | Import member names from the old spreadsheet |
| ⚙️ Settings | Change password, import members, configure system |

## Interest Formula

```
Interest = Principal × 10% × Days / 365
```

This matches exactly how the original Excel calculated daily interest.

## Getting Started

### Run from source (any OS with Python)

```bash
pip install -r requirements.txt   # customtkinter, pillow, openpyxl
python app.py
```

### Build the .exe (Windows)

1. Install **Python 3.10+** from <https://python.org> — tick **"Add Python to PATH"**.
2. Double-click **`BUILD_EXE.bat`**.
3. Wait 2–3 minutes until it says `Done!`.
4. Grab your standalone app from `dist\SavingGroup_LoanManagement.exe`.

> A prebuilt exe is also shipped inside `dist\` for convenience.

### First Run

- Login with **`admin` / `admin123`**, then **Settings → Change Password immediately**.
- Import existing members: Settings → Import Members.

## Tech Stack

| Layer        | Technology                                     |
| ------------ | ---------------------------------------------- |
| Language     | Python 3.10+                                   |
| GUI          | CustomTkinter ≥ 5.2.0                          |
| Database     | SQLite (stdlib, WAL mode)                      |
| Excel        | openpyxl (export/import)                       |
| Build        | PyInstaller (onefile, via `BUILD_EXE.bat`)     |

## Project Structure

```
├── app.py                # entry point: LoginWindow + MainApp (sidebar UI)
├── db.py                 # schema + data access
├── services.py           # business logic (loans, interest, statements)
├── ui_tables.py          # editable tree tables
├── views_statement.py    # quarterly statement engine
├── BUILD_EXE.bat         # one-click PyInstaller build
├── *.spec                # PyInstaller specs
└── data/saving_group.db  # runtime database (back this up!)
```

## Database & Backup

Everything lives in one SQLite file: `saving_group.db` (in the same folder as
the app).

- **Back it up regularly** — copy it to USB or Google Drive.
- The app runs **completely offline** — no network needed.

## Security

- Passwords stored as salted PBKDF2-SHA256 hashes (never plain text)
- Legacy SHA-256 fallback for older accounts
- Foreign-key constraints prevent orphaned data
- Full audit log with timestamp + username
- DB integrity check on startup

## License

See the LICENSE file in this repository.