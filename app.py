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

# ===== YOUR SUPABASE CREDENTIALS =====
SUPABASE_URL = "https://hzqrdwerkgfmfaufabjr.supabase.co"
SUPABASE_KEY = "sb_publishable_tnBOmCO7EFfIoXfNjEH_Tg_D7WX-zld"

SUPABASE_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# ===== DATABASE CONNECTION =====
DB_CONNECTED = False
DB_TYPE = 'json'

def test_supabase_connection():
    try:
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/bookings?select=count",
            headers=SUPABASE_HEADERS,
            timeout=10
        )
        return response.status_code == 200
    except:
        return False

try:
    if test_supabase_connection():
        DB_CONNECTED = True
        DB_TYPE = 'supabase'
        print("✅ Supabase connected!")
except:
    print("📁 Using JSON storage")

# ===== JSON BACKUP =====
ORDERS_FILE = 'bookings.json'
PAYMENTS_FILE = 'payments.json'

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

# ===== DATABASE FUNCTIONS =====
def load_bookings():
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
                return data[0]['id'] if data else None
        except:
            pass
    bookings = load_json(ORDERS_FILE)
    booking_data['id'] = len(bookings) + 1
    bookings.append(booking_data)
    save_json(ORDERS_FILE, bookings)
    return booking_data['id']

def update_booking(booking_id, updates):
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
    bookings = load_json(ORDERS_FILE)
    for booking in bookings:
        if booking.get('id') == booking_id:
            booking.update(updates)
            save_json(ORDERS_FILE, bookings)
            return True
    return False

def get_booking(booking_id):
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

# ===== PAYMENT FUNCTIONS =====
def load_payments():
    if DB_CONNECTED:
        try:
            response = requests.get(
                f"{SUPABASE_URL}/rest/v1/payments?select=*&order=created_at.desc",
                headers=SUPABASE_HEADERS,
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
        except:
            pass
    return load_json(PAYMENTS_FILE)

def save_payment(payment_data):
    if DB_CONNECTED:
        try:
            response = requests.post(
                f"{SUPABASE_URL}/rest/v1/payments",
                headers=SUPABASE_HEADERS,
                json=payment_data,
                timeout=10
            )
            if response.status_code == 201:
                data = response.json()
                return data[0]['id'] if data else None
        except:
            pass
    payments = load_json(PAYMENTS_FILE)
    payment_data['id'] = len(payments) + 1
    payments.append(payment_data)
    save_json(PAYMENTS_FILE, payments)
    return payment_data['id']

def update_payment(payment_id, updates):
    if DB_CONNECTED:
        try:
            response = requests.patch(
                f"{SUPABASE_URL}/rest/v1/payments?id=eq.{payment_id}",
                headers=SUPABASE_HEADERS,
                json=updates,
                timeout=10
            )
            if response.status_code == 200:
                return True
        except:
            pass
    payments = load_json(PAYMENTS_FILE)
    for payment in payments:
        if payment.get('id') == payment_id:
            payment.update(updates)
            save_json(PAYMENTS_FILE, payments)
            return True
    return False

# ===== HELPERS =====
def generate_booking_id():
    return 'DON-' + str(uuid.uuid4().hex[:8]).upper()

def generate_payment_id():
    return 'PAY-' + str(uuid.uuid4().hex[:8]).upper()

def calculate_price(vehicle_type, distance_km=10):
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
    payments = load_payments()
    
    stats = {
        'total': len(bookings),
        'pending': len([b for b in bookings if b.get('status') == 'pending']),
        'confirmed': len([b for b in bookings if b.get('status') == 'confirmed']),
        'completed': len([b for b in bookings if b.get('status') == 'completed']),
        'cancelled': len([b for b in bookings if b.get('status') == 'cancelled']),
        'revenue': sum([float(b.get('amount', 0)) for b in bookings if b.get('status') == 'completed']),
        'payments': len(payments),
        'today': len([b for b in bookings if b.get('created_at', '').startswith(datetime.now().strftime('%Y-%m-%d'))])
    }
    return render_template('admin.html', bookings=bookings, payments=payments, stats=stats, db_type=DB_TYPE, db_connected=DB_CONNECTED)

@app.route('/api/status')
def api_status():
    bookings = load_bookings()
    return jsonify({
        'database': DB_TYPE,
        'connected': DB_CONNECTED,
        'bookings': len(bookings),
        'timestamp': datetime.utcnow().isoformat()
    })

@app.route('/api/reconnect')
def reconnect_db():
    global DB_CONNECTED
    DB_CONNECTED = test_supabase_connection()
    return jsonify({'connected': DB_CONNECTED})

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

@app.route('/api/payment', methods=['POST'])
def process_payment():
    try:
        data = request.get_json()
        booking_id = data.get('booking_id')
        payment_method = data.get('payment_method', 'mpesa')
        phone_number = data.get('phone_number', '')
        
        booking = get_booking(int(booking_id)) if booking_id else None
        if not booking:
            return jsonify({'success': False, 'error': 'Booking not found'}), 404
        
        payment_id = generate_payment_id()
        
        payment_data = {
            'payment_id': payment_id,
            'booking_id': booking_id,
            'customer_name': booking.get('customer_name'),
            'customer_email': booking.get('customer_email'),
            'customer_phone': booking.get('customer_phone'),
            'amount': booking.get('amount'),
            'payment_method': payment_method,
            'payment_status': 'processing',
            'created_at': datetime.utcnow().isoformat()
        }
        
        save_payment(payment_data)
        
        # Simulate payment processing
        # In production, this would call M-Pesa API
        
        # Update booking status
        update_booking(int(booking_id), {'payment_status': 'paid', 'status': 'confirmed'})
        
        return jsonify({
            'success': True,
            'message': 'Payment processed successfully!',
            'payment_id': payment_id,
            'receipt': {
                'booking_id': booking_id,
                'amount': booking.get('amount'),
                'payment_method': payment_method,
                'status': 'completed',
                'paid_at': datetime.utcnow().isoformat()
            }
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

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
