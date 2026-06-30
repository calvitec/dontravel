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

try:
    # Test connection
    response = requests.get(
        f"{SUPABASE_URL}/rest/v1/bookings?select=count",
        headers=SUPABASE_HEADERS
    )
    
    if response.status_code == 200:
        DB_CONNECTED = True
        DB_TYPE = 'supabase'
        print("✅ Supabase connected successfully!")
    else:
        print(f"❌ Supabase error: {response.status_code}")
        
except Exception as e:
    print(f"❌ Supabase connection error: {e}")
    print("📁 Using JSON storage")

# ===== JSON BACKUP =====
ORDERS_FILE = 'bookings.json'
USERS_FILE = 'users.json'

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
                headers=SUPABASE_HEADERS
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
                json=booking_data
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
                json=updates
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
                headers=SUPABASE_HEADERS
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
                headers=SUPABASE_HEADERS
            )
            if response.status_code == 204:
                return True
        except:
            pass
    bookings = load_json(ORDERS_FILE)
    bookings = [b for b in bookings if b.get('id') != booking_id]
    save_json(ORDERS_FILE, bookings)
    return True

# ===== USER FUNCTIONS =====
def load_users():
    if DB_CONNECTED:
        try:
            response = requests.get(
                f"{SUPABASE_URL}/rest/v1/users?select=*",
                headers=SUPABASE_HEADERS
            )
            if response.status_code == 200:
                return response.json()
        except:
            pass
    return load_json(USERS_FILE)

def save_user(user_data):
    if DB_CONNECTED:
        try:
            response = requests.post(
                f"{SUPABASE_URL}/rest/v1/users",
                headers=SUPABASE_HEADERS,
                json=user_data
            )
            if response.status_code == 201:
                return True
        except:
            pass
    users = load_json(USERS_FILE)
    user_data['id'] = len(users) + 1
    users.append(user_data)
    save_json(USERS_FILE, users)
    return True

def get_user_by_email(email):
    users = load_users()
    for user in users:
        if user.get('email') == email:
            return user
    return None

# ===== HELPERS =====
def generate_booking_id():
    return 'DON-' + str(uuid.uuid4().hex[:8]).upper()

def generate_user_id():
    return 'USR-' + str(uuid.uuid4().hex[:8]).upper()

def generate_payment_id():
    return 'PAY-' + str(uuid.uuid4().hex[:8]).upper()

def calculate_price(vehicle_type, distance_km=10):
    """Calculate price based on vehicle type and distance"""
    base_prices = {
        'Standard Sedan': 1500,
        'Premium Sedan': 2500,
        'Toyota Hiace': 3500,
        'Executive Sedan': 4500,
        'Luxury SUV': 5500,
        'Executive Van': 6500
    }
    
    per_km_rates = {
        'Standard Sedan': 50,
        'Premium Sedan': 80,
        'Toyota Hiace': 70,
        'Executive Sedan': 100,
        'Luxury SUV': 120,
        'Executive Van': 110
    }
    
    base = base_prices.get(vehicle_type, 2000)
    per_km = per_km_rates.get(vehicle_type, 60)
    
    # Minimum 5km included in base price
    if distance_km <= 5:
        return base
    else:
        return base + (distance_km - 5) * per_km

# ===== AUTH DECORATOR =====
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ===== ROUTES =====

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = get_user_by_email(email)
        if user and user.get('password') == password:  # In production, use password hashing
            session.permanent = True
            session['user_id'] = user.get('id')
            session['user_name'] = user.get('full_name')
            session['user_email'] = user.get('email')
            session['user_role'] = user.get('role', 'customer')
            
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')
        
        # Check if user exists
        if get_user_by_email(email):
            flash('Email already registered', 'danger')
            return redirect(url_for('register'))
        
        user_data = {
            'user_id': generate_user_id(),
            'full_name': full_name,
            'email': email,
            'phone': phone,
            'password': password,  # In production, hash this!
            'role': 'customer',
            'is_verified': True,
            'created_at': datetime.utcnow().isoformat()
        }
        
        if save_user(user_data):
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Registration failed. Please try again.', 'danger')
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    bookings = load_bookings()
    user_bookings = [b for b in bookings if b.get('customer_email') == session.get('user_email')]
    
    stats = {
        'total': len(user_bookings),
        'pending': len([b for b in user_bookings if b.get('status') == 'pending']),
        'confirmed': len([b for b in user_bookings if b.get('status') == 'confirmed']),
        'completed': len([b for b in user_bookings if b.get('status') == 'completed']),
        'cancelled': len([b for b in user_bookings if b.get('status') == 'cancelled'])
    }
    
    return render_template('dashboard.html', bookings=user_bookings, stats=stats)

@app.route('/booking/<booking_id>')
@login_required
def view_booking(booking_id):
    booking = get_booking(int(booking_id)) if booking_id.isdigit() else None
    if not booking:
        flash('Booking not found', 'danger')
        return redirect(url_for('dashboard'))
    
    if booking.get('customer_email') != session.get('user_email'):
        flash('Unauthorized access', 'danger')
        return redirect(url_for('dashboard'))
    
    return render_template('booking_detail.html', booking=booking)

@app.route('/booking/cancel/<int:booking_id>', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    booking = get_booking(booking_id)
    if not booking:
        return jsonify({'success': False, 'error': 'Booking not found'})
    
    if booking.get('status') in ['completed', 'cancelled']:
        return jsonify({'success': False, 'error': 'Cannot cancel this booking'})
    
    updates = {
        'status': 'cancelled',
        'cancelled_at': datetime.utcnow().isoformat(),
        'cancellation_reason': request.json.get('reason', 'Customer cancelled')
    }
    
    if update_booking(booking_id, updates):
        return jsonify({'success': True, 'message': 'Booking cancelled successfully'})
    
    return jsonify({'success': False, 'error': 'Failed to cancel booking'})

@app.route('/admin')
def admin():
    bookings = load_bookings()
    
    # Calculate stats
    stats = {
        'total': len(bookings),
        'pending': len([b for b in bookings if b.get('status') == 'pending']),
        'confirmed': len([b for b in bookings if b.get('status') == 'confirmed']),
        'completed': len([b for b in bookings if b.get('status') == 'completed']),
        'cancelled': len([b for b in bookings if b.get('status') == 'cancelled']),
        'revenue': sum([float(b.get('amount', 0)) for b in bookings if b.get('status') == 'completed']),
        'today': len([b for b in bookings if b.get('created_at', '').startswith(datetime.now().strftime('%Y-%m-%d'))])
    }
    
    return render_template('admin.html', bookings=bookings, stats=stats)

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

        # Calculate price
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

@app.route('/api/status')
def api_status():
    bookings = load_bookings()
    return jsonify({
        'database': DB_TYPE,
        'connected': DB_CONNECTED,
        'bookings': len(bookings),
        'timestamp': datetime.utcnow().isoformat()
    })

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
