from flask import Flask, request, jsonify, render_template, session, redirect, url_for, flash
from datetime import datetime, timedelta
import os
import uuid
import json
import requests
import traceback
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
    "Content-Type": "application/json",
    "Prefer": "return=representation"
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

def load_schedules():
    if DB_CONNECTED:
        try:
            response = requests.get(
                f"{SUPABASE_URL}/rest/v1/schedules?select=*",
                headers=SUPABASE_HEADERS,
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Error loading schedules: {e}")
    return load_json('schedules.json')

def load_bus_seats(bus_id, date):
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

    seats_data = load_json('bus_seats.json')
    for seat in seats_data:
        if seat.get('bus_id') == bus_id and seat.get('booking_date') == date:
            return seat

    return {'bus_id': bus_id, 'booking_date': date, 'booked_seats_list': [], 'booked_seats': 0}

def update_bus_seats(bus_id, date, booked_seats_list):
    if DB_CONNECTED:
        try:
            check = requests.get(
                f"{SUPABASE_URL}/rest/v1/bus_seats?bus_id=eq.{bus_id}&booking_date=eq.{date}",
                headers=SUPABASE_HEADERS,
                timeout=10
            )

            if check.status_code == 200 and check.json():
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
                if data:
                    return data[0]
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
                if data:
                    return data[0]
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
                if data:
                    return data[0]
        except:
            pass
    routes = load_json('routes.json')
    for route in routes:
        if str(route.get('id')) == str(route_id):
            return route
    return None

def get_schedule_by_bus_and_date(bus_id, date):
    if DB_CONNECTED:
        try:
            response = requests.get(
                f"{SUPABASE_URL}/rest/v1/schedules?bus_id=eq.{bus_id}&departure_date=eq.{date}&status=eq.available",
                headers=SUPABASE_HEADERS,
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if data:
                    return data[0]
        except Exception as e:
            print(f"Error getting schedule: {e}")
    
    # JSON fallback
    schedules = load_json('schedules.json')
    for s in schedules:
        if s.get('bus_id') == bus_id and s.get('departure_date') == date and s.get('status') == 'available':
            return s
    return None

def save_booking_to_supabase(booking_data):
    if not DB_CONNECTED:
        raise Exception("Supabase not connected")
    
    response = requests.post(
        f"{SUPABASE_URL}/rest/v1/bookings",
        headers=SUPABASE_HEADERS,
        json=booking_data,
        timeout=10
    )
    
    if response.status_code == 201:
        data = response.json()
        print(f"✅ Booking saved to Supabase: {booking_data.get('booking_ref')}")
        return data[0] if data else None
    else:
        error_msg = f"Status: {response.status_code}, Body: {response.text[:200]}"
        print(f"❌ Supabase insert failed: {error_msg}")
        raise Exception(f"Supabase insert failed: {error_msg}")

def get_booking_by_ref(booking_ref):
    print(f"🔍 Looking for booking: {booking_ref} in Supabase")
    
    if not DB_CONNECTED:
        print(f"❌ Supabase not connected")
        return None
    
    try:
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/bookings?booking_ref=eq.{booking_ref}",
            headers=SUPABASE_HEADERS,
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if data:
                print(f"✅ Found in Supabase: {booking_ref}")
                return data[0]
            else:
                print(f"ℹ️ Not found in Supabase: {booking_ref}")
        else:
            print(f"❌ Supabase error: {response.status_code}")
    except Exception as e:
        print(f"❌ Error checking Supabase: {e}")
    
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
    time_from = request.args.get('time_from', '')
    time_to = request.args.get('time_to', '')
    
    if not origin or not destination or not date:
        flash('Please fill in all search fields', 'warning')
        return redirect(url_for('index'))
    
    try:
        # 1. Find the route
        route = None
        routes = load_routes()
        for r in routes:
            if r.get('origin', '').lower().strip() == origin.lower().strip() and r.get('destination', '').lower().strip() == destination.lower().strip():
                route = r
                break
        
        if not route:
            flash('No route found for this destination', 'warning')
            return render_template('search_results.html', results=[], origin=origin, destination=destination, date=date, passengers=passengers)
        
        route_id = route.get('id')
        
        # 2. Get all buses for this route
        buses = load_buses()
        results = []
        
        for bus in buses:
            if bus.get('route_id') == route_id and bus.get('status') == 'active':
                bus_id = bus.get('id')
                
                # 3. Check if this bus has a schedule on the selected date
                schedule = get_schedule_by_bus_and_date(bus_id, date)
                if not schedule:
                    continue  # No schedule for this date
                
                # 4. Get vehicle info
                vehicle = get_vehicle_by_id(bus.get('vehicle_id'))
                if not vehicle:
                    continue
                
                # 5. Get seat availability
                booked_seats = 0
                if DB_CONNECTED:
                    try:
                        seat_response = requests.get(
                            f"{SUPABASE_URL}/rest/v1/bus_seats?schedule_id=eq.{schedule.get('id')}&booking_date=eq.{date}",
                            headers=SUPABASE_HEADERS,
                            timeout=10
                        )
                        if seat_response.status_code == 200 and seat_response.json():
                            seat_data = seat_response.json()[0]
                            booked_seats = seat_data.get('booked_seats', 0)
                    except:
                        booked_seats = 0
                else:
                    seat_data = load_bus_seats(bus_id, date)
                    booked_seats = seat_data.get('booked_seats', 0)
                
                total_seats = bus.get('total_seats', schedule.get('total_seats', 40))
                available_seats = total_seats - booked_seats
                
                # 6. Apply time filters if any
                dep_time = bus.get('departure_time', '')
                if time_from and dep_time:
                    if dep_time < time_from:
                        continue
                if time_to and dep_time:
                    if dep_time > time_to:
                        continue
                
                # 7. Check if enough seats available
                if available_seats >= passengers:
                    results.append({
                        'bus': bus,
                        'vehicle': vehicle,
                        'route': route,
                        'schedule': schedule,
                        'fare': bus.get('fare', route.get('base_fare', 500)),
                        'available_seats': available_seats,
                        'date': date
                    })
        
        # Sort results by departure time
        results.sort(key=lambda x: x['bus'].get('departure_time', '00:00'))
        
        return render_template('search_results.html', 
            results=results, 
            origin=origin, 
            destination=destination, 
            date=date, 
            passengers=passengers,
            time_from=time_from,
            time_to=time_to
        )
        
    except Exception as e:
        print(f"❌ Search error: {e}")
        traceback.print_exc()
        flash('An error occurred while searching. Please try again.', 'danger')
        return render_template('search_results.html', results=[], origin=origin, destination=destination, date=date, passengers=passengers)

@app.route('/booking/<int:bus_id>')
def booking_page(bus_id):
    bus = get_bus_by_id(bus_id)
    if not bus:
        flash('Bus not found', 'danger')
        return redirect(url_for('index'))
    
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    
    # Get schedule for this bus on this date
    schedule = get_schedule_by_bus_and_date(bus_id, date)
    
    if not schedule:
        flash('No schedule available for this date', 'warning')
        return redirect(url_for('index'))
    
    vehicle = get_vehicle_by_id(bus.get('vehicle_id'))
    route = get_route_by_id(bus.get('route_id'))
    
    total_seats = schedule.get('total_seats', bus.get('total_seats', 40))
    schedule_id = schedule.get('id')
    
    # Get booked seats from bus_seats
    booked_seats_list = []
    if DB_CONNECTED:
        try:
            response = requests.get(
                f"{SUPABASE_URL}/rest/v1/bus_seats?schedule_id=eq.{schedule_id}&booking_date=eq.{date}",
                headers=SUPABASE_HEADERS,
                timeout=10
            )
            if response.status_code == 200 and response.json():
                seat_data = response.json()[0]
                booked_seats_list = seat_data.get('booked_seats_list', [])
        except:
            pass
    else:
        seat_data = load_bus_seats(bus_id, date)
        booked_seats_list = seat_data.get('booked_seats_list', [])
    
    seats = []
    for i in range(1, total_seats + 1):
        seat_num = str(i)
        is_booked = seat_num in booked_seats_list
        seats.append({
            'id': i,
            'number': i,
            'status': 'booked' if is_booked else 'available'
        })
    
    return render_template('booking.html', 
        bus=bus,
        vehicle=vehicle,
        route=route,
        schedule=schedule,
        seats=seats,
        date=date,
        fare=bus.get('fare')
    )

@app.route('/api/book', methods=['POST'])
def create_booking():
    try:
        print("=" * 60)
        print("📥 INCOMING BOOKING REQUEST")
        
        data = request.get_json()
        print("📦 Data received:", data)
        
        bus_id = data.get('bus_id')
        booking_date = data.get('booking_date', datetime.now().strftime('%Y-%m-%d'))
        passenger_name = data.get('passenger_name', '').strip()
        passenger_phone = data.get('passenger_phone', '').strip()
        passenger_email = data.get('passenger_email', '').strip()
        selected_seats = data.get('selected_seats', [])
        total_fare = data.get('total_fare', 0)
        payment_method = data.get('payment_method', 'mpesa')
        
        print(f"🚌 Bus ID: {bus_id}")
        print(f"👤 Passenger: {passenger_name}")
        print(f"💺 Seats: {selected_seats}")
        print(f"📅 Date: {booking_date}")
        
        if not all([bus_id, passenger_name, passenger_phone, selected_seats]):
            return jsonify({'success': False, 'error': 'Please fill in all required fields'}), 400
        
        bus = get_bus_by_id(bus_id)
        if not bus:
            return jsonify({'success': False, 'error': 'Bus not found'}), 404
        
        # Get schedule for this date
        schedule = get_schedule_by_bus_and_date(bus_id, booking_date)
        
        if not schedule:
            return jsonify({'success': False, 'error': 'No schedule available for this date'}), 404
        
        schedule_id = schedule.get('id')
        
        # Get current booked seats
        booked_seats_list = []
        if DB_CONNECTED:
            try:
                response = requests.get(
                    f"{SUPABASE_URL}/rest/v1/bus_seats?schedule_id=eq.{schedule_id}&booking_date=eq.{booking_date}",
                    headers=SUPABASE_HEADERS,
                    timeout=10
                )
                if response.status_code == 200 and response.json():
                    seat_data = response.json()[0]
                    booked_seats_list = seat_data.get('booked_seats_list', [])
            except:
                pass
        
        # Check if seats are already booked
        for seat in selected_seats:
            if str(seat) in booked_seats_list:
                return jsonify({'success': False, 'error': f'Seat {seat} is already booked for {booking_date}'}), 400
        
        # Update booked seats
        new_booked_list = booked_seats_list.copy()
        for seat in selected_seats:
            seat = str(seat)
            if seat not in new_booked_list:
                new_booked_list.append(seat)
        
        # Update bus_seats
        if DB_CONNECTED:
            try:
                check = requests.get(
                    f"{SUPABASE_URL}/rest/v1/bus_seats?schedule_id=eq.{schedule_id}&booking_date=eq.{booking_date}",
                    headers=SUPABASE_HEADERS,
                    timeout=10
                )
                
                if check.status_code == 200 and check.json():
                    # Update existing
                    response = requests.patch(
                        f"{SUPABASE_URL}/rest/v1/bus_seats?schedule_id=eq.{schedule_id}&booking_date=eq.{booking_date}",
                        headers=SUPABASE_HEADERS,
                        json={
                            'booked_seats_list': new_booked_list,
                            'booked_seats': len(new_booked_list),
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
                            'schedule_id': schedule_id,
                            'booking_date': booking_date,
                            'booked_seats_list': new_booked_list,
                            'booked_seats': len(new_booked_list)
                        },
                        timeout=10
                    )
            except Exception as e:
                print(f"Error updating seats: {e}")
                return jsonify({'success': False, 'error': 'Failed to update seats'}), 500
        else:
            # JSON fallback
            update_bus_seats(bus_id, booking_date, new_booked_list)
        
        # Create booking
        booking_ref = generate_booking_ref()
        booking_id = generate_booking_id()
        
        booking_data = {
            'booking_id': booking_id,
            'booking_ref': booking_ref,
            'bus_id': bus_id,
            'schedule_id': schedule_id,
            'vehicle_id': bus.get('vehicle_id'),
            'route_id': bus.get('route_id'),
            'passenger_name': passenger_name,
            'passenger_phone': passenger_phone,
            'passenger_email': passenger_email,
            'selected_seats': selected_seats,
            'total_fare': total_fare,
            'booking_date': booking_date,
            'departure_date': booking_date,
            'departure_time': bus.get('departure_time'),
            'arrival_time': bus.get('arrival_time'),
            'status': 'confirmed',
            'payment_status': 'paid' if payment_method in ['mpesa', 'card'] else 'pending',
            'payment_method': payment_method,
            'created_at': datetime.utcnow().isoformat()
        }
        
        if DB_CONNECTED:
            save_booking_to_supabase(booking_data)
        else:
            # JSON fallback
            bookings = load_json('bookings.json')
            bookings.append(booking_data)
            save_json('bookings.json', bookings)
        
        print(f"✅ Booking created: {booking_ref}")
        print("=" * 60)
        
        return jsonify({
            'success': True,
            'message': 'Booking confirmed!',
            'booking_ref': booking_ref,
            'booking': booking_data
        }), 200
        
    except Exception as e:
        print(f"❌ BOOKING ERROR: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Booking failed: {str(e)}'
        }), 500

@app.route('/confirmation/<booking_ref>')
def confirmation(booking_ref):
    print(f"🔍 Looking for booking: {booking_ref}")
    booking = get_booking_by_ref(booking_ref)
    
    if not booking:
        print(f"❌ Booking not found: {booking_ref}")
        flash('Booking not found', 'danger')
        return redirect(url_for('index'))
    
    print(f"✅ Booking found: {booking}")
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
            flash('Invalid credentials. Please try again.', 'error')
            return redirect(url_for('admin_login'))
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash('Logged out successfully', 'success')
    return redirect(url_for('admin_login'))

@app.route('/admin')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        flash('Please login to access admin panel', 'error')
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
        'today_bookings': len([b for b in bookings if b.get('created_at', '').startswith(datetime.now().strftime('%Y-%m-%d'))]),
        'pending_payments': len([b for b in bookings if b.get('payment_status') == 'pending'])
    }
    
    return render_template('admin.html', 
        bookings=bookings, 
        vehicles=vehicles, 
        routes=routes, 
        buses=buses, 
        stats=stats,
        db_type=DB_TYPE,
        db_connected=DB_CONNECTED
    )

@app.route('/api/status')
def api_status():
    return jsonify({
        'database': DB_TYPE,
        'connected': DB_CONNECTED,
        'vehicles': len(load_vehicles()),
        'routes': len(load_routes()),
        'buses': len(load_buses()),
        'schedules': len(load_schedules()),
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
    
    # Show data counts
    vehicles = load_vehicles()
    routes = load_routes()
    buses = load_buses()
    schedules = load_schedules()
    bookings = load_bookings()
    
    print(f"📊 Vehicles: {len(vehicles)}")
    print(f"📊 Routes: {len(routes)}")
    print(f"📊 Buses: {len(buses)}")
    print(f"📊 Schedules: {len(schedules)}")
    print(f"📊 Bookings: {len(bookings)}")
    print("="*60)
    
    # Show some sample schedules
    if schedules:
        print("\n📅 Sample Schedules:")
        for s in schedules[:5]:
            print(f"  - Bus {s.get('bus_id')} on {s.get('departure_date')}: {s.get('available_seats')} seats")
    
    print("\n🚀 Starting server...")
    print("📍 http://localhost:5000")
    print("="*60)
    app.run(debug=True, host='0.0.0.0', port=5000)
