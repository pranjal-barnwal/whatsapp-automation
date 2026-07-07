# WhatsApp Automation

Send personalized WhatsApp messages to your clients (e.g. ITR / filing
reminders) from an Excel sheet. Messages support mixed **Hindi + English** and
are automated through **WhatsApp Web** using Selenium.

Works on both **Windows** and **macOS**.

---

## How it works

1. Reads clients from `data/Clients.xlsx` (row 1 = header and is skipped;
   column 1 = **name**, column 2 = **phone number** without country code).
2. Renders `message.txt`, replacing `{NAME}` (and any other `{COLUMN}`
   placeholder) with each client's data.
3. Opens WhatsApp Web in Chrome, pre-fills each chat, and sends — with a
   randomized delay between messages.
4. Writes a per-client report to `logs/`.

Phone numbers are automatically cleaned (spaces, dashes, leading `0`/`+`) and
prefixed with the `+91` country code.

---

## Project layout

```
main.py                          # launcher: python main.py [options]
message.txt                      # editable message template ({NAME} etc.)
requirements.txt
data/Clients.xlsx                # your client list (git-ignored)
src/                             # the app package
├── config.py                    # all tweakable settings
├── cli.py                       # command-line interface + orchestration
├── clients/                     # reading the recipient list
│   ├── models.py                #   Client / SkippedRow data classes
│   ├── phone.py                 #   phone cleaning + +91 validation
│   └── loader.py                #   read Excel, stop at first empty row
├── messaging/
│   └── templating.py            # render message + build WhatsApp links
├── sending/                     # WhatsApp Web automation
│   ├── selectors.py             #   WhatsApp Web XPaths (edit here if UI changes)
│   └── sender.py                #   Selenium sender + throttle
└── reporting/
    └── report.py                # per-run CSV report + resume lookup
```

---

## Prerequisites

- **Python 3.10+** — <https://www.python.org/downloads/>
- **Google Chrome** installed (the matching driver is downloaded automatically).
- A phone with WhatsApp, to scan the QR code once.

---

## Setup

```bash
# 1. (Recommended) create a virtual environment
python -m venv .venv

# macOS / Linux
source .venv/bin/activate
# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt
```

---

## Prepare your data

- Put your Excel file at `data/Clients.xlsx`.
  - **Row 1**: headings (skipped).
  - **Column 1**: client name.
  - **Column 2**: 10-digit mobile number (no country code).
  - Any other columns are ignored.
  - Reading **stops at the first empty row**, so the first blank line marks the
    end of your client list.
- Edit `message.txt` to change the message. Use `{NAME}` where the client's
  name should appear. You can also reference any other column by its header in
  braces, e.g. `{DUE DATE}`. Example:

  ```
  Hi {NAME}
  Your ITR date is near.
  Please revert back, so that we can help you with your filing.
  ```

---

## Usage

**Always preview first** (no browser, nothing is sent):

```bash
python main.py --dry-run
```

**Live test to yourself** — put your own number as the first row, then:

```bash
python main.py --limit 1
```

The first time, a Chrome window opens WhatsApp Web — **scan the QR code** with
your phone. Your login is saved in `.wa_profile/`, so you won't need to scan
again on later runs.

**Full run:**

```bash
python main.py
```

**Resume** (skip anyone already sent in a previous run):

```bash
python main.py --resume
```

### Options

| Flag | Description |
| --- | --- |
| `--dry-run` | Preview messages/links without opening a browser. |
| `--limit N` | Only process the first N clients (great for testing). |
| `--resume` | Skip numbers already marked `sent` in previous reports. |
| `--data PATH` | Use a different Excel file. |
| `--template PATH` | Use a different message template. |
| `--min-delay` / `--max-delay` | Seconds to wait between messages (default 8–20). |
| `--yes` | Skip the confirmation prompt. |

---

## Reports

Every run writes a CSV to `logs/report-YYYYmmdd-HHMMSS.csv` with the status
(`sent`, `invalid`, `failed`) for each client. These files are git-ignored.

---

## Important notes

- **Client data is private.** `data/*.xlsx` and `logs/` are git-ignored so
  phone numbers are never committed. Keep it that way.
- **Use responsibly.** Automated/bulk messaging can violate WhatsApp's Terms of
  Service and, if abused, may get your number restricted. Only message clients
  who expect to hear from you, keep volumes reasonable, and keep the delay
  between messages. The default throttle exists for this reason.
- If sends start failing after a WhatsApp Web update, the UI selectors in
  `src/sending/selectors.py` may need a small update.
