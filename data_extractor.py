"""
Data Extractor Module
Uses OpenAI API to extract purchase order data from emails and attachments.
"""

import os
import sys
import base64
from dotenv import load_dotenv
from openai import OpenAI
import PyPDF2
from PIL import Image
import io

# Fix Windows console encoding
sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

# Product types for the company
PRODUCT_TYPES = [
    "Sachets fond plat",
    "Sac fond carré sans poignées",
    "Sac fond carré avec poignées plates",
    "Sac fond carré avec poignées torsadées"
]

class DataExtractor:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o"
    
    def extract_from_email(self, email_data, attachment_texts=None):
        """Extract purchase order data from email content and attachments."""
        
        # Build context from email
        email_content = f"""
SUJET: {email_data.get('subject', '')}
DE: {email_data.get('from', '')}
DATE: {email_data.get('date', '')}

CONTENU:
{email_data.get('body', '')}
"""
        
        # Add attachment content if available
        if attachment_texts:
            email_content += "\n\nCONTENU DES PIÈCES JOINTES:\n"
            for filename, text in attachment_texts.items():
                email_content += f"\n--- {filename} ---\n{text}\n"
        
        return self._extract_with_openai(email_content)
    
    def _extract_with_openai(self, content):
        """Use OpenAI to extract structured data from content."""
        
        prompt = f"""Tu es un assistant spécialisé dans l'extraction de données de bons de commande.

L'entreprise fabrique 4 types de produits d'emballage:
1. Sachets fond plat
2. Sac fond carré sans poignées
3. Sac fond carré avec poignées plates
4. Sac fond carré avec poignées torsadées

Analyse le contenu suivant et extrais les informations du bon de commande.
Retourne les données au format JSON avec les champs suivants:
- numero_commande: string (numéro du bon de commande)
- entreprise_cliente: string (nom de l'entreprise qui passe la commande)
- type_produit: string (un des 4 types listés ci-dessus, ou null si non identifiable)
- nature_produit: string (détails spécifiques du produit)
- quantite: number (quantité commandée)
- unite: string (unité de mesure: pièces, kg, etc.)
- date_commande: string (date du bon de commande)
- date_livraison: string (date de livraison souhaitée, si mentionnée)
- prix_unitaire: number (prix unitaire si mentionné)
- prix_total: number (prix total si mentionné)
- devise: string (EUR, MAD, USD, etc.)
- informations_supplementaires: string (autres informations pertinentes)
- confiance: number (niveau de confiance de 0 à 100)
- est_bon_commande: boolean (true si c'est bien un bon de commande)

Si une information n'est pas trouvée, utilise null.

CONTENU À ANALYSER:
{content}

Réponds UNIQUEMENT avec le JSON, sans texte additionnel."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Tu es un expert en extraction de données de documents commerciaux. Tu réponds uniquement en JSON valide."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1000
            )
            
            result = response.choices[0].message.content.strip()
            
            # Clean JSON if wrapped in markdown
            if result.startswith("```"):
                result = result.split("```")[1]
                if result.startswith("json"):
                    result = result[4:]
                result = result.strip()
            
            import json
            return json.loads(result)
            
        except Exception as e:
            print(f"❌ Erreur OpenAI: {e}")
            return None
    
    def extract_text_from_pdf(self, pdf_path):
        """Extract text content from a PDF file."""
        try:
            text = ""
            with open(pdf_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            print(f"❌ Erreur extraction PDF: {e}")
            return ""
    
    def extract_text_from_image(self, image_path):
        """Use OpenAI Vision to extract text from an image."""
        try:
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")
            
            # Determine image type
            ext = os.path.splitext(image_path)[1].lower()
            mime_type = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".gif": "image/gif",
                ".webp": "image/webp"
            }.get(ext, "image/jpeg")
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Extrais tout le texte visible dans cette image. Retourne uniquement le texte extrait, sans commentaire."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{image_data}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=2000
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"❌ Erreur extraction image: {e}")
            return ""
    
    def process_attachment(self, filepath):
        """Process an attachment and extract text based on file type."""
        ext = os.path.splitext(filepath)[1].lower()
        
        if ext == ".pdf":
            print(f"   📄 Extraction PDF: {os.path.basename(filepath)}")
            return self.extract_text_from_pdf(filepath)
        
        elif ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
            print(f"   🖼️ Extraction image: {os.path.basename(filepath)}")
            return self.extract_text_from_image(filepath)
        
        elif ext in [".txt", ".csv"]:
            print(f"   📝 Lecture fichier texte: {os.path.basename(filepath)}")
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    return f.read()
            except:
                return ""
        
        else:
            print(f"   ⚠️ Type de fichier non supporté: {ext}")
            return ""
    
    def process_attachments(self, filepaths):
        """Process multiple attachments and return extracted text."""
        results = {}
        for filepath in filepaths:
            filename = os.path.basename(filepath)
            text = self.process_attachment(filepath)
            if text:
                results[filename] = text
        return results


def test_extractor():
    """Test the data extractor with sample data."""
    print("=" * 50)
    print("🧪 Test de l'extracteur de données")
    print("=" * 50)
    
    extractor = DataExtractor()
    
    # Test with sample email data
    sample_email = {
        "subject": "Commande N° BC-2024-0156 - Sachets kraft",
        "from": "achats@entreprise-client.ma",
        "date": "2024-12-23",
        "body": """Bonjour,

Veuillez trouver ci-dessous notre bon de commande:

Numéro de commande: BC-2024-0156
Entreprise: SARL Les Délices du Maroc
Date: 23/12/2024

Produit: Sachets fond plat kraft naturel
Dimensions: 15x25 cm
Quantité: 10 000 pièces
Prix unitaire: 0.15 MAD
Total: 1 500 MAD HT

Livraison souhaitée: 15/01/2025

Cordialement,
Service Achats
"""
    }
    
    print("\n📧 Email de test:")
    print(f"   Sujet: {sample_email['subject']}")
    print(f"   De: {sample_email['from']}")
    
    print("\n🔍 Extraction en cours...")
    result = extractor.extract_from_email(sample_email)
    
    if result:
        print("\n✅ Données extraites:")
        import json
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("❌ Échec de l'extraction")
    
    print("\n" + "=" * 50)


if __name__ == "__main__":
    test_extractor()
