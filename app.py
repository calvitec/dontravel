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

def load_bus_seats(bus_id, date):
    """Get seat availability for a specific bus on a specific date"""
    if DB_CONNECTED:
        try:
            response = requests.get(
                f"{SUPABASE_URL}/rest/v1/bus_seats?bus_id=eq.{bus_id}&booking_date=eq.{date}",
                headers=SUPABASE_HEADERS,
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if data:
                    return data[0]
        except Exception as e:
            print(f"Error loading seats: {e}")
    
    # JSON fallback
    seats_data = load_json('bus_seats.json')
    for seat in seats_data:
        if seat.get('bus_id') == bus_id and seat.get('booking_date') == date:
            return seat
    
    return {'bus_id': bus_id, 'booking_date': date, 'booked_seats_list': [], 'booked_seats': 0}

def update_bus_seats(bus_id, date, booked_seats_list):
    """Update seat availability for a specific bus on a specific date"""
    if DB_CONNECTED:
        try:
            # Check if entry exists
            check = requests.get(
                f"{SUPABASE_URL}/rest/v1/bus_seats?bus_id=eq.{bus_id}&booking_date=eq.{date}",
                headers=SUPABASE_HEADERS,
                timeout=10
            )
            
            if check.status_code == 200 and check.json():
                # Update existing
                response = requests.patch(
                    f"{SUPABASE_URL}/rest/v1/bus_seats?bus_id=eq.{bus_id}&booking_date=eq.{date}",
                    headers=SUPABASE_HEADERS,
                    json={
                        'booked_seats_list': booked_seats_list,
                        'booked_seats': len(booked_seats_list),
                        'updated_at': datetime.utcnow().isoformat()
                    },
                    timeout=10
                )
            else:
                # Insert new
                response = requests.post(
                    f"{SUPABASE_URL}/rest/v1/bus_seats",
                    headers=SUPABASE_HEADERS,
                    json={
                        'bus_id': bus_id,
                        'booking_date': date,
                        'booked_seats_list': booked_seats_list,
                        'booked_seats': len(booked_seats_list)
                    },
                    timeout=10
                )
            return response.status_code in [200, 201, 204]
        except Exception as e:
            print(f"Update error: {e}")
            return False
    
    # JSON fallback
    seats_data = load_json('bus_seats.json')
    found = False
    for seat in seats_data:
        if seat.get('bus_id') == bus_id and seat.get('booking_date') == date:
            seat['booked_seats_list'] = booked_seats_list
            seat['booked_seats'] = len(booked_seats_list)
            found = True
            break
    
    if not found:
        seats_data.append({
            'bus_id': bus_id,
            'booking_date': date,
            'booked_seats_list': booked_seats_list,
            'booked_seats': len(booked_seats_list)
        })
    
    save_json('bus_seats.json', seats_data)
    return True

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
                        # Get seat availability for the specific date
                        seat_data = load_bus_seats(bus.get('id'), date)
                        booked = seat_data.get('booked_seats', 0)
                        total = bus.get('total_seats', 40)
                        available = total - booked
                        if available >= passengers:
                            results.append({
                                'bus': bus,
                                'vehicle': vehicle,
                                'route': route,
                                'fare': bus.get('fare', route.get('base_fare', 1500)),
                                'available_seats': available,
                                'date': date
                            })
    
    return render_template('search_results.html', results=results, origin=origin, destination=destination, date=date, passengers=passengers)

@app.route('/booking/<int:bus_id>')
def booking_page(bus_id):
    bus = get_bus_by_id(bus_id)
    if not bus:
        flash('Bus not found', 'danger')
        return redirect(url_for('index'))
    
    # Get the date from query params or use today
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    
    vehicle = get_vehicle_by_id(bus.get('vehicle_id'))
    route = get_route_by_id(bus.get('route_id'))
    
    total_seats = bus.get('total_seats', 40)
    seat_data = load_bus_seats(bus_id, date)
    booked_seats_list = seat_data.get('booked_seats_list', [])
    
    seats = []
    for i in range(1, total_seats + 1):
        seat_id = str(i)
        is_booked = seat_id in booked_seats_list
        seats.append({
            'id': i,
            'number': i,
            'status': 'booked' if is_booked else 'available'
        })
    
    return render_template('booking.html', bus=bus, vehicle=vehicle, route=route, seats=seats, date=date)

@app.route('/api/book', methods=['POST'])
def create_booking():
    try:
        data = request.get_json()
        
        bus_id = data.get('bus_id')
        booking_date = data.get('booking_date', datetime.now().strftime('%Y-%m-%d'))
        passenger_name = data.get('passenger_name', '').strip()
        passenger_phone = data.get('passenger_phone', '').strip()
        passenger_email = data.get('passenger_email', '').strip()
        selected_seats = data.get('selected_seats', [])
        total_fare = data.get('total_fare', 0)
        payment_method = data.get('payment_method', 'mpesa')
        
        if not all([bus_id, passenger_name, passenger_phone, selected_seats]):
            return jsonify({'success': False, 'error': 'Please fill in all required fields'}), 400
        
        # Get current seat data for this date
        seat_data = load_bus_seats(bus_id, booking_date)
        booked_seats_list = seat_data.get('booked_seats_list', [])
        
        # Check if seats are still available
        for seat in selected_seats:
            if str(seat) in booked_seats_list:
                return jsonify({'success': False, 'error': f'Seat {seat} is already booked for {booking_date}. Please refresh and try again.'}), 400
        
        # Create new booked list
        new_booked_list = booked_seats_list.copy()
        for seat in selected_seats:
            if str(seat) not in new_booked_list:
                new_booked_list.append(str(seat))
        
        # Update bus seats for this date
        update_success = update_bus_seats(bus_id, booking_date, new_booked_list)
        if not update_success:
            return jsonify({'success': False, 'error': 'Failed to update seats. Please try again.'}), 500
        
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
            'booking_date': booking_date,
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
