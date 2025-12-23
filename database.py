"""
Database Manager Module
SQLite database for storing purchase orders, clients, products, and logs.
"""

import sqlite3
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Fix Windows console encoding
sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

DATABASE_FILE = "orders.db"

# Product types catalog
PRODUCT_CATALOG = [
    {"id": 1, "type": "Sachets fond plat", "description": "Sachets à fond plat pour emballage"},
    {"id": 2, "type": "Sac fond carré sans poignées", "description": "Sacs fond carré sans poignées"},
    {"id": 3, "type": "Sac fond carré avec poignées plates", "description": "Sacs fond carré avec poignées plates"},
    {"id": 4, "type": "Sac fond carré avec poignées torsadées", "description": "Sacs fond carré avec poignées torsadées"}
]


class DatabaseManager:
    def __init__(self, db_file=DATABASE_FILE):
        self.db_file = db_file
        self.connection = None
    
    def connect(self):
        """Connect to the SQLite database."""
        try:
            self.connection = sqlite3.connect(self.db_file)
            self.connection.row_factory = sqlite3.Row
            print(f"✅ Connexion à la base de données: {self.db_file}")
            return True
        except Exception as e:
            print(f"❌ Erreur de connexion DB: {e}")
            return False
    
    def disconnect(self):
        """Close the database connection."""
        if self.connection:
            self.connection.close()
            print("📤 Déconnexion de la base de données")
    
    def init_database(self):
        """Initialize database with required tables."""
        if not self.connection:
            self.connect()
        
        cursor = self.connection.cursor()
        
        # Create Clients table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT NOT NULL,
                email TEXT,
                telephone TEXT,
                adresse TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create Products table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS produits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create Orders table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS commandes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero_commande TEXT UNIQUE,
                client_id INTEGER,
                produit_id INTEGER,
                nature_produit TEXT,
                quantite REAL,
                unite TEXT,
                prix_unitaire REAL,
                prix_total REAL,
                devise TEXT DEFAULT 'MAD',
                date_commande DATE,
                date_livraison DATE,
                informations_supplementaires TEXT,
                confiance INTEGER,
                statut TEXT DEFAULT 'en_attente',
                email_id TEXT,
                email_subject TEXT,
                email_from TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                validated_at TIMESTAMP,
                validated_by TEXT,
                FOREIGN KEY (client_id) REFERENCES clients(id),
                FOREIGN KEY (produit_id) REFERENCES produits(id)
            )
        """)
        
        # Create Logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                table_name TEXT,
                record_id INTEGER,
                details TEXT,
                user_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert default products if not exist
        for product in PRODUCT_CATALOG:
            cursor.execute("""
                INSERT OR IGNORE INTO produits (id, type, description)
                VALUES (?, ?, ?)
            """, (product['id'], product['type'], product['description']))
        
        self.connection.commit()
        print("✅ Base de données initialisée avec succès")
        
        self._log_action("INIT", "database", None, "Database initialized")
    
    def _log_action(self, action, table_name, record_id, details):
        """Log an action to the logs table."""
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT INTO logs (action, table_name, record_id, details)
            VALUES (?, ?, ?, ?)
        """, (action, table_name, record_id, details))
        self.connection.commit()
    
    # Client operations
    def get_or_create_client(self, nom, email=None):
        """Get existing client or create new one."""
        cursor = self.connection.cursor()
        
        # Try to find by name
        cursor.execute("SELECT * FROM clients WHERE nom = ?", (nom,))
        client = cursor.fetchone()
        
        if client:
            return dict(client)
        
        # Create new client
        cursor.execute("""
            INSERT INTO clients (nom, email)
            VALUES (?, ?)
        """, (nom, email))
        self.connection.commit()
        
        client_id = cursor.lastrowid
        self._log_action("CREATE", "clients", client_id, f"Created client: {nom}")
        
        return {"id": client_id, "nom": nom, "email": email}
    
    def get_all_clients(self):
        """Get all clients."""
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM clients ORDER BY nom")
        return [dict(row) for row in cursor.fetchall()]
    
    # Product operations
    def get_product_by_type(self, type_name):
        """Get product by type name."""
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM produits WHERE type LIKE ?", (f"%{type_name}%",))
        product = cursor.fetchone()
        return dict(product) if product else None
    
    def get_all_products(self):
        """Get all products."""
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM produits")
        return [dict(row) for row in cursor.fetchall()]
    
    # Order operations
    def create_order(self, order_data):
        """Create a new order from extracted data."""
        cursor = self.connection.cursor()
        
        # Get or create client
        client_name = order_data.get('entreprise_cliente', 'Client Inconnu')
        client = self.get_or_create_client(client_name, order_data.get('email_from'))
        
        # Get product
        product = None
        if order_data.get('type_produit'):
            product = self.get_product_by_type(order_data['type_produit'])
        
        # Insert order
        cursor.execute("""
            INSERT INTO commandes (
                numero_commande, client_id, produit_id, nature_produit,
                quantite, unite, prix_unitaire, prix_total, devise,
                date_commande, date_livraison, informations_supplementaires,
                confiance, email_id, email_subject, email_from
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            order_data.get('numero_commande'),
            client['id'],
            product['id'] if product else None,
            order_data.get('nature_produit'),
            order_data.get('quantite'),
            order_data.get('unite'),
            order_data.get('prix_unitaire'),
            order_data.get('prix_total'),
            order_data.get('devise', 'MAD'),
            order_data.get('date_commande'),
            order_data.get('date_livraison'),
            order_data.get('informations_supplementaires'),
            order_data.get('confiance'),
            order_data.get('email_id'),
            order_data.get('email_subject'),
            order_data.get('email_from')
        ))
        
        self.connection.commit()
        order_id = cursor.lastrowid
        
        self._log_action("CREATE", "commandes", order_id, 
                        f"Created order: {order_data.get('numero_commande')}")
        
        print(f"   💾 Commande enregistrée (ID: {order_id})")
        return order_id
    
    def get_order(self, order_id):
        """Get order by ID with client and product info."""
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT c.*, cl.nom as client_nom, p.type as produit_type
            FROM commandes c
            LEFT JOIN clients cl ON c.client_id = cl.id
            LEFT JOIN produits p ON c.produit_id = p.id
            WHERE c.id = ?
        """, (order_id,))
        order = cursor.fetchone()
        return dict(order) if order else None
    
    def get_all_orders(self, status=None):
        """Get all orders, optionally filtered by status."""
        cursor = self.connection.cursor()
        
        if status:
            cursor.execute("""
                SELECT c.*, cl.nom as client_nom, p.type as produit_type
                FROM commandes c
                LEFT JOIN clients cl ON c.client_id = cl.id
                LEFT JOIN produits p ON c.produit_id = p.id
                WHERE c.statut = ?
                ORDER BY c.created_at DESC
            """, (status,))
        else:
            cursor.execute("""
                SELECT c.*, cl.nom as client_nom, p.type as produit_type
                FROM commandes c
                LEFT JOIN clients cl ON c.client_id = cl.id
                LEFT JOIN produits p ON c.produit_id = p.id
                ORDER BY c.created_at DESC
            """)
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_pending_orders(self):
        """Get orders pending validation."""
        return self.get_all_orders(status='en_attente')
    
    def update_order_status(self, order_id, status, validated_by=None):
        """Update order status."""
        cursor = self.connection.cursor()
        
        if status == 'validee':
            cursor.execute("""
                UPDATE commandes
                SET statut = ?, validated_at = ?, validated_by = ?
                WHERE id = ?
            """, (status, datetime.now().isoformat(), validated_by, order_id))
        else:
            cursor.execute("""
                UPDATE commandes SET statut = ? WHERE id = ?
            """, (status, order_id))
        
        self.connection.commit()
        self._log_action("UPDATE", "commandes", order_id, f"Status changed to: {status}")
        print(f"   ✅ Statut mis à jour: {status}")
    
    def update_order(self, order_id, updates):
        """Update order fields."""
        cursor = self.connection.cursor()
        
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [order_id]
        
        cursor.execute(f"""
            UPDATE commandes SET {set_clause}, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, values)
        
        self.connection.commit()
        self._log_action("UPDATE", "commandes", order_id, f"Updated fields: {list(updates.keys())}")
    
    def delete_order(self, order_id):
        """Delete an order (soft delete by changing status)."""
        cursor = self.connection.cursor()
        cursor.execute("UPDATE commandes SET statut = 'supprimee' WHERE id = ?", (order_id,))
        self.connection.commit()
        self._log_action("DELETE", "commandes", order_id, "Order marked as deleted")
    
    # Statistics
    def get_stats(self):
        """Get database statistics."""
        cursor = self.connection.cursor()
        
        stats = {}
        
        cursor.execute("SELECT COUNT(*) FROM commandes")
        stats['total_orders'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM commandes WHERE statut = 'en_attente'")
        stats['pending_orders'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM commandes WHERE statut = 'validee'")
        stats['validated_orders'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM clients")
        stats['total_clients'] = cursor.fetchone()[0]
        
        return stats
    
    def get_logs(self, limit=50):
        """Get recent logs."""
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT * FROM logs ORDER BY created_at DESC LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]


def test_database():
    """Test database operations."""
    print("=" * 50)
    print("🧪 Test de la base de données")
    print("=" * 50)
    
    db = DatabaseManager()
    db.connect()
    db.init_database()
    
    # Show products
    print("\n📦 Produits disponibles:")
    products = db.get_all_products()
    for p in products:
        print(f"   {p['id']}. {p['type']}")
    
    # Test order creation
    print("\n🛒 Test création de commande...")
    test_order = {
        "numero_commande": "TEST-001",
        "entreprise_cliente": "Entreprise Test SARL",
        "type_produit": "Sachets fond plat",
        "nature_produit": "Sachets kraft 15x25cm",
        "quantite": 5000,
        "unite": "pièces",
        "prix_unitaire": 0.20,
        "prix_total": 1000,
        "devise": "MAD",
        "date_commande": "2024-12-23",
        "date_livraison": "2025-01-15",
        "confiance": 90,
        "email_id": "test-email-001",
        "email_subject": "Test Order",
        "email_from": "test@example.com"
    }
    
    order_id = db.create_order(test_order)
    
    # Get order
    order = db.get_order(order_id)
    print(f"\n📋 Commande créée:")
    print(f"   ID: {order['id']}")
    print(f"   N°: {order['numero_commande']}")
    print(f"   Client: {order['client_nom']}")
    print(f"   Produit: {order['produit_type']}")
    print(f"   Quantité: {order['quantite']} {order['unite']}")
    print(f"   Statut: {order['statut']}")
    
    # Stats
    stats = db.get_stats()
    print(f"\n📊 Statistiques:")
    print(f"   Total commandes: {stats['total_orders']}")
    print(f"   En attente: {stats['pending_orders']}")
    print(f"   Validées: {stats['validated_orders']}")
    print(f"   Clients: {stats['total_clients']}")
    
    db.disconnect()
    
    print("\n" + "=" * 50)
    print("✅ Test base de données terminé")
    print("=" * 50)


if __name__ == "__main__":
    test_database()
