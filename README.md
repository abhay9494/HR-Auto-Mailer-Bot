<div align="center">

# 🚀 HR-Auto-Mailer-Bot

### The Beginner-Friendly, Automated Cold Email Engine

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg?style=for-the-badge&logo=python&logoColor=white)](#)
[![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-2088FF?style=for-the-badge&logo=github-actions&logoColor=white)](#)
[![Google Sheets](https://img.shields.io/badge/Google_Sheets-34A853?style=for-the-badge&logo=google-sheets&logoColor=white)](#)
[![Telegram](https://img.shields.io/badge/Telegram-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)](#)

<p align="center">
  <i>A lightweight job-outreach automation bot that reads recruiter contacts from Google Sheets, sends personalized cold emails, tracks delivery status, and can be remotely controlled through Telegram.</i>
</p>

</div>

---

## ✨ What This Project Does

**HR-Auto-Mailer-Bot** automates repetitive job-outreach tasks while keeping the workflow organized and remotely manageable.

> ⚠️ **Important:** Email providers have sending limits and anti-spam systems. Do not use this project to send unsolicited bulk email, evade spam detection, or violate the terms of Gmail, GitHub, Telegram, or any other service. Use conservative volumes, contact relevant recipients, and follow applicable laws and service policies.

### Core Features

| Feature | What it does |
|---|---|
| 🧠 **Google Sheets tracking** | Reads recruiter/company data and records outreach status. |
| ✉️ **Personalized templates** | Rotates greetings, subjects, and content variations. |
| 📎 **Resume attachment** | Attaches your PDF resume to outgoing emails. |
| 🧹 **Bounce handling** | Checks the mailbox for delivery-failure messages and updates your sheet. |
| 📱 **Telegram control** | Lets you check status, pause sending, and adjust volume remotely. |
| ☁️ **GitHub Actions** | Runs the workflow automatically on a schedule without keeping your laptop on. |

---

## 📖 Table of Contents

1. [How It Works](#-how-it-works)
2. [Project Structure](#-project-structure)
3. [Prerequisites](#-prerequisites)
   - [Gmail App Password](#a-gmail-app-password)
   - [Telegram Bot Token](#b-telegram-bot-token)
   - [Google Sheets Service Account](#c-google-sheets-service-account)
4. [Google Sheet Setup](#-google-sheet-setup)
5. [Local Installation](#-local-installation)
6. [Environment Variables](#-environment-variables)
7. [Bot Configuration](#-bot-configuration)
8. [Content & Resume Setup](#-content--resume-setup)
9. [Testing Safely](#-testing-safely)
10. [Run Automatically with GitHub Actions](#-run-automatically-with-github-actions)
11. [Telegram Commands](#-telegram-commands)
12. [Security Checklist](#-security-checklist)
13. [Troubleshooting](#-troubleshooting)

---

## 🔄 How It Works

The workflow is intentionally simple:

```text
┌───────────────────────┐
│   Google Sheet        │
│ Company / Name /      │
│ Email / Status        │
└──────────┬────────────┘
           │
           ▼
┌───────────────────────┐
│   HR Mailer Bot       │
│ Template + Config     │
└──────────┬────────────┘
           │
      ┌────┴─────┐
      ▼          ▼
   Gmail       Telegram
      │          │
      │      Remote control
      ▼
   Outreach
      │
      ▼
┌───────────────────────┐
│ Update Google Sheet   │
│ sent / failed / etc.  │
└───────────────────────┘
```

### In plain English

- **The source of truth:** Google Sheets stores your recruiter/company list and status.
- **The mailer:** The script generates emails from your configured content variations.
- **The attachment:** Your PDF resume can be included with each email.
- **The tracker:** The bot updates the Google Sheet after processing contacts.
- **The remote control:** Telegram commands let you inspect or change the bot's operating state.
- **The scheduler:** GitHub Actions can wake the workflow on a schedule.

---

## 🗂️ Project Structure

A typical repository can look like this:

```text
HR-Auto-Mailer-Bot/
├── .github/
│   └── workflows/
│       └── hr-mailer.yml
├── main.py
├── config.json
├── content.json
├── requirements.txt
├── resume.pdf
├── .env                  # local only — DO NOT COMMIT
├── credentials.json      # local only — DO NOT COMMIT
└── README.md
```

> 🔐 Add `.env` and `credentials.json` to `.gitignore` before pushing the repository.

Example `.gitignore`:

```gitignore
.env
credentials.json
__pycache__/
*.pyc
```

---

# 🧰 Prerequisites

Before touching the code, prepare access for the three services used by the project:

- **Gmail** — sending mail
- **Telegram** — remote control
- **Google Sheets** — contact/status tracking

---

## A. Gmail App Password

You should **not** put your normal Gmail password into the project. Use a Google **App Password** for a Gmail account with 2-Step Verification enabled.

### Steps

1. Open [Google Account](https://myaccount.google.com/).
2. Go to **Security**.
3. Make sure **2-Step Verification** is enabled.
4. Find **App Passwords**.
5. Create an app password for the mailer (for example, `HR Bot`).
6. Save the generated 16-character password somewhere secure.

For multiple sending accounts, create an appropriate app password for each account.

> 💡 **Tip:** Never commit app passwords to Git. Store them in environment variables or GitHub Actions secrets.

---

## B. Telegram Bot Token

Telegram provides a simple way to monitor and control the automation from your phone.

### Create the bot

1. Open Telegram and search for **[@BotFather](https://t.me/BotFather)**.
2. Send `/newbot`.
3. Choose a display name and unique username.
4. BotFather will provide an **HTTP API token**.
5. Store that token securely.

### Find your Chat ID

1. Search for **@userinfobot** in Telegram.
2. Start the bot.
3. Copy the numeric **ID** it provides.

You will use both values in your environment configuration.

---

## C. Google Sheets Service Account

The bot needs a service account with permission to edit your spreadsheet.

### Create the credentials

1. Open [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project.
3. Go to **APIs & Services → Library**.
4. Search for **Google Sheets API** and enable it.
5. Go to **APIs & Services → Credentials**.
6. Choose **Create Credentials → Service Account**.
7. Give it a descriptive name such as `sheet-editor`.
8. Open the new service account.
9. Go to **Keys → Add Key → Create new key**.
10. Select **JSON** and download the credentials file.

The downloaded file is typically named:

```text
credentials.json
```

### Share the spreadsheet with the service account

Open `credentials.json` and find the `client_email` value. It will look similar to:

```text
sheet-editor@your-project.iam.gserviceaccount.com
```

Share your Google Sheet with that email address and give it **Editor** permission.

---

# 📊 Google Sheet Setup

Create a new Google Sheet and use these exact headers in row 1:

| Column | Header |
|---|---|
| A | `Company` |
| B | `Name` |
| C | `Email` |
| D | `Status` |

Example:

| Company | Name | Email | Status |
|---|---|---|---|
| Example Labs | Alex Sharma | alex@example.com | Pending |
| Acme Tech | Priya Singh | priya@example.com | Pending |

> ✅ Keep the header names exactly as expected by your code.

---

# 💻 Local Installation

## 1. Clone the repository

```bash
git clone https://github.com/yourusername/HR-Auto-Mailer-Bot.git
cd HR-Auto-Mailer-Bot
```

## 2. Install dependencies

Make sure Python 3.8+ is installed, then run:

```bash
pip install -r requirements.txt
```

### Optional: use a virtual environment

```bash
python -m venv .venv
```

Activate it:

**Windows**

```powershell
.venv\Scripts\activate
```

**macOS / Linux**

```bash
source .venv/bin/activate
```

Then install dependencies:

```bash
pip install -r requirements.txt
```

---

# 🔐 Environment Variables

Create a file named `.env` in the project root.

```env
TELEGRAM_BOT_TOKEN=paste_your_botfather_token_here
TELEGRAM_CHAT_ID=paste_your_userinfobot_id_here
GOOGLE_SHEET_URL=paste_the_full_url_of_your_google_sheet_here
GOOGLE_CREDENTIALS={"type":"service_account", "project_id":"your-project-id", ...}

# Format:
# email@gmail.com,app_password|email2@gmail.com,app_password
SENDER_ACCOUNTS=your.email@gmail.com,abcdefghijklmnop
```

---

# ⚙️ Bot Configuration

Open `config.json` and set your personal configuration.

```json
{
  "DISPLAY_NAME": "Your Name",
  "DELIVERY_METHOD": "ATTACHMENT",
  "DRY_RUN": true
}
```

### Configuration reference

| Key | Description |
|---|---|
| `DISPLAY_NAME` | Name used in generated emails. |
| `DELIVERY_METHOD` | Determines how the resume is delivered, based on your implementation. |
| `DRIVE_LINK` | Upload your Resume to Google Drive, Turn on Sharing for the Resume, Copy the Link and Paste it here |
| `DRY_RUN` | When `true`, prevents real sending if the code supports dry-run behavior. |

> 🧪 **Keep `DRY_RUN` set to `true` during your first test.** Verify the generated output, Sheet updates, and configuration before enabling real sending.

---

# ✍️ Content & Resume Setup

## `content.json`

Put your email content variations in `content.json`.

For example, you might maintain multiple versions of:

- Greetings
- Subject lines
- Opening paragraphs
- Relevant project highlights
- Closing lines

The exact JSON structure should match what `main.py` expects.

## Resume PDF

Place your PDF resume in the repository folder, for example:

```text
resume.pdf
```

Make sure the filename/path referenced by your code matches the actual file.

> 📎 Keep the resume filename simple and predictable to reduce path issues in local runs and GitHub Actions.

---

# 🧪 Testing Safely

Before enabling real email sending, test the entire pipeline in a controlled way.

### Recommended sequence

1. Set `DRY_RUN` to `true`.
2. Use a tiny test dataset in Google Sheets.
3. Confirm the service account can read and update the sheet.
4. Confirm your Gmail authentication works.
5. Confirm Telegram commands are recognized.
6. Inspect generated email content and attachment handling.
7. Review logs for errors.
8. Only then enable real delivery.

> 🚨 **Do not start with hundreds of contacts.** Validate the system with a small number of appropriate recipients first.

---

# ☁️ Run Automatically with GitHub Actions

You can run the bot from GitHub Actions so your local machine does not need to stay powered on.

## 1. Use a private repository

Upload the project to a **private** GitHub repository.

**Never commit:**

- `.env`
- `credentials.json`
- App passwords
- Telegram bot tokens
- Any other API credentials

## 2. Add repository secrets

Go to:

**Repository → Settings → Secrets and variables → Actions**

Create the secrets your workflow expects. With the configuration above, that may include:

```text
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
GOOGLE_SHEET_URL
GOOGLE_CREDENTIALS
SENDER_ACCOUNTS
```

> 🔒 GitHub Actions secrets are the preferred place for sensitive runtime values in a CI workflow.

## 3. Enable the workflow

Open the repository's **Actions** tab.

Select your workflow, such as **HR Mailer Automation**, and enable it if required.

## 4. Verify the schedule

If your workflow is configured to run every two hours, it will execute according to the schedule defined in your workflow YAML.

**Do not assume the schedule from this README alone.** Check `.github/workflows/*.yml` to confirm the actual `cron` configuration.

---

# 📱 Telegram Commands

The exact behavior depends on your implementation, but the intended commands described by this project are:

| Command | Purpose |
|---|---|
| `/help` | Shows available commands. |
| `/status` | Shows sender status and configured limits. |
| `/cooldown your.email@gmail.com` | Pauses a specific account for a defined cooldown period. |
| `/cooldown all` | Pauses the campaign according to the bot's cooldown logic. |
| `/volume all 50` | Sets the configured daily volume to 50, if supported. |

### Example

```text
/status
```

Then, for a conservative volume setting:

```text
/volume all 50
```

> ⚠️ **Sending limits are implementation-specific.** Gmail and other providers may impose limits or temporarily restrict accounts. Keep volumes conservative and comply with provider policies.

---

# 🛡️ Security Checklist

Before pushing your code or enabling automation, confirm:

- [ ] `.env` is in `.gitignore`.
- [ ] `credentials.json` is in `.gitignore`.
- [ ] No passwords, tokens, or JSON credentials are hard-coded in source files.
- [ ] The GitHub repository is private.
- [ ] GitHub Actions secrets contain sensitive values instead of committed files.
- [ ] Your Telegram bot is not publicly advertised with sensitive operational commands.
- [ ] The Google service account has access only to the spreadsheets it actually needs.
- [ ] You have tested with `DRY_RUN=true` first.
- [ ] Your outreach process follows applicable email, privacy, and anti-spam requirements.

---

# 🛠️ Troubleshooting

## `Permission denied` on Google Sheets

Check that:

1. The **Google Sheets API** is enabled.
2. The service account email from `credentials.json` has **Editor** access to the sheet.
3. The `GOOGLE_SHEET_URL` is correct.
4. Your code is loading the intended credentials.

## Gmail authentication fails

Check that:

1. 2-Step Verification is enabled.
2. You are using a valid **App Password**, not your normal Gmail password.
3. The sender address matches the configured account.
4. The account has not been restricted or challenged by the provider.

## Telegram commands do not work

Check that:

1. The bot token is correct.
2. The Chat ID is correct.
3. You have started a conversation with the bot.
4. The polling/webhook behavior matches the implementation.
5. The workflow is actually running when commands are expected to be processed.

## GitHub Actions cannot find environment variables

Verify that the workflow maps repository secrets into the environment expected by your script, for example:

```yaml
env:
  TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
  TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
  GOOGLE_SHEET_URL: ${{ secrets.GOOGLE_SHEET_URL }}
  GOOGLE_CREDENTIALS: ${{ secrets.GOOGLE_CREDENTIALS }}
  SENDER_ACCOUNTS: ${{ secrets.SENDER_ACCOUNTS }}
```

The exact mapping should match your workflow and application code.

---

# ✅ Recommended First Run

For a clean first deployment:

```text
1. Create Gmail App Password
        ↓
2. Create Telegram bot + Chat ID
        ↓
3. Create Google service account
        ↓
4. Share Google Sheet with service account
        ↓
5. Clone repository
        ↓
6. Install requirements
        ↓
7. Create .env
        ↓
8. Configure config.json + content.json
        ↓
9. Add resume PDF
        ↓
10. Test with DRY_RUN=true
        ↓
11. Verify logs + Google Sheet
        ↓
12. Add GitHub Actions secrets
        ↓
13. Enable the workflow
```

---

# 🤝 Contributing

Suggestions, bug fixes, documentation improvements, and workflow enhancements are welcome.

When contributing:

- Keep credentials out of commits.
- Test changes locally before opening a pull request.
- Document configuration changes.
- Avoid increasing default sending volume without a clear reason.

---

<div align="center">

### 🚀 Automate the repetitive parts. Keep the outreach relevant.

**Built with Python · Google Sheets · Gmail · Telegram · GitHub Actions**

</div>
