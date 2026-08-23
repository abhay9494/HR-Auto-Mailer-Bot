import os, re, time, random, json, smtplib, imaplib, email
from io import BytesIO
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import gspread
import requests
import PyPDF2
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

load_dotenv()

# --- Load Environment Variables ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SHEET_URL = os.getenv("GOOGLE_SHEET_URL")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS")
SENDER_ACCOUNTS = [acc.split(",") for acc in os.getenv("SENDER_ACCOUNTS").split("|") if acc]
RESUME_FOLDER_LINK = os.getenv("RESUME_FOLDER_LINK")

with open('config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)
with open('content.json', 'r', encoding='utf-8') as f:
    content = json.load(f)

DISPLAY_NAME = config.get("DISPLAY_NAME", "Abhay Prasad")
DELIVERY_METHOD = config.get("DELIVERY_METHOD", "ATTACHMENT")
DRIVE_LINK = config.get("DRIVE_LINK", "")
DRY_RUN = config.get("DRY_RUN", False)

def send_telegram_message(text, silent=True):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML", "disable_notification": silent})
    except: pass

# --- Telegram Polling Engine ---
def process_telegram_commands(bot_sheet):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    try:
        last_update_id = bot_sheet.acell('F2').value
        params = {"offset": int(last_update_id) + 1} if last_update_id else {}
        response = requests.get(url, params=params).json()
        
        if not response.get("ok") or not response["result"]: return
        
        highest_id = 0
        for item in response["result"]:
            highest_id = max(highest_id, item["update_id"])
            msg_text = item.get("message", {}).get("text", "").lower()
            
            if msg_text.startswith("/help"):
                help_text = (
                    "🛠️ <b>Bot Commands</b>\n"
                    "<code>/status</code> : View active limits & cooldowns\n"
                    "<code>/cooldown [email|all]</code> : Stop sending for 48h\n"
                    "<code>/volume [email|all] [num]</code> : Set daily limit"
                )
                send_telegram_message(help_text, silent=False)
                
            elif msg_text.startswith("/cooldown"):
                parts = msg_text.split()
                if len(parts) == 2:
                    target = parts[1]
                    cooldown_time = (datetime.now(timezone.utc) + timedelta(hours=48)).strftime('%Y-%m-%d %H:%M:%S')
                    records = bot_sheet.get_all_records()
                    for i, row in enumerate(records, start=2):
                        if target == "all" or row['Account Email'] == target:
                            bot_sheet.update_cell(i, 3, cooldown_time)
                    send_telegram_message(f"✅ Cooldown applied to {target} for 48 hours.", silent=False)
                    
            elif msg_text.startswith("/volume"):
                parts = msg_text.split()
                if len(parts) == 3:
                    target, vol = parts[1], parts[2]
                    records = bot_sheet.get_all_records()
                    for i, row in enumerate(records, start=2):
                        if target == "all" or row['Account Email'] == target:
                            bot_sheet.update_cell(i, 2, vol)
                    send_telegram_message(f"✅ Volume for {target} set to {vol}/day.", silent=False)
                    
            elif msg_text.startswith("/status"):
                records = bot_sheet.get_all_records()
                stat_msg = "📊 <b>Current Bot Status</b>\n\n"
                for r in records:
                    stat_msg += f"📧 {r['Account Email']}\n└ Vol: {r['Volume Limit']} | CD: {r['Cooldown Until (UTC)'] or 'None'}\n\n"
                send_telegram_message(stat_msg, silent=False)
                
        if highest_id > 0: bot_sheet.update_acell('F2', highest_id)
    except Exception as e: pass

# --- Spintax Engine ---
def generate_spintax_email():
    subject = random.choice(content['subjects'])
    body_paragraphs = [
        random.choice(content['greetings']),
        random.choice(content['intros']),
        random.choice(content['education'])
    ]
    
    selected_projects = random.sample(content['projects'], random.randint(1, 2))
    proj_html = "<ul>" + "".join([f"<li>{p}</li>" for p in selected_projects]) + "</ul>"
    body_paragraphs.append(f"A few relevant projects I've built: {proj_html}")
    
    if DELIVERY_METHOD == "LINK":
        safe_link = f"{DRIVE_LINK}{'&' if '?' in DRIVE_LINK else '?'}trk={random.randint(100000, 999999)}"
        body_paragraphs.append(f"You can review my full resume here: <a href='{safe_link}'>View Resume</a>")
    else:
        body_paragraphs.append("I have attached my resume for your review.")
        
    body_paragraphs.append(random.choice(content['signoffs']) + f"<br>{DISPLAY_NAME}")
    
    html_body = "".join([f"<p>{p}</p>" for p in body_paragraphs])
    return subject, html_body

# --- PDF Hash Randomizer ---
def get_randomized_pdf(creds):
    folder_id_match = re.search(r'/folders/([a-zA-Z0-9_-]+)', RESUME_FOLDER_LINK)
    if not folder_id_match:
        raise Exception("Invalid Google Drive Folder Link in environment variables.")
    folder_id = folder_id_match.group(1)
    
    drive_service = build('drive', 'v3', credentials=creds)
    
    # 1. Search the specific folder for any PDF file
    query = f"'{folder_id}' in parents and mimeType='application/pdf' and trashed=false"
    results = drive_service.files().list(q=query, fields="files(id, name)").execute()
    items = results.get('files', [])
    
    if not items:
        raise Exception("No PDF found in the specified Drive folder.")
    
    # Grab the ID of the first file found in the folder
    file_id = items[0]['id']
    
    # 2. Download the file directly into memory
    request = drive_service.files().get_media(fileId=file_id)
    downloaded_bytes = BytesIO()
    downloader = MediaIoBaseDownload(downloaded_bytes, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
        
    # 3. Inject the hash randomizer
    downloaded_bytes.seek(0)
    reader = PyPDF2.PdfReader(downloaded_bytes)
    writer = PyPDF2.PdfWriter()
    
    for page in reader.pages: 
        writer.add_page(page)
        
    writer.add_metadata({"/CustomHash": str(time.time())})
    pdf_bytes_out = BytesIO()
    writer.write(pdf_bytes_out)
    pdf_bytes_out.seek(0)
    
    return pdf_bytes_out

# --- IMAP Bounce Handler ---
def process_bounces(sheet1):
    bounce_regex = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    bounces_found = 0
    for email_addr, app_pass in SENDER_ACCOUNTS:
        try:
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(email_addr, app_pass)
            
            # Check both the primary Inbox and the Spam folder
            for folder in ["inbox", '"[Gmail]/Spam"']:
                try:
                    mail.select(folder)
                    
                    # Search for various bounce subjects AND senders (Unread only)
                    queries = [
                        '(UNSEEN SUBJECT "Delivery Status Notification")',
                        '(UNSEEN SUBJECT "Undeliverable")',
                        '(UNSEEN SUBJECT "Message blocked")',
                        '(UNSEEN FROM "Mail Delivery System")',
                        '(UNSEEN FROM "mailer-daemon")',
                        '(UNSEEN FROM "postmaster")'
                    ]
                    
                    all_message_nums = set()
                    for query in queries:
                        status, messages = mail.search(None, query)
                        if status == "OK" and messages[0]:
                            all_message_nums.update(messages[0].split())
                    
                    if all_message_nums:
                        for num in all_message_nums:
                            res, data = mail.fetch(num, "(RFC822)")
                            msg = email.message_from_bytes(data[0][1])
                            body = ""
                            if msg.is_multipart():
                                for part in msg.walk():
                                    if part.get_content_type() == "text/plain":
                                        body += part.get_payload(decode=True).decode(errors="ignore")
                            else:
                                body = msg.get_payload(decode=True).decode(errors="ignore")
                            
                            failed_emails = re.findall(bounce_regex, body)
                            for failed in failed_emails:
                                if failed.lower() != email_addr.lower():
                                    cell = sheet1.find(failed)
                                    if cell:
                                        # Categorize the specific type of failure
                                        if "Delivery incomplete" in body or "temporary problem" in body.lower():
                                            sheet1.update_cell(cell.row, 4, "Delayed - Gmail Retrying")
                                        elif "Message blocked" in body or "blocked" in body.lower():
                                            sheet1.update_cell(cell.row, 4, "Blocked - Retrying")
                                        elif "inbox full" in body.lower():
                                            sheet1.update_cell(cell.row, 4, "Failed - Inbox Full")
                                        elif "message not delivered" in body.lower() or "timed out" in body.lower():
                                            sheet1.update_cell(cell.row, 4, "Failed - Server Timeout")
                                        else:
                                            sheet1.update_cell(cell.row, 4, "Failed - Bounced")
                                            
                                        bounces_found += 1
                                        time.sleep(1)
                            
                            # Mark as read only to preserve the bounce logs for manual review
                            mail.store(num, '+FLAGS', '\\Seen')
                except:
                    pass # Safely skip if the folder doesn't exist or is empty
            
            mail.logout()
        except: pass
    return bounces_found

# --- Core Execution ---
def main():
    # --- Micro-Delay: Sleep 1 to 14 minutes to randomize execution time daily ---
    delay_minutes = random.randint(1, 14)
    print(f"Applying micro-delay of {delay_minutes} minutes...")
    time.sleep(delay_minutes * 60)
    
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.readonly"
    ]
    creds = Credentials.from_service_account_info(json.loads(GOOGLE_CREDENTIALS_JSON), scopes=scopes)
    client = gspread.authorize(creds)
    sheet1 = client.open_by_url(SHEET_URL).sheet1
    
    try:
        bot_sheet = client.open_by_url(SHEET_URL).worksheet("Bot Settings")
    except gspread.WorksheetNotFound:
        bot_sheet = client.open_by_url(SHEET_URL).add_worksheet(title="Bot Settings", rows="50", cols="10")
        bot_sheet.update('A1:F1', [["Account Email", "Volume Limit", "Cooldown Until (UTC)", "", "Last Update ID", "0"]])
        default_data = [[acc[0], 400, ""] for acc in SENDER_ACCOUNTS]
        bot_sheet.update(f'A2:C{len(default_data)+1}', default_data)
        time.sleep(2)
        
    process_telegram_commands(bot_sheet)
    bounces = process_bounces(sheet1) if not DRY_RUN else 0
    
    bot_records = bot_sheet.get_all_records()
    active_senders = []
    for acc in SENDER_ACCOUNTS:
        record = next((r for r in bot_records if r['Account Email'] == acc[0]), None)
        if record:
            cooldown = record['Cooldown Until (UTC)']
            if cooldown:
                if datetime.now(timezone.utc) < datetime.strptime(cooldown, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc):
                    continue 
                else:
                    bot_sheet.update_cell(bot_records.index(record) + 2, 3, "") 
            active_senders.append({"creds": acc, "vol": int(record['Volume Limit'])})

    if not active_senders:
        send_telegram_message("🛑 <b>All accounts are currently on cooldown.</b> Batch skipped.")
        return

    total_emails_this_run = sum(s['vol'] for s in active_senders) // 12
    mode_tag = "🧪 DRY RUN" if DRY_RUN else "🚀 LIVE RUN"
    send_telegram_message(f"{mode_tag} <b>Started</b> | 🎯 Limit: {total_emails_this_run} | ♻️ Bounces: {bounces}")

    rows = sheet1.get_all_values()
    email_regex = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    
    # Calculate suffix for Dry Run tagging
    dr_suffix = " - DR" if DRY_RUN else ""
    
    # Build sent emails list (ignore "- DR" tags so we don't accidentally skip them during live mode)
    sent_emails = {re.findall(email_regex, r[2])[0] for r in rows[1:] if r[3].strip() == "Yes" and re.findall(email_regex, r[2])}

    emails_sent_this_run = 0
    account_index = 0
    
    for i, row in enumerate(rows):
        # HARD LOCK: If Dry Run is active, stop checking after row 6
        if DRY_RUN and i > 5:
            send_telegram_message("🏁 <b>Dry Run Test Complete.</b> Only processed rows 2 through 6.")
            break

        if emails_sent_this_run >= total_emails_this_run:
            next_time = (datetime.now(timezone.utc) + timedelta(hours=2)).astimezone(timezone(timedelta(hours=5, minutes=30))).strftime('%I:%M %p IST')
            send_telegram_message(f"⏸️ <b>Batch limit reached.</b> Next run at {next_time}.")
            break

        if i == 0: continue
        
        while len(row) < 4: row.append("")
        status = row[3].strip()
        
        # STATUS HANDLER: 
        if status != "":
            # If it's a LIVE RUN, and the row was marked with "- DR", process it anyway to overwrite it!
            if not DRY_RUN and status.endswith("- DR"):
                pass 
            # If it was marked as a temporary block, allow it through for a retry!
            elif status == "Blocked - Retrying":
                pass
            else:
                continue # Otherwise, skip this row entirely
        
        cell_data, row_num = row[2], i + 1
        emails = re.findall(email_regex, cell_data)

        if emails:
            target_email = emails[0]
            if target_email in sent_emails:
                try: sheet1.update_cell(row_num, 4, f"Skipped - Duplicate{dr_suffix}"); time.sleep(1)
                except: pass
                continue
                
            sender = active_senders[account_index]
            sender_email, app_pass = sender['creds']
            subj, body = generate_spintax_email()
            
            msg = MIMEMultipart()
            msg['From'] = f"{DISPLAY_NAME} <{sender_email}>"
            msg['To'] = target_email
            msg['Subject'] = subj
            msg.add_header('reply-to', SENDER_ACCOUNTS[0][0]) 
            msg.attach(MIMEText(body, 'html'))
            
            if DELIVERY_METHOD == "ATTACHMENT":
                pdf_bytes = get_randomized_pdf(creds)
                attach = MIMEApplication(pdf_bytes.read(), _subtype="pdf")
                attach.add_header('Content-Disposition', 'attachment', filename="Abhay_Prasad_Resume.pdf")
                msg.attach(attach)
                
            try:
                server = smtplib.SMTP('smtp.gmail.com', 587)
                server.starttls()
                server.login(sender_email, app_pass)
                server.send_message(msg)
                server.quit()
                
                # Only add to the deduplication memory if it's a live run
                if not DRY_RUN:
                    sent_emails.add(target_email)
                    
                emails_sent_this_run += 1
                sheet1.update_cell(row_num, 4, f"Yes{dr_suffix}")
                send_telegram_message(f"✅ Sent to: {target_email}\nFrom: {sender_email}\n(Mode: {'Live Test' if DRY_RUN else 'Live Campaign'})")
                
                if not DRY_RUN:
                    time.sleep(random.randint(6, 9))
                else:
                    time.sleep(4) 
                    
            except Exception as e:
                sheet1.update_cell(row_num, 4, f"Failed{dr_suffix}")
                send_telegram_message(f"❌ Failed ({sender_email} -> {target_email}): {str(e)}")
                
            account_index = (account_index + 1) % len(active_senders)

    # --- POST-SWEEP: Catch instant bounces immediately before sleeping ---
    if not DRY_RUN:
        post_bounces = process_bounces(sheet1)
        if post_bounces > 0:
            send_telegram_message(f"🧹 <b>Post-Sweep Cleanup</b> | Caught {post_bounces} instant bounces.")

if __name__ == "__main__":
    main()