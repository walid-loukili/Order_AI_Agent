"""
Gmail Email Receiver Module
Uses IMAP to connect to Gmail and fetch emails.
"""

import imaplib
import email
from email.header import decode_header
import os
import sys
from dotenv import load_dotenv
from datetime import datetime

# Fix Windows console encoding
sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

class GmailReceiver:
    def __init__(self):
        self.email_address = os.getenv("GMAIL_EMAIL")
        self.app_password = os.getenv("GMAIL_APP_PASSWORD")
        self.imap_server = "imap.gmail.com"
        self.imap_port = 993
        self.connection = None
    
    def connect(self):
        """Establish connection to Gmail IMAP server."""
        try:
            self.connection = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            self.connection.login(self.email_address, self.app_password)
            print(f"✅ Connexion réussie à {self.email_address}")
            return True
        except imaplib.IMAP4.error as e:
            print(f"❌ Erreur de connexion IMAP: {e}")
            return False
        except Exception as e:
            print(f"❌ Erreur inattendue: {e}")
            return False
    
    def disconnect(self):
        """Close the IMAP connection."""
        if self.connection:
            try:
                self.connection.logout()
                print("📤 Déconnexion réussie")
            except:
                pass
    
    def get_recent_emails(self, folder="INBOX", count=5):
        """Fetch the most recent emails from specified folder."""
        if not self.connection:
            print("❌ Non connecté. Appelez connect() d'abord.")
            return []
        
        try:
            self.connection.select(folder)
            
            # Search for all emails
            status, messages = self.connection.search(None, "ALL")
            
            if status != "OK":
                print("❌ Erreur lors de la recherche des emails")
                return []
            
            email_ids = messages[0].split()
            
            if not email_ids:
                print("📭 Aucun email trouvé dans la boîte de réception")
                return []
            
            # Get the last 'count' emails
            recent_ids = email_ids[-count:] if len(email_ids) >= count else email_ids
            recent_ids = recent_ids[::-1]  # Reverse to get newest first
            
            emails = []
            for email_id in recent_ids:
                email_data = self._fetch_email(email_id)
                if email_data:
                    emails.append(email_data)
            
            return emails
            
        except Exception as e:
            print(f"❌ Erreur lors de la récupération des emails: {e}")
            return []
    
    def _fetch_email(self, email_id):
        """Fetch a single email by ID."""
        try:
            status, msg_data = self.connection.fetch(email_id, "(RFC822)")
            
            if status != "OK":
                return None
            
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    # Decode subject
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding or "utf-8")
                    
                    # Decode sender
                    from_header = msg.get("From", "")
                    sender, encoding = decode_header(from_header)[0]
                    if isinstance(sender, bytes):
                        sender = sender.decode(encoding or "utf-8")
                    
                    # Get date
                    date = msg.get("Date", "")
                    
                    # Get body
                    body = self._get_email_body(msg)
                    
                    # Get attachments info
                    attachments = self._get_attachments_info(msg)
                    
                    return {
                        "id": email_id.decode(),
                        "subject": subject,
                        "from": sender,
                        "date": date,
                        "body": body,
                        "attachments": attachments
                    }
            
            return None
            
        except Exception as e:
            print(f"❌ Erreur lors de la lecture de l'email {email_id}: {e}")
            return None
    
    def _get_email_body(self, msg):
        """Extract the email body (text content)."""
        body = ""
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                
                if content_type == "text/plain" and "attachment" not in content_disposition:
                    try:
                        body = part.get_payload(decode=True).decode()
                        break
                    except:
                        pass
        else:
            try:
                body = msg.get_payload(decode=True).decode()
            except:
                pass
        
        return body
    
    def _get_attachments_info(self, msg):
        """Get list of attachment filenames."""
        attachments = []
        
        if msg.is_multipart():
            for part in msg.walk():
                content_disposition = str(part.get("Content-Disposition"))
                
                if "attachment" in content_disposition:
                    filename = part.get_filename()
                    if filename:
                        filename, encoding = decode_header(filename)[0]
                        if isinstance(filename, bytes):
                            filename = filename.decode(encoding or "utf-8")
                        attachments.append(filename)
        
        return attachments
    
    def download_attachments(self, email_id, save_dir="attachments"):
        """Download all attachments from an email."""
        if not self.connection:
            print("❌ Non connecté. Appelez connect() d'abord.")
            return []
        
        os.makedirs(save_dir, exist_ok=True)
        downloaded = []
        
        try:
            self.connection.select("INBOX")
            status, msg_data = self.connection.fetch(email_id.encode() if isinstance(email_id, str) else email_id, "(RFC822)")
            
            if status != "OK":
                return []
            
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_disposition = str(part.get("Content-Disposition"))
                            
                            if "attachment" in content_disposition:
                                filename = part.get_filename()
                                if filename:
                                    filename, encoding = decode_header(filename)[0]
                                    if isinstance(filename, bytes):
                                        filename = filename.decode(encoding or "utf-8")
                                    
                                    filepath = os.path.join(save_dir, filename)
                                    with open(filepath, "wb") as f:
                                        f.write(part.get_payload(decode=True))
                                    
                                    downloaded.append(filepath)
                                    print(f"   📥 Téléchargé: {filename}")
            
            return downloaded
            
        except Exception as e:
            print(f"❌ Erreur lors du téléchargement: {e}")
            return []
    
    def check_for_new_emails(self, since_date=None):
        """Check for unread/new emails."""
        if not self.connection:
            print("❌ Non connecté. Appelez connect() d'abord.")
            return []
        
        try:
            self.connection.select("INBOX")
            
            # Search for unseen emails
            status, messages = self.connection.search(None, "UNSEEN")
            
            if status != "OK":
                return []
            
            email_ids = messages[0].split()
            
            if not email_ids:
                print("📭 Aucun nouveau email non lu")
                return []
            
            print(f"📬 {len(email_ids)} nouveau(x) email(s) trouvé(s)")
            
            emails = []
            for email_id in email_ids:
                email_data = self._fetch_email(email_id)
                if email_data:
                    emails.append(email_data)
            
            return emails
            
        except Exception as e:
            print(f"❌ Erreur lors de la vérification des nouveaux emails: {e}")
            return []


def main():
    """Test the Gmail receiver."""
    print("=" * 50)
    print("🚀 Test de réception des emails Gmail")
    print("=" * 50)
    
    receiver = GmailReceiver()
    
    # Connect to Gmail
    if not receiver.connect():
        print("Échec de la connexion. Vérifiez vos identifiants.")
        return
    
    print("\n" + "-" * 50)
    print("📥 Récupération des 5 derniers emails...")
    print("-" * 50)
    
    emails = receiver.get_recent_emails(count=5)
    
    if emails:
        for i, email_data in enumerate(emails, 1):
            print(f"\n📧 Email {i}:")
            print(f"   📌 Sujet: {email_data['subject']}")
            print(f"   👤 De: {email_data['from']}")
            print(f"   📅 Date: {email_data['date']}")
            if email_data['attachments']:
                print(f"   📎 Pièces jointes: {', '.join(email_data['attachments'])}")
            print(f"   📝 Aperçu: {email_data['body'][:100]}..." if len(email_data['body']) > 100 else f"   📝 Contenu: {email_data['body']}")
    else:
        print("Aucun email récupéré.")
    
    print("\n" + "-" * 50)
    print("📬 Vérification des emails non lus...")
    print("-" * 50)
    
    new_emails = receiver.check_for_new_emails()
    
    if new_emails:
        print(f"✅ {len(new_emails)} email(s) non lu(s) détecté(s)")
        for email_data in new_emails:
            print(f"   - {email_data['subject']} (de: {email_data['from']})")
    
    receiver.disconnect()
    
    print("\n" + "=" * 50)
    print("✅ Test terminé avec succès!")
    print("=" * 50)


if __name__ == "__main__":
    main()
