from flask import Flask, request, jsonify, render_template, send_file, send_from_directory
from datetime import datetime
import os
import uuid
import base64
import json
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'dev-secret-key-12345'

# ===== SUPABASE CONFIGURATION =====
SUPABASE_URL = "https://hzqrdwerkgfmfaufabjr.supabase.co"
SUPABASE_KEY = "sb_publishable_tnBOmCO7EFfIoXfNjEH_Tg_D7WX-zld"

# Try to import supabase
try:
    from supabase import create_client
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    DB_CONNECTED = True
    DB_TYPE = 'supabase'
    print("✅ Supabase connected!")
except Exception as e:
    supabase = None
    DB_CONNECTED = False
    DB_TYPE = 'json'
    print(f"⚠️ Supabase error: {e}")
    print("📁 Using JSON storage")

# ===== FILE CONFIGURATION =====
if os.environ.get('VERCEL'):
    UPLOAD_FOLDER = '/tmp/uploads'
    ORDERS_FILE = '/tmp/bookings.json'
else:
    UPLOAD_FOLDER = 'uploads'
    ORDERS_FILE = 'bookings.json'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}

# ===== DATABASE FUNCTIONS =====
def get_bookings_from_supabase():
    """Get bookings from Supabase"""
    try:
        response = supabase.table('bookings').select('*').order('created_at', desc=True).execute()
        return response.data
    except Exception as e:
        print(f"Supabase error: {e}")
        return None

def save_booking_to_supabase(booking_data):
    """Save booking to Supabase"""
    try:
        response = supabase.table('bookings').insert(booking_data).execute()
        return response.data[0]['id'] if response.data else None
    except Exception as e:
        print(f"Supabase save error: {e}")
        return None

def load_bookings():
    """Load bookings from Supabase or JSON"""
    if DB_CONNECTED:
        try:
            bookings = get_bookings_from_supabase()
            if bookings is not None:
                return bookings
        except:
            pass
    return load_bookings_json()

def load_bookings_json():
    try:
        if os.path.exists(ORDERS_FILE):
            with open(ORDERS_FILE, 'r') as f:
                return json.load(f)
        return []
    except:
        return []

def save_bookings_json(bookings):
    try:
        with open(ORDERS_FILE, 'w') as f:
            json.dump(bookings, f, indent=2)
        return True
    except:
        return False

def get_booking_by_id(booking_id):
    if DB_CONNECTED:
        try:
            response = supabase.table('bookings').select('*').eq('id', booking_id).execute()
            return response.data[0] if response.data else None
        except:
            pass
    bookings = load_bookings_json()
    for booking in bookings:
        if booking.get('id') == booking_id:
            return booking
    return None

def add_booking(booking_data):
    if DB_CONNECTED:
        try:
            booking_id = save_booking_to_supabase(booking_data)
            if booking_id:
                print(f"✅ Booking saved to Supabase: {booking_data['booking_id']}")
                return booking_id
        except:
            pass
    
    # Fallback to JSON
    bookings = load_bookings_json()
    booking_data['id'] = len(bookings) + 1
    bookings.append(booking_data)
    save_bookings_json(bookings)
    print(f"📁 Booking saved to JSON: {booking_data['booking_id']}")
    return booking_data['id']

def update_booking(booking_id, updates):
    if DB_CONNECTED:
        try:
            response = supabase.table('bookings').update(updates).eq('id', booking_id).execute()
            if response.data:
                return True
        except:
            pass
    
    # Fallback to JSON
    bookings = load_bookings_json()
    for booking in bookings:
        if booking.get('id') == booking_id:
            booking.update(updates)
            save_bookings_json(bookings)
            return True
    return False

def delete_booking(booking_id):
    if DB_CONNECTED:
        try:
            response = supabase.table('bookings').delete().eq('id', booking_id).execute()
            if response.data:
                return True
        except:
            pass
    
    # Fallback to JSON
    bookings = load_bookings_json()
    bookings = [b for b in bookings if b.get('id') != booking_id]
    save_bookings_json(bookings)
    return True

# ===== HELPER FUNCTIONS =====
def generate_booking_id():
    return 'DON-' + str(uuid.uuid4().hex[:8]).upper()

# ===== ROUTES =====

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin')
def admin():
    try:
        bookings = load_bookings()
        for booking in bookings:
            if 'created_at' not in booking:
                booking['created_at'] = datetime.utcnow().isoformat()
        
        stats = {
            'total': len(bookings),
            'pending': len([b for b in bookings if b.get('status') == 'pending']),
            'confirmed': len([b for b in bookings if b.get('status') == 'confirmed']),
            'completed': len([b for b in bookings if b.get('status') == 'completed']),
            'cancelled': len([b for b in bookings if b.get('status') == 'cancelled']),
            'revenue': sum([float(b.get('amount', 0)) for b in bookings if b.get('status') == 'completed'])
        }
        
        return render_template('admin.html', 
            bookings=bookings, 
            stats=stats, 
            db_connected=DB_CONNECTED,
            db_type=DB_TYPE,
            db_status={'connected': DB_CONNECTED, 'type': DB_TYPE}
        )
    except Exception as e:
        return f"<h1>Error loading admin</h1><p>{str(e)}</p>", 500

@app.route('/api/status')
def api_status():
    return jsonify({
        'database_connected': DB_CONNECTED,
        'database_type': DB_TYPE,
        'bookings': len(load_bookings()),
        'timestamp': datetime.utcnow().isoformat()
    })

@app.route('/api/test-db')
def test_db():
    result = {
        'connected': DB_CONNECTED,
        'type': DB_TYPE,
        'bookings_count': len(load_bookings()),
        'message': '✅ Connected to Supabase!' if DB_CONNECTED else '📁 Using JSON storage'
    }
    return jsonify(result)

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

        # Calculate price based on vehicle type
        vehicle_prices = {
            'Standard': 1500,
            'Premium': 2500,
            'Executive': 4000,
            'Luxury SUV': 5500,
            'Van': 3500
        }
        amount = vehicle_prices.get(vehicle_type, 2000)

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
        
        add_booking(booking_data)

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

        booking = get_booking_by_id(booking_id)
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
        booking = get_booking_by_id(booking_id)
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
