from flask import Flask, request, jsonify, render_template, session, redirect, url_for, flash
from datetime import datetime, timedelta
import os
import uuid
import json
import requests
from functools import wraps

app = Flask(__name__)
app.secret_key = 'don-travels-secret-key-2026'
app.permanent_session_lifetime = timedelta(days=7)

# ===== YOUR SUPABASE CREDENTIALS (HARDCODED FOR RELIABILITY) =====
SUPABASE_URL = "https://hzqrdwerkgfmfaufabjr.supabase.co"
SUPABASE_KEY = "sb_publishable_tnBOmCO7EFfIoXfNjEH_Tg_D7WX-zld"

SUPABASE_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# ===== DATABASE CONNECTION WITH RETRY LOGIC =====
DB_CONNECTED = False
DB_TYPE = 'json'

def test_supabase_connection():
    """Test Supabase connection with retry"""
    try:
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/bookings?select=count",
            headers=SUPABASE_HEADERS,
            timeout=10
        )
        return response.status_code == 200
    except:
        return False

# Try to connect
try:
    if test_supabase_connection():
        DB_CONNECTED = True
        DB_TYPE = 'supabase'
        print("✅ Supabase connected successfully!")
    else:
        print("❌ Supabase connection failed")
        print("📁 Using JSON storage")
except Exception as e:
    print(f"❌ Supabase error: {e}")
    print("📁 Using JSON storage")

# ===== JSON BACKUP =====
ORDERS_FILE = 'bookings.json'

def load_json(file_path):
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                return json.load(f)
        return []
    except:
        return []

def save_json(file_path, data):
    try:
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except:
        return False

# ===== DATABASE FUNCTIONS WITH AUTO-RETRY =====
def ensure_connection():
    """Check and reconnect if needed"""
    global DB_CONNECTED
    if not DB_CONNECTED:
        DB_CONNECTED = test_supabase_connection()
    return DB_CONNECTED

def load_bookings():
    # Try to reconnect if needed
    ensure_connection()
    
    if DB_CONNECTED:
        try:
            response = requests.get(
                f"{SUPABASE_URL}/rest/v1/bookings?select=*&order=created_at.desc",
                headers=SUPABASE_HEADERS,
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
        except:
            pass
    return load_json(ORDERS_FILE)

def save_booking(booking_data):
    # Try to reconnect if needed
    ensure_connection()
    
    if DB_CONNECTED:
        try:
            response = requests.post(
                f"{SUPABASE_URL}/rest/v1/bookings",
                headers=SUPABASE_HEADERS,
                json=booking_data,
                timeout=10
            )
            if response.status_code == 201:
                data = response.json()
                print(f"✅ Booking saved to Supabase: {booking_data['booking_id']}")
                return data[0]['id'] if data else None
        except Exception as e:
            print(f"⚠️ Supabase save error: {e}")
    
    # Fallback to JSON
    bookings = load_json(ORDERS_FILE)
    booking_data['id'] = len(bookings) + 1
    bookings.append(booking_data)
    save_json(ORDERS_FILE, bookings)
    print(f"📁 Booking saved to JSON: {booking_data['booking_id']}")
    return booking_data['id']

def update_booking(booking_id, updates):
    # Try to reconnect if needed
    ensure_connection()
    
    if DB_CONNECTED:
        try:
            response = requests.patch(
                f"{SUPABASE_URL}/rest/v1/bookings?id=eq.{booking_id}",
                headers=SUPABASE_HEADERS,
                json=updates,
                timeout=10
            )
            if response.status_code == 200:
                return True
        except:
            pass
    
    # Fallback to JSON
    bookings = load_json(ORDERS_FILE)
    for booking in bookings:
        if booking.get('id') == booking_id:
            booking.update(updates)
            save_json(ORDERS_FILE, bookings)
            return True
    return False

def get_booking(booking_id):
    # Try to reconnect if needed
    ensure_connection()
    
    if DB_CONNECTED:
        try:
            response = requests.get(
                f"{SUPABASE_URL}/rest/v1/bookings?id=eq.{booking_id}",
                headers=SUPABASE_HEADERS,
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                return data[0] if data else None
        except:
            pass
    
    bookings = load_json(ORDERS_FILE)
    for booking in bookings:
        if booking.get('id') == booking_id:
            return booking
    return None

def delete_booking(booking_id):
    # Try to reconnect if needed
    ensure_connection()
    
    if DB_CONNECTED:
        try:
            response = requests.delete(
                f"{SUPABASE_URL}/rest/v1/bookings?id=eq.{booking_id}",
                headers=SUPABASE_HEADERS,
                timeout=10
            )
            if response.status_code == 204:
                return True
        except:
            pass
    
    bookings = load_json(ORDERS_FILE)
    bookings = [b for b in bookings if b.get('id') != booking_id]
    save_json(ORDERS_FILE, bookings)
    return True

# ===== HELPERS =====
def generate_booking_id():
    return 'DON-' + str(uuid.uuid4().hex[:8]).upper()

def generate_user_id():
    return 'USR-' + str(uuid.uuid4().hex[:8]).upper()

def calculate_price(vehicle_type, distance_km=10):
    """Calculate price based on vehicle type"""
    prices = {
        'Standard Sedan': 1500,
        'Premium Sedan': 2500,
        'Toyota Hiace': 3500,
        'Executive Sedan': 4500,
        'Luxury SUV': 5500,
        'Executive Van': 6500
    }
    return prices.get(vehicle_type, 2000)

# ===== ROUTES =====
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin')
def admin():
    bookings = load_bookings()
    stats = {
        'total': len(bookings),
        'pending': len([b for b in bookings if b.get('status') == 'pending']),
        'confirmed': len([b for b in bookings if b.get('status') == 'confirmed']),
        'completed': len([b for b in bookings if b.get('status') == 'completed']),
        'cancelled': len([b for b in bookings if b.get('status') == 'cancelled']),
        'revenue': sum([float(b.get('amount', 0)) for b in bookings if b.get('status') == 'completed'])
    }
    return render_template('admin.html', bookings=bookings, stats=stats, db_type=DB_TYPE, db_connected=DB_CONNECTED)

@app.route('/api/status')
def api_status():
    # Force recheck connection
    global DB_CONNECTED
    DB_CONNECTED = test_supabase_connection()
    bookings = load_bookings()
    
    return jsonify({
        'database': DB_TYPE,
        'connected': DB_CONNECTED,
        'bookings': len(bookings),
        'timestamp': datetime.utcnow().isoformat()
    })

@app.route('/api/test-db')
def test_db():
    # Force recheck connection
    global DB_CONNECTED
    DB_CONNECTED = test_supabase_connection()
    bookings = load_bookings()
    
    return jsonify({
        'connected': DB_CONNECTED,
        'type': DB_TYPE,
        'bookings_count': len(bookings),
        'message': '✅ Connected to Supabase!' if DB_CONNECTED else '📁 Using JSON storage'
    })

@app.route('/api/reconnect')
def reconnect_db():
    """Force reconnection to Supabase"""
    global DB_CONNECTED
    DB_CONNECTED = test_supabase_connection()
    return jsonify({
        'connected': DB_CONNECTED,
        'message': '✅ Reconnected to Supabase!' if DB_CONNECTED else '❌ Still disconnected'
    })

@app.route('/api/book', methods=['POST'])
def create_booking():
    try:
        customer_name = request.form.get('name', '').strip()
        customer_email = request.form.get('email', '').strip()
        customer_phone = request.form.get('phone', '').strip()
        pickup_location = request.form.get('pickup', '').strip()
        dropoff_location = request.form.get('dropoff', '').strip()
        vehicle_type = request.form.get('vehicle', '').strip()
        booking_date = request.form.get('date', '').strip()
        booking_time = request.form.get('time', '').strip()
        passengers = request.form.get('passengers', '1').strip()
        special_requests = request.form.get('special_requests', '').strip()

        if not all([customer_name, customer_email, pickup_location, dropoff_location, vehicle_type, booking_date]):
            return jsonify({'success': False, 'error': 'Please fill in all required fields'}), 400

        amount = calculate_price(vehicle_type)
        booking_id = generate_booking_id()
        
        booking_data = {
            'booking_id': booking_id,
            'customer_name': customer_name,
            'customer_email': customer_email,
            'customer_phone': customer_phone,
            'pickup_location': pickup_location,
            'dropoff_location': dropoff_location,
            'vehicle_type': vehicle_type,
            'booking_date': booking_date,
            'booking_time': booking_time,
            'passengers': int(passengers),
            'special_requests': special_requests,
            'amount': amount,
            'status': 'pending',
            'payment_status': 'pending',
            'created_at': datetime.utcnow().isoformat()
        }
        
        save_booking(booking_data)

        return jsonify({
            'success': True, 
            'message': 'Booking created successfully!',
            'booking_id': booking_id,
            'amount': amount
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/bookings', methods=['GET'])
def get_bookings():
    bookings = load_bookings()
    return jsonify({'bookings': bookings}), 200

@app.route('/api/bookings/<int:booking_id>/status', methods=['PUT'])
def update_booking_status(booking_id):
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        if new_status not in ['pending', 'confirmed', 'completed', 'cancelled']:
            return jsonify({'success': False, 'error': 'Invalid status'}), 400

        booking = get_booking(booking_id)
        if not booking:
            return jsonify({'success': False, 'error': 'Booking not found'}), 404

        updates = {'status': new_status}
        if new_status == 'confirmed':
            updates['payment_status'] = 'paid'
        
        update_booking(booking_id, updates)

        return jsonify({'success': True, 'message': f'Status updated to {new_status}'}), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/bookings/<int:booking_id>', methods=['DELETE'])
def delete_booking_route(booking_id):
    try:
        booking = get_booking(booking_id)
        if not booking:
            return jsonify({'success': False, 'error': 'Booking not found'}), 404

        delete_booking(booking_id)

        return jsonify({'success': True, 'message': 'Booking deleted successfully'}), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ===== VERCEL HANDLER =====
def handler(request, context):
    return app(request, context)

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 DON TRAVELS - Premium Taxi & Executive Services")
    print("="*60)
    print(f"📁 Database: {DB_TYPE}")
    print(f"🔗 Connected: {'✅ YES' if DB_CONNECTED else '❌ NO'}")
    print("="*60)
    app.run(debug=True, host='0.0.0.0', port=5000)
