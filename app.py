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
            f"{SUPABASE_URL}/rest/v1/vehicles?select=count",
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

# ===== CREATE SAMPLE DATA IF NOT EXISTS =====
def create_sample_data():
    """Create sample vehicles, routes, and buses if they don't exist"""
    
    # Check if vehicles exist
    vehicles = load_json('vehicles.json')
    if not vehicles:
        print("📁 Creating sample vehicles...")
        sample_vehicles = [
            {
                "id": 1,
                "vehicle_id": "VEH-001",
                "vehicle_type": "Toyota Hiace",
                "vehicle_model": "Hiace Minibus",
                "registration": "KCA 123A",
                "color": "White",
                "capacity": 14,
                "features": {"seats": 14, "ac": True, "wifi": True, "tv": True},
                "image_url": "https://images.unsplash.com/photo-1544626331-e26879cd4d9b?w=600&h=400&fit=crop",
                "base_price": 3500,
                "status": "available"
            },
            {
                "id": 2,
                "vehicle_id": "VEH-002",
                "vehicle_type": "Executive Van",
                "vehicle_model": "Mercedes Sprinter",
                "registration": "KCB 456B",
                "color": "Black",
                "capacity": 8,
                "features": {"seats": 8, "ac": True, "wifi": True, "refreshments": True, "leather_seats": True},
                "image_url": "https://images.unsplash.com/photo-1580273916550-e323be2ae537?w=600&h=400&fit=crop",
                "base_price": 6500,
                "status": "available"
            },
            {
                "id": 3,
                "vehicle_id": "VEH-003",
                "vehicle_type": "Luxury SUV",
                "vehicle_model": "Land Cruiser V8",
                "registration": "KCC 789C",
                "color": "Black",
                "capacity": 7,
                "features": {"seats": 7, "ac": True, "wifi": True, "climate_control": True, "premium": True},
                "image_url": "https://images.unsplash.com/photo-1550355291-bbee04a5f9ba?w=600&h=400&fit=crop",
                "base_price": 5500,
                "status": "available"
            }
        ]
        save_json('vehicles.json', sample_vehicles)
    
    routes = load_json('routes.json')
    if not routes:
        print("📁 Creating sample routes...")
        sample_routes = [
            {"id": 1, "route_id": "RTE-001", "origin": "Nairobi", "destination": "Mombasa", "distance_km": 480, "duration_minutes": 480, "base_fare": 1500},
            {"id": 2, "route_id": "RTE-002", "origin": "Nairobi", "destination": "Kisumu", "distance_km": 350, "duration_minutes": 360, "base_fare": 1200},
            {"id": 3, "route_id": "RTE-003", "origin": "Nairobi", "destination": "Eldoret", "distance_km": 310, "duration_minutes": 300, "base_fare": 1000},
            {"id": 4, "route_id": "RTE-004", "origin": "Mombasa", "destination": "Nairobi", "distance_km": 480, "duration_minutes": 480, "base_fare": 1500},
            {"id": 5, "route_id": "RTE-005", "origin": "Kisumu", "destination": "Nairobi", "distance_km": 350, "duration_minutes": 360, "base_fare": 1200}
        ]
        save_json('routes.json', sample_routes)
    
    buses = load_json('buses.json')
    if not buses:
        print("📁 Creating sample buses...")
        sample_buses = [
            {"id": 1, "bus_id": "BUS-001", "company_name": "Don Travels Express", "route_id": 1, "vehicle_id": 1, "total_seats": 40, "booked_seats": 2, "fare": 1800, "departure_time": "07:00:00", "arrival_time": "15:00:00", "status": "active"},
            {"id": 2, "bus_id": "BUS-002", "company_name": "Don Travels Express", "route_id": 1, "vehicle_id": 1, "total_seats": 40, "booked_seats": 1, "fare": 1800, "departure_time": "14:00:00", "arrival_time": "22:00:00", "status": "active"},
            {"id": 3, "bus_id": "BUS-003", "company_name": "Don Travels Express", "route_id": 2, "vehicle_id": 1, "total_seats": 40, "booked_seats": 0, "fare": 1400, "departure_time": "08:00:00", "arrival_time": "14:00:00", "status": "active"},
            {"id": 4, "bus_id": "BUS-004", "company_name": "Don Travels Executive", "route_id": 1, "vehicle_id": 2, "total_seats": 8, "booked_seats": 1, "fare": 2500, "departure_time": "06:00:00", "arrival_time": "14:00:00", "status": "active"},
            {"id": 5, "bus_id": "BUS-005", "company_name": "Don Travels Executive", "route_id": 3, "vehicle_id": 2, "total_seats": 8, "booked_seats": 0, "fare": 2000, "departure_time": "09:00:00", "arrival_time": "14:00:00", "status": "active"},
            {"id": 6, "bus_id": "BUS-006", "company_name": "Don Travels Luxury", "route_id": 1, "vehicle_id": 3, "total_seats": 7, "booked_seats": 0, "fare": 3000, "departure_time": "07:30:00", "arrival_time": "15:30:00", "status": "active"}
        ]
        save_json('buses.json', sample_buses)

# ===== DATABASE FUNCTIONS =====
def load_vehicles():
    if DB_CONNECTED:
        try:
            response = requests.get(
                f"{SUPABASE_URL}/rest/v1/vehicles?select=*",
                headers=SUPABASE_HEADERS,
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
        except:
            pass
    return load_json('vehicles.json')

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

def load_drivers():
    if DB_CONNECTED:
        try:
            response = requests.get(
                f"{SUPABASE_URL}/rest/v1/drivers?select=*",
                headers=SUPABASE_HEADERS,
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
        except:
            pass
    return load_json('drivers.json')

def get_vehicle_by_id(vehicle_id):
    vehicles = load_vehicles()
    for vehicle in vehicles:
        if str(vehicle.get('id')) == str(vehicle_id):
            return vehicle
    return None

def get_route_by_id(route_id):
    routes = load_routes()
    for route in routes:
        if str(route.get('id')) == str(route_id):
            return route
    return None

def get_bus_by_id(bus_id):
    buses = load_buses()
    for bus in buses:
        if str(bus.get('id')) == str(bus_id):
            return bus
    return None

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
    bookings = load_json('bookings.json')
    bookings = [b for b in bookings if b.get('id') != booking_id]
    save_json('bookings.json', bookings)
    return True

# ===== HELPERS =====
def generate_booking_ref():
    return 'BC-' + str(uuid.uuid4().hex[:8]).upper()

def generate_booking_id():
    return 'BK-' + str(uuid.uuid4().hex[:8]).upper()

# ===== ADMIN AUTH =====
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'dontravels2026')

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
    # Create sample data if needed
    create_sample_data()
    
    vehicles = load_vehicles()
    routes = load_routes()
    
    # Get today's date and max date (30 days from now)
    today = datetime.now().strftime('%Y-%m-%d')
    max_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
    
    return render_template('index.html', 
        vehicles=vehicles, 
        routes=routes,
        today=today,
        max_date=max_date
    )

@app.route('/search')
def search_results():
    origin = request.args.get('origin', '').strip()
    destination = request.args.get('destination', '').strip()
    date = request.args.get('date', '')
    passengers = int(request.args.get('passengers', 1))
    
    # Create sample data if needed
    create_sample_data()
    
    vehicles = load_vehicles()
    routes = load_routes()
    buses = load_buses()
    
    # Debug: Print what we're searching for
    print(f"🔍 Searching: {origin} → {destination}")
    print(f"📊 Routes found: {len(routes)}")
    print(f"📊 Buses found: {len(buses)}")
    
    results = []
    
    # First, find matching routes
    for route in routes:
        route_origin = route.get('origin', '').lower().strip()
        route_dest = route.get('destination', '').lower().strip()
        search_origin = origin.lower().strip()
        search_dest = destination.lower().strip()
        
        # Check if route matches (case insensitive)
        if route_origin == search_origin and route_dest == search_dest:
            print(f"✅ Found matching route: {route.get('origin')} → {route.get('destination')}")
            
            # Find buses for this route
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
                            print(f"   ✅ Added bus {bus.get('bus_id')} with {available} seats")
    
    print(f"📊 Found {len(results)} results")
    
    # If no results, try partial match
    if not results:
        print("🔄 No exact matches, trying partial matches...")
        for route in routes:
            route_origin = route.get('origin', '').lower()
            route_dest = route.get('destination', '').lower()
            if search_origin in route_origin and search_dest in route_dest:
                print(f"✅ Found partial match: {route.get('origin')} → {route.get('destination')}")
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
    
    return render_template('search_results.html', 
        results=results, 
        origin=origin, 
        destination=destination, 
        date=date, 
        passengers=passengers)

@app.route('/booking/<int:bus_id>')
def booking_page(bus_id):
    bus = get_bus_by_id(bus_id)
    if not bus:
        flash('Bus not found', 'danger')
        return redirect(url_for('index'))
    
    vehicle = get_vehicle_by_id(bus.get('vehicle_id'))
    route = get_route_by_id(bus.get('route_id'))
    
    # Generate seat layout
    total_seats = bus.get('total_seats', 40)
    booked_seats = bus.get('booked_seats', 0)
    
    seats = []
    for i in range(1, total_seats + 1):
        seat = {
            'id': i,
            'number': i,
            'status': 'booked' if i <= booked_seats else 'available'
        }
        seats.append(seat)
    
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
        
        bus = get_bus_by_id(bus_id)
        if not bus:
            return jsonify({'success': False, 'error': 'Bus not found'}), 404
        
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
        
        # Update bus booked seats
        if DB_CONNECTED:
            try:
                new_booked = bus.get('booked_seats', 0) + len(selected_seats)
                requests.patch(
                    f"{SUPABASE_URL}/rest/v1/buses?id=eq.{bus_id}",
                    headers=SUPABASE_HEADERS,
                    json={'booked_seats': new_booked},
                    timeout=10
                )
            except:
                pass
        else:
            buses = load_json('buses.json')
            for b in buses:
                if str(b.get('id')) == str(bus_id):
                    b['booked_seats'] = b.get('booked_seats', 0) + len(selected_seats)
                    save_json('buses.json', buses)
                    break
        
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

@app.route('/api/vehicles')
def get_vehicles():
    vehicles = load_vehicles()
    return jsonify({'vehicles': vehicles})

@app.route('/api/routes')
def get_routes():
    routes = load_routes()
    return jsonify({'routes': routes})

@app.route('/api/buses')
def get_buses():
    buses = load_buses()
    return jsonify({'buses': buses})

@app.route('/api/bookings')
def get_bookings():
    bookings = load_bookings()
    return jsonify({'bookings': bookings})

@app.route('/api/drivers')
def get_drivers():
    drivers = load_drivers()
    return jsonify({'drivers': drivers})

@app.route('/api/status')
def api_status():
    return jsonify({
        'database': DB_TYPE,
        'connected': DB_CONNECTED,
        'vehicles': len(load_vehicles()),
        'routes': len(load_routes()),
        'buses': len(load_buses()),
        'bookings': len(load_bookings()),
        'drivers': len(load_drivers()),
        'timestamp': datetime.utcnow().isoformat()
    })

@app.route('/api/reconnect')
def reconnect_db():
    global DB_CONNECTED
    DB_CONNECTED = test_supabase_connection()
    return jsonify({'connected': DB_CONNECTED})

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
    vehicles = load_vehicles()
    routes = load_routes()
    buses = load_buses()
    drivers = load_drivers()
    
    stats = {
        'total_bookings': len(bookings),
        'total_revenue': sum([float(b.get('total_fare', 0)) for b in bookings if b.get('status') == 'confirmed']),
        'total_vehicles': len(vehicles),
        'total_routes': len(routes),
        'total_buses': len(buses),
        'total_drivers': len(drivers),
        'today_bookings': len([b for b in bookings if b.get('created_at', '').startswith(datetime.now().strftime('%Y-%m-%d'))]),
        'pending_payments': len([b for b in bookings if b.get('payment_status') == 'pending'])
    }
    
    return render_template('admin.html', 
        bookings=bookings, 
        vehicles=vehicles, 
        routes=routes, 
        buses=buses, 
        drivers=drivers,
        stats=stats,
        db_type=DB_TYPE,
        db_connected=DB_CONNECTED
    )

@app.route('/admin/bookings/<int:booking_id>/status', methods=['PUT'])
@admin_required
def admin_update_booking_status(booking_id):
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        if new_status not in ['confirmed', 'cancelled', 'completed']:
            return jsonify({'success': False, 'error': 'Invalid status'}), 400
        
        update_booking(booking_id, {'status': new_status})
        
        return jsonify({'success': True, 'message': f'Status updated to {new_status}'}), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/bookings/<int:booking_id>', methods=['DELETE'])
@admin_required
def admin_delete_booking(booking_id):
    try:
        delete_booking(booking_id)
        return jsonify({'success': True, 'message': 'Booking deleted'}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ===== VERCEL HANDLER =====
def handler(request, context):
    return app(request, context)

if __name__ == '__main__':
    # Create sample data on startup
    create_sample_data()
    
    print("\n" + "="*60)
    print("🚌 DON TRAVELS - Complete Bus Booking System")
    print("="*60)
    print(f"📁 Database: {DB_TYPE}")
    print(f"🔗 Connected: {'✅ YES' if DB_CONNECTED else '❌ NO'}")
    
    # Show data counts
    vehicles = load_vehicles()
    routes = load_routes()
    buses = load_buses()
    print(f"📊 Vehicles: {len(vehicles)}, Routes: {len(routes)}, Buses: {len(buses)}")
    print("="*60)
    app.run(debug=True, host='0.0.0.0', port=5000)
