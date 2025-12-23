"""Test script to check email attachments detection."""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from gmail_receiver import GmailReceiver

def test():
    r = GmailReceiver()
    r.connect()
    
    print("\n📧 3 derniers emails:")
    print("-" * 50)
    
    emails = r.get_recent_emails(count=3)
    for i, e in enumerate(emails, 1):
        print(f"\n{i}. Sujet: {e['subject'][:50]}")
        print(f"   De: {e['from']}")
        print(f"   Attachments: {e['attachments']}")
        
        # Try to download attachments
        if e['attachments']:
            print("   📎 Téléchargement des pièces jointes...")
            downloaded = r.download_attachments(e['id'], save_dir="attachments")
            print(f"   ✅ Téléchargés: {downloaded}")
    
    r.disconnect()

if __name__ == "__main__":
    test()
