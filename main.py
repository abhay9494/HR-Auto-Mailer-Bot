import os
import re
import time
import random
import smtplib
import gspread
import requests
import json
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

load_dotenv()

# --- Load Environment Variables ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SHEET_URL = os.getenv("GOOGLE_SHEET_URL")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS")
SENDER_ACCOUNTS = [acc.split(",") for acc in os.getenv("SENDER_ACCOUNTS").split("|") if acc]

# --- Load Generic Configurations ---
with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

DISPLAY_NAME = config.get("DISPLAY_NAME", "Abhay Prasad")
EMAIL_SUBJECT = config.get("EMAIL_SUBJECT", "Application for Intern Role")
RESUME_FILENAME = config.get("RESUME_FILENAME", "Abhay_Prasad_Resume.pdf")
DRY_RUN = config.get("DRY_RUN", False)

with open('email_template.html', 'r', encoding='utf-8') as f:
    HTML_TEMPLATE = f.read().replace("{DISPLAY_NAME}", DISPLAY_NAME)

# --- Smart Auto-Limits ---
ACTIVE_ACCOUNTS = len(SENDER_ACCOUNTS)
# Target: 100 emails per account/day. Divided by 12 GitHub runs/day.
MAX_EMAILS_PER_RUN = (ACTIVE_ACCOUNTS * 100) // 12

def send_telegram_message(text, silent=True):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_notification": silent # True = Silent, False = Buzzes phone
    }
    try:
        requests.post(url, json=payload)
    except Exception:
        pass

def generate_progress_bar(current, total, length=12):
    filled = int(length * current // total)
    bar = '█' * filled + '░' * (length - filled)
    return f"[{bar}]"

def get_next_run_timestamp():
    now_utc = datetime.now(timezone.utc)
    ist_tz = timezone(timedelta(hours=5, minutes=30))
    next_run_hour = (now_utc.hour + 2) % 24
    days_to_add = 1 if next_run_hour < now_utc.hour else 0
    next_run_utc = now_utc.replace(hour=next_run_hour, minute=0, second=0, microsecond=0) + timedelta(days=days_to_add)
    return next_run_utc.astimezone(ist_tz).strftime('%I:%M %p IST')

def send_email(sender_email, app_password, recipient_email):
    msg = MIMEMultipart()
    msg['From'] = f"{DISPLAY_NAME} <{sender_email}>"
    msg['To'] = recipient_email
    msg['Subject'] = EMAIL_SUBJECT
    
    msg.attach(MIMEText(HTML_TEMPLATE, 'html'))
    
    with open(RESUME_FILENAME, "rb") as f:
        attach = MIMEApplication(f.read(), _subtype="pdf")
        attach.add_header('Content-Disposition', 'attachment', filename=RESUME_FILENAME)
        msg.attach(attach)

    if not DRY_RUN:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, app_password)
        server.send_message(msg)
        server.quit()

def main():
    now_utc = datetime.now(timezone.utc)
    ist_tz = timezone(timedelta(hours=5, minutes=30))
    today_ist = now_utc.astimezone(ist_tz).strftime('%Y-%m-%d')
    is_last_run = (now_utc.hour == 18) # 18:00 UTC = 23:30 IST
    
    mode_text = "🧪 DRY RUN MODE" if DRY_RUN else "🚀 LIVE MODE"
    send_telegram_message(f"🤖 <b>GitHub Actions Started</b> | {mode_text}\nSmart Limit: {MAX_EMAILS_PER_RUN} emails.")
    
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_url(SHEET_URL).sheet1
    
    rows = sheet.get_all_values()
    email_regex = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    
    # --- Deduplication Engine ---
    sent_emails = set()
    for i, row in enumerate(rows):
        if i == 0: continue
        while len(row) < 4: row.append("")
        if row[3].strip() == "Yes":
            sent_emails.update(re.findall(email_regex, row[2]))

    account_index = 0
    emails_sent_this_run = 0
    phones_found_today = []

    for i, row in enumerate(rows[:4]):
        if emails_sent_this_run >= MAX_EMAILS_PER_RUN:
            next_time = get_next_run_timestamp()
            send_telegram_message(f"⏸️ <b>Batch limit of {MAX_EMAILS_PER_RUN} reached.</b>\nThe next batch will start at exactly {next_time}.")
            break

        if i == 0: continue
        
        status = row[3].strip()
        
        # Collect existing phones for end-of-day wrap-up
        if f"Phone Logged: {today_ist}" in status:
            clean = re.sub(r'[^\d+]', ' ', row[2])
            phones_found_today.extend([p for p in clean.split() if 10 <= len(re.sub(r'\D', '', p)) <= 15])
            continue
            
        if status != "": 
            continue 
            
        cell_data = row[2]
        row_num = i + 1
        
        # 1. Extract Emails
        emails = re.findall(email_regex, cell_data)
        
        # 2. Extract Phones
        text_without_emails = re.sub(email_regex, ' ', cell_data)
        clean_text = re.sub(r'[^\d+]', ' ', text_without_emails)
        phones = [p for p in clean_text.split() if 10 <= len(re.sub(r'\D', '', p)) <= 15]

        # 3. Action Logic
        if emails:
            # Deduplication Check
            if any(e in sent_emails for e in emails):
                try:
                    sheet.update_cell(row_num, 4, "Skipped - Duplicate")
                    time.sleep(1.5)
                except: pass
                continue
            
            all_successful = True
            for target_email in emails:
                if emails_sent_this_run >= MAX_EMAILS_PER_RUN:
                    break
                    
                sender_email, app_pass = SENDER_ACCOUNTS[account_index]
                try:
                    send_email(sender_email, app_pass, target_email)
                    emails_sent_this_run += 1
                    sent_emails.add(target_email)
                    
                    p_bar = generate_progress_bar(emails_sent_this_run, MAX_EMAILS_PER_RUN)
                    send_telegram_message(f"✅ <b>Sent to:</b> {target_email}\n<b>From:</b> {sender_email}\n<b>Progress:</b> {p_bar} {emails_sent_this_run}/{MAX_EMAILS_PER_RUN}")
                    
                    if not DRY_RUN: time.sleep(random.randint(6, 9))
                except Exception as e:
                    send_telegram_message(f"❌ Failed to send to {target_email}: {str(e)}")
                    all_successful = False
                
                account_index = (account_index + 1) % len(SENDER_ACCOUNTS)
            
            try:
                if all_successful:
                    sheet.update_cell(row_num, 4, "Yes")
                else:
                    sheet.update_cell(row_num, 4, "Failed")
                time.sleep(1.5) 
            except Exception: pass

        elif phones:
            phones_str = ", ".join(phones)
            phones_found_today.extend(phones)
            # Silent=False buzzes your phone specifically for this
            send_telegram_message(f"📞 <b>#PHONE_NUMBER DETECTED</b>\n<b>Number:</b> {phones_str}\n<b>Data:</b> {row[0]} | {row[1]}", silent=False)
            try:
                sheet.update_cell(row_num, 4, f"Phone Logged: {today_ist}")
                time.sleep(1.5) 
            except Exception: pass
                
        else:
            try:
                sheet.update_cell(row_num, 4, "Invalid/Empty")
                time.sleep(1.5) 
            except Exception: pass

    # --- End of Day Forecasting & Phone Book ---
    if is_last_run:
        blank_rows = sum(1 for r in rows[1:] if len(r) < 4 or r[3].strip() == "")
        daily_capacity = ACTIVE_ACCOUNTS * 100
        days_left = max(1, blank_rows // daily_capacity)
        
        phone_book = "\n".join(phones_found_today) if phones_found_today else "No numbers found today."
        
        wrap_up = (
            f"📈 <b>DAILY WRAP-UP</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<b>Rows Remaining:</b> {blank_rows}\n"
            f"<b>Estimated Time Left:</b> {days_left} Days\n\n"
            f"📓 <b>Today's Phone Book:</b>\n{phone_book}"
        )
        send_telegram_message(wrap_up, silent=False)

if __name__ == "__main__":
    main()