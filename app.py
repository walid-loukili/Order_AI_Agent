"""
Flask Web Application for Purchase Order Validation
Interface for commercial team to view, edit, and validate orders.
"""

import os
import sys
from flask import Flask, render_template, request, jsonify, redirect, url_for
from datetime import datetime

# Fix Windows console encoding
sys.stdout.reconfigure(encoding='utf-8')

from database import DatabaseManager
from process_orders import OrderProcessor

app = Flask(__name__)
app.secret_key = os.urandom(24)

db = DatabaseManager()


@app.before_request
def before_request():
    """Connect to database before each request."""
    db.connect()
    db.init_database()


@app.teardown_request
def teardown_request(exception):
    """Disconnect from database after each request."""
    db.disconnect()


# ============== PAGES ==============

@app.route('/')
def index():
    """Dashboard page."""
    stats = db.get_stats()
    recent_orders = db.get_all_orders()[:5]
    return render_template('index.html', stats=stats, recent_orders=recent_orders)


@app.route('/orders')
def orders_list():
    """List all orders."""
    status_filter = request.args.get('status', None)
    if status_filter:
        orders = db.get_all_orders(status=status_filter)
    else:
        orders = db.get_all_orders()
    return render_template('orders.html', orders=orders, current_filter=status_filter)


@app.route('/orders/<int:order_id>')
def order_detail(order_id):
    """Order detail page for validation."""
    order = db.get_order(order_id)
    products = db.get_all_products()
    if not order:
        return redirect(url_for('orders_list'))
    return render_template('order_detail.html', order=order, products=products)


@app.route('/process')
def process_page():
    """Page to trigger email processing."""
    return render_template('process.html')


# ============== API ENDPOINTS ==============

@app.route('/api/process-emails', methods=['POST'])
def api_process_emails():
    """Process new emails for purchase orders."""
    try:
        processor = OrderProcessor()
        orders = processor.process_new_emails(max_emails=10, save_to_db=True)
        return jsonify({
            'success': True,
            'message': f'{len(orders)} bon(s) de commande détecté(s)',
            'orders_count': len(orders)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/orders/<int:order_id>/validate', methods=['POST'])
def api_validate_order(order_id):
    """Validate an order."""
    validated_by = request.json.get('validated_by', 'Commercial')
    db.update_order_status(order_id, 'validee', validated_by)
    return jsonify({'success': True, 'message': 'Commande validée'})


@app.route('/api/orders/<int:order_id>/reject', methods=['POST'])
def api_reject_order(order_id):
    """Reject an order."""
    db.update_order_status(order_id, 'rejetee')
    return jsonify({'success': True, 'message': 'Commande rejetée'})


@app.route('/api/orders/<int:order_id>/update', methods=['POST'])
def api_update_order(order_id):
    """Update order fields."""
    updates = request.json
    # Remove fields that shouldn't be updated directly
    updates.pop('id', None)
    updates.pop('created_at', None)
    db.update_order(order_id, updates)
    return jsonify({'success': True, 'message': 'Commande mise à jour'})


@app.route('/api/stats')
def api_stats():
    """Get statistics."""
    stats = db.get_stats()
    return jsonify(stats)


@app.route('/api/orders')
def api_orders():
    """Get all orders as JSON."""
    orders = db.get_all_orders()
    return jsonify(orders)


if __name__ == '__main__':
    print("=" * 50)
    print("🚀 Démarrage de l'interface de validation")
    print("=" * 50)
    print("📍 URL: http://localhost:5000")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5000)
