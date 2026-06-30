from flask import Flask, request, jsonify, render_template, session, redirect, url_for, flash
from datetime import datetime, timedelta
import os
import uuid
import json
import requests
from functools import wraps

app = Flask(__name__)
app.secret_key = 'buscar-secret-key-2026'
app.permanent_session_lifetime = timedelta(days=7)

# ===== SUPABASE CONFIGURATION =====
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
            f"{SUPABASE_URL}/rest/v1/buses?select=count",
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

# ===== JSON FALLBACK =====
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
def load_buses():
    if DB_CONNECTED:
        try:
            response = requests.get(
                f"{SUPABASE_URL}/rest/v1/buses?select=*",
                headers=SUPABASE_HEADERS,
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
        except:
            pass
    return load_json('buses.json')

def load_routes():
    if DB_CONNECTED:
        try:
            response = requests.get(
                f"{SUPABASE_URL}/rest/v1/routes?select=*",
                headers=SUPABASE_HEADERS,
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
        except:
            pass
    return load_json('routes.json')

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
    return load_json('bookings.json')

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
    bookings = load_json('bookings.json')
    booking_data['id'] = len(bookings) + 1
    bookings.append(booking_data)
    save_json('bookings.json', bookings)
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
    bookings = load_json('bookings.json')
    for booking in bookings:
        if booking.get('id') == booking_id:
            booking.update(updates)
            save_json('bookings.json', bookings)
            return True
    return False

def get_booking_by_ref(booking_ref):
    if DB_CONNECTED:
        try:
            response = requests.get(
                f"{SUPABASE_URL}/rest/v1/bookings?booking_ref=eq.{booking_ref}",
                headers=SUPABASE_HEADERS,
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                return data[0] if data else None
        except:
            pass
    bookings = load_json('bookings.json')
    for booking in bookings:
        if booking.get('booking_ref') == booking_ref:
            return booking
    return None

# ===== HELPER FUNCTIONS =====
def generate_booking_ref():
    return 'BC-' + str(uuid.uuid4().hex[:8]).upper()

def generate_seat_layout(total_seats=40):
    """Generate a seat layout with rows"""
    seats = []
    for row in range(1, 11):  # 10 rows
        for side in ['L', 'R']:  # Left and Right side
            for seat_num in range(1, 3):  # 2 seats per side
                seat_id = f"{row}{side}{seat_num}"
                seats.append({
                    'id': seat_id,
                    'row': row,
                    'side': side,
                    'number': seat_num,
                    'status': 'available'  # available, booked, selected
                })
    return seats

# ===== ADMIN AUTH =====
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'buscar2026')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash('Please login to access admin panel', 'warning')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# ===== ROUTES =====

@app.route('/')
def index():
    routes = load_routes()
    return render_template('index.html', routes=routes)

@app.route('/search')
def search_results():
    origin = request.args.get('origin', '')
    destination = request.args.get('destination', '')
    date = request.args.get('date', '')
    passengers = int(request.args.get('passengers', 1))
    
    buses = load_buses()
    routes = load_routes()
    
    # Filter buses based on search
    results = []
    for bus in buses:
        # Check if bus route matches
        route = next((r for r in routes if r.get('id') == bus.get('route_id')), {})
        if route:
            if route.get('origin', '').lower() == origin.lower() and route.get('destination', '').lower() == destination.lower():
                # Check date and availability
                bus['route'] = route
                bus['available_seats'] = bus.get('total_seats', 40) - bus.get('booked_seats', 0)
                if bus['available_seats'] >= passengers:
                    results.append(bus)
    
    return render_template('search_results.html', results=results, origin=origin, destination=destination, date=date, passengers=passengers)

@app.route('/booking/<bus_id>')
def booking(bus_id):
    buses = load_buses()
    bus = next((b for b in buses if str(b.get('id')) == bus_id), None)
    
    if not bus:
        flash('Bus not found', 'danger')
        return redirect(url_for('index'))
    
    # Generate seat layout
    seats = generate_seat_layout(bus.get('total_seats', 40))
    bus['seats'] = seats
    
    return render_template('booking.html', bus=bus)

@app.route('/api/book', methods=['POST'])
def create_booking():
    try:
        data = request.get_json()
        
        bus_id = data.get('bus_id')
        passenger_name = data.get('passenger_name', '').strip()
        passenger_phone = data.get('passenger_phone', '').strip()
        passenger_email = data.get('passenger_email', '').strip()
        selected_seats = data.get('selected_seats', [])
        total_fare = data.get('total_fare', 0)
        
        if not all([bus_id, passenger_name, passenger_phone, selected_seats]):
            return jsonify({'success': False, 'error': 'Please fill in all required fields'}), 400
        
        # Generate booking reference
        booking_ref = generate_booking_ref()
        
        booking_data = {
            'booking_ref': booking_ref,
            'bus_id': bus_id,
            'passenger_name': passenger_name,
            'passenger_phone': passenger_phone,
            'passenger_email': passenger_email,
            'selected_seats': selected_seats,
            'total_fare': total_fare,
            'status': 'confirmed',
            'payment_status': 'pending',
            'created_at': datetime.utcnow().isoformat(),
            'payment_method': data.get('payment_method', 'cash')
        }
        
        save_booking(booking_data)
        
        # Update bus booked seats
        buses = load_buses()
        for bus in buses:
            if str(bus.get('id')) == bus_id:
                bus['booked_seats'] = bus.get('booked_seats', 0) + len(selected_seats)
                if DB_CONNECTED:
                    try:
                        requests.patch(
                            f"{SUPABASE_URL}/rest/v1/buses?id=eq.{bus_id}",
                            headers=SUPABASE_HEADERS,
                            json={'booked_seats': bus['booked_seats']},
                            timeout=10
                        )
                    except:
                        pass
                break
        save_json('buses.json', buses)
        
        return jsonify({
            'success': True,
            'message': 'Booking confirmed!',
            'booking_ref': booking_ref,
            'booking': booking_data
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/confirmation/<booking_ref>')
def confirmation(booking_ref):
    booking = get_booking_by_ref(booking_ref)
    if not booking:
        flash('Booking not found', 'danger')
        return redirect(url_for('index'))
    
    return render_template('confirmation.html', booking=booking)

@app.route('/check-booking', methods=['GET', 'POST'])
def check_booking():
    if request.method == 'POST':
        booking_ref = request.form.get('booking_ref', '').strip()
        phone = request.form.get('phone', '').strip()
        
        booking = get_booking_by_ref(booking_ref)
        if booking and booking.get('passenger_phone') == phone:
            return render_template('check_booking.html', booking=booking)
        else:
            flash('No booking found. Please check your details.', 'danger')
    
    return render_template('check_booking.html')

# ===== ADMIN ROUTES =====

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            flash('Login successful!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials', 'danger')
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash('Logged out successfully', 'info')
    return redirect(url_for('admin_login'))

@app.route('/admin')
@admin_required
def admin_dashboard():
    bookings = load_bookings()
    buses = load_buses()
    routes = load_routes()
    
    stats = {
        'total_bookings': len(bookings),
        'total_revenue': sum([float(b.get('total_fare', 0)) for b in bookings if b.get('status') == 'confirmed']),
        'total_buses': len(buses),
        'total_routes': len(routes),
        'today_bookings': len([b for b in bookings if b.get('created_at', '').startswith(datetime.now().strftime('%Y-%m-%d'))]),
        'pending_payments': len([b for b in bookings if b.get('payment_status') == 'pending'])
    }
    
    return render_template('admin.html', bookings=bookings, buses=buses, routes=routes, stats=stats)

@app.route('/admin/buses')
@admin_required
def admin_buses():
    buses = load_buses()
    return render_template('admin_buses.html', buses=buses)

@app.route('/admin/routes')
@admin_required
def admin_routes():
    routes = load_routes()
    return render_template('admin_routes.html', routes=routes)

@app.route('/admin/bookings')
@admin_required
def admin_bookings():
    bookings = load_bookings()
    return render_template('admin_bookings.html', bookings=bookings)

# ===== VERCEL HANDLER =====
def handler(request, context):
    return app(request, context)

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚌 BUSCAR - Complete Bus Booking System")
    print("="*60)
    print(f"📁 Database: {DB_TYPE}")
    print(f"🔗 Connected: {'✅ YES' if DB_CONNECTED else '❌ NO'}")
    print("="*60)
    app.run(debug=True, host='0.0.0.0', port=5000)
