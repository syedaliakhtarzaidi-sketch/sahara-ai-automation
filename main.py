import os
import time
import imaplib
import email
from email.header import decode_header
from supabase import create_client, Client
import google.generativeai as genai

# Fetching Credentials from Environment Variables
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASS = os.environ.get("EMAIL_PASS")
IMAP_SERVER = os.environ.get("IMAP_SERVER", "imap.saharaukfoods.co.uk")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GEMINI_API_KEY)

def extract_email_info(body):
    """Uses Gemini 1.5 Flash model to parse email metadata"""
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"""
    Analyze this email for Sahara UK Foods Ltd.
    Determine if it is 'BULK_PO' or 'SAMPLE_REQUEST'.
    Return formatted text:
    TYPE: [BULK_PO or SAMPLE_REQUEST]
    CLIENT: [Client Name]
    LEAD: [Mustafa, Roya, Aashir, or Kulsoom]
    REGION: [UK or EU]
    PRODUCTS: [Product details]
    
    Email Text:
    {body}
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Gemini AI Parsing Error: {e}")
        return ""

def start_listening():
    print("🚀 24/7 Sahara AI Agent Active & Listening on Cloud...")
    while True:
        try:
            mail = imaplib.IMAP4_SSL(IMAP_SERVER)
            mail.login(EMAIL_USER, EMAIL_PASS)
            mail.select("inbox")

            status, messages = mail.search(None, 'UNSEEN')
            email_ids = messages[0].split()

            for e_id in email_ids:
                res, msg_data = mail.fetch(e_id, '(RFC822)')
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    body = part.get_payload(decode=True).decode(errors='ignore')
                        else:
                            body = msg.get_payload(decode=True).decode(errors='ignore')

                        parsed = extract_email_info(body)

                        # Agent 1: Bulk PO Routing Logic
                        if "TYPE: BULK_PO" in parsed:
                            logistics_assignee = "Kulsoom" if "REGION: EU" in parsed else "Ali"
                            supabase.table("bulk_orders").insert({
                                "po_number": f"PO-{int(time.time())}",
                                "client_name": "New Client Order",
                                "lead_source": "Mustafa",
                                "execution_lead": "Terry",
                                "logistics_lead": logistics_assignee,
                                "current_stage": "Pending Docs",
                                "region": "EU" if "REGION: EU" in parsed else "UK"
                            }).execute()
                            print(f"✅ Bulk Order Logged -> Assigned to {logistics_assignee}")

                        # Agent 2: Sample Request Routing Logic
                        elif "TYPE: SAMPLE_REQUEST" in parsed:
                            dispatch_assignee = "Kulsoom" if "REGION: EU" in parsed else "Ghazanfar"
                            supabase.table("sample_dispatches").insert({
                                "sample_id": f"SMP-{int(time.time())}",
                                "client_name": "Sample Client",
                                "lead_source": "Aashir",
                                "dispatch_lead": dispatch_assignee,
                                "status": "Requested"
                            }).execute()
                            print(f"📦 Sample Logged -> Assigned to {dispatch_assignee}")

            mail.logout()
        except Exception as e:
            print(f"Polling check error: {e}")

        time.sleep(30)

if __name__ == "__main__":
    start_listening()
