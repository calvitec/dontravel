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
    else:
        print("⚠️ Supabase connection failed - using JSON storage")
except Exception as e:
    print(f"⚠️ Supabase error: {e}")
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
def load_vehicles():
    if DB_CONNECTED:
        try:
            response = requests.get(f"{SUPABASE_URL}/rest/v1/vehicles?select=*", headers=SUPABASE_HEADERS, timeout=10)
            if response.status_code == 200:
                return response.json()
        except:
            pass
    return load_json('vehicles.json')

def load_routes():
    if DB_CONNECTED:
        try:
            response = requests.get(f"{SUPABASE_URL}/rest/v1/routes?select=*", headers=SUPABASE_HEADERS, timeout=10)
            if response.status_code == 200:
                return response.json()
        except:
            pass
    return load_json('routes.json')

def load_buses():
    if DB_CONNECTED:
        try:
            response = requests.get(f"{SUPABASE_URL}/rest/v1/buses?select=*", headers=SUPABASE_HEADERS, timeout=10)
            if response.status_code == 200:
                return response.json()
        except:
            pass
    return load_json('buses.json')

def load_bookings():
    if DB_CONNECTED:
        try:
            response = requests.get(f"{SUPABASE_URL}/rest/v1/bookings?select=*&order=created_at.desc", headers=SUPABASE_HEADERS, timeout=10)
            if response.status_code == 200:
                return response.json()
        except:
            pass
    return load_json('bookings.json')

def get_bus_by_id(bus_id):
    if DB_CONNECTED:
        try:
            response = requests.get(f"{SUPABASE_URL}/rest/v1/buses?id=eq.{bus_id}", headers=SUPABASE_HEADERS, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data[0] if data else None
        except:
            pass
    buses = load_json('buses.json')
    for bus in buses:
        if str(bus.get('id')) == str(bus_id):
            return bus
    return None

def get_vehicle_by_id(vehicle_id):
    if DB_CONNECTED:
        try:
            response = requests.get(f"{SUPABASE_URL}/rest/v1/vehicles?id=eq.{vehicle_id}", headers=SUPABASE_HEADERS, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data[0] if data else None
        except:
            pass
    vehicles = load_json('vehicles.json')
    for vehicle in vehicles:
        if str(vehicle.get('id')) == str(vehicle_id):
            return vehicle
    return None

def get_route_by_id(route_id):
    if DB_CONNECTED:
        try:
            response = requests.get(f"{SUPABASE_URL}/rest/v1/routes?id=eq.{route_id}", headers=SUPABASE_HEADERS, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data[0] if data else None
        except:
            pass
    routes = load_json('routes.json')
    for route in routes:
        if str(route.get('id')) == str(route_id):
            return route
    return None

def update_bus_seats(bus_id, booked_seats_list):
    """Update bus booked seats in database"""
    if DB_CONNECTED:
        try:
            response = requests.patch(
                f"{SUPABASE_URL}/rest/v1/buses?id=eq.{bus_id}",
                headers=SUPABASE_HEADERS,
                json={
                    'booked_seats_list': booked_seats_list,
                    'booked_seats': len(booked_seats_list)
                },
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Update error: {e}")
            return False
    return False

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
        except Exception as e:
            print(f"Save booking error: {e}")
            pass
    bookings = load_json('bookings.json')
    booking_data['id'] = len(bookings) + 1
    bookings.append(booking_data)
    save_json('bookings.json', bookings)
    return booking_data['id']

def get_booking_by_ref(booking_ref):
    if DB_CONNECTED:
        try:
            response = requests.get(f"{SUPABASE_URL}/rest/v1/bookings?booking_ref=eq.{booking_ref}", headers=SUPABASE_HEADERS, timeout=10)
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

def generate_booking_ref():
    return 'BC-' + str(uuid.uuid4().hex[:8]).upper()

def generate_booking_id():
    return 'BK-' + str(uuid.uuid4().hex[:8]).upper()

# ===== ROUTES =====

@app.route('/')
def index():
    vehicles = load_vehicles()
    routes = load_routes()
    today = datetime.now().strftime('%Y-%m-%d')
    max_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
    return render_template('index.html', vehicles=vehicles, routes=routes, today=today, max_date=max_date)

@app.route('/search')
def search_results():
    origin = request.args.get('origin', '').strip()
    destination = request.args.get('destination', '').strip()
    date = request.args.get('date', '')
    passengers = int(request.args.get('passengers', 1))
    
    buses = load_buses()
    routes = load_routes()
    
    results = []
    for route in routes:
        if route.get('origin', '').lower().strip() == origin.lower().strip() and route.get('destination', '').lower().strip() == destination.lower().strip():
            for bus in buses:
                if bus.get('route_id') == route.get('id'):
                    vehicle = get_vehicle_by_id(bus.get('vehicle_id'))
                    if vehicle:
                        available = bus.get('total_seats', 40) - bus.get('booked_seats', 0)
                        if available >= passengers:
                            results.append({
                                'bus': bus,
                                'vehicle': vehicle,
                                'route': route,
                                'fare': bus.get('fare', route.get('base_fare', 1500)),
                                'available_seats': available
                            })
    
    return render_template('search_results.html', results=results, origin=origin, destination=destination, date=date, passengers=passengers)

@app.route('/booking/<int:bus_id>')
def booking_page(bus_id):
    # Force refresh bus data from database
    bus = get_bus_by_id(bus_id)
    if not bus:
        flash('Bus not found', 'danger')
        return redirect(url_for('index'))
    
    vehicle = get_vehicle_by_id(bus.get('vehicle_id'))
    route = get_route_by_id(bus.get('route_id'))
    
    total_seats = bus.get('total_seats', 40)
    booked_seats_list = bus.get('booked_seats_list', [])
    
    # Debug: Print booked seats
    print(f"Bus {bus_id} - Booked seats: {booked_seats_list}")
    
    seats = []
    for i in range(1, total_seats + 1):
        seat_id = str(i)
        is_booked = seat_id in booked_seats_list
        seats.append({
            'id': i,
            'number': i,
            'status': 'booked' if is_booked else 'available'
        })
    
    return render_template('booking.html', bus=bus, vehicle=vehicle, route=route, seats=seats)

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
        payment_method = data.get('payment_method', 'mpesa')
        
        if not all([bus_id, passenger_name, passenger_phone, selected_seats]):
            return jsonify({'success': False, 'error': 'Please fill in all required fields'}), 400
        
        # Get current bus data
        bus = get_bus_by_id(bus_id)
        if not bus:
            return jsonify({'success': False, 'error': 'Bus not found'}), 404
        
        # Get current booked seats
        booked_seats_list = bus.get('booked_seats_list', [])
        
        # Check if seats are still available
        for seat in selected_seats:
            if str(seat) in booked_seats_list:
                return jsonify({'success': False, 'error': f'Seat {seat} is already booked. Please refresh and try again.'}), 400
        
        # Create new booked list
        new_booked_list = booked_seats_list.copy()
        for seat in selected_seats:
            if str(seat) not in new_booked_list:
                new_booked_list.append(str(seat))
        
        # Update bus in database
        update_success = update_bus_seats(bus_id, new_booked_list)
        if not update_success and DB_CONNECTED:
            # Try JSON fallback
            buses = load_json('buses.json')
            for b in buses:
                if str(b.get('id')) == str(bus_id):
                    b['booked_seats_list'] = new_booked_list
                    b['booked_seats'] = len(new_booked_list)
                    save_json('buses.json', buses)
                    break
        
        # Create booking
        booking_ref = generate_booking_ref()
        booking_id = generate_booking_id()
        
        booking_data = {
            'booking_id': booking_id,
            'booking_ref': booking_ref,
            'bus_id': bus_id,
            'vehicle_id': bus.get('vehicle_id'),
            'route_id': bus.get('route_id'),
            'passenger_name': passenger_name,
            'passenger_phone': passenger_phone,
            'passenger_email': passenger_email,
            'selected_seats': selected_seats,
            'total_fare': total_fare,
            'status': 'confirmed',
            'payment_status': 'paid' if payment_method in ['mpesa', 'card'] else 'pending',
            'payment_method': payment_method,
            'created_at': datetime.utcnow().isoformat()
        }
        
        save_booking(booking_data)
        
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

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == 'admin' and password == 'dontravels2026':
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
def admin_dashboard():
    if not session.get('admin_logged_in'):
        flash('Please login to access admin panel', 'warning')
        return redirect(url_for('admin_login'))
    
    bookings = load_bookings()
    vehicles = load_vehicles()
    routes = load_routes()
    buses = load_buses()
    
    stats = {
        'total_bookings': len(bookings),
        'total_revenue': sum([float(b.get('total_fare', 0)) for b in bookings if b.get('status') == 'confirmed']),
        'total_vehicles': len(vehicles),
        'total_routes': len(routes),
        'total_buses': len(buses),
        'today_bookings': len([b for b in bookings if b.get('created_at', '').startswith(datetime.now().strftime('%Y-%m-%d'))])
    }
    
    return render_template('admin.html', bookings=bookings, vehicles=vehicles, routes=routes, buses=buses, stats=stats, db_type=DB_TYPE, db_connected=DB_CONNECTED)

@app.route('/api/status')
def api_status():
    return jsonify({
        'database': DB_TYPE,
        'connected': DB_CONNECTED,
        'vehicles': len(load_vehicles()),
        'routes': len(load_routes()),
        'buses': len(load_buses()),
        'bookings': len(load_bookings()),
        'timestamp': datetime.utcnow().isoformat()
    })

@app.route('/api/reconnect')
def reconnect_db():
    global DB_CONNECTED
    DB_CONNECTED = test_supabase_connection()
    return jsonify({'connected': DB_CONNECTED})

# ===== VERCEL HANDLER =====
def handler(request, context):
    return app(request, context)

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚌 DON TRAVELS - Complete Bus Booking System")
    print("="*60)
    print(f"📁 Database: {DB_TYPE}")
    print(f"🔗 Connected: {'✅ YES' if DB_CONNECTED else '❌ NO'}")
    print("="*60)
    app.run(debug=True, host='0.0.0.0', port=5000)
