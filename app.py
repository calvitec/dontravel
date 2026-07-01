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

# ===== HELPERS FOR LENIENT STATUS MATCHING =====
def bus_is_active(bus):
    """
    Treat a bus as active unless it's explicitly marked inactive/cancelled/disabled.
    Missing status, None, or unexpected casing no longer hides the bus.
    """
    status = bus.get('status')
    if status is None or status == '':
        return True
    return str(status).strip().lower() not in ('inactive', 'cancelled', 'canceled', 'disabled', 'suspended')

def schedule_is_available(schedule):
    """
    Treat a schedule as available unless it's explicitly marked full/cancelled/closed.
    Missing status, None, or unexpected casing no longer hides the schedule.
    """
    status = schedule.get('status')
    if status is None or status == '':
        return True
    return str(status).strip().lower() not in ('full', 'cancelled', 'canceled', 'closed', 'unavailable')

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
    """
    Relaxed version: fetch by bus_id + date only (no status filter in the query),
    then apply a lenient status check in Python so missing/odd status values
    don't hide otherwise-valid schedules.
    """
    if DB_CONNECTED:
        try:
            response = requests.get(
                f"{SUPABASE_URL}/rest/v1/schedules?bus_id=eq.{bus_id}&departure_date=eq.{date}",
                headers=SUPABASE_HEADERS,
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                for s in data:
                    if schedule_is_available(s):
                        return s
                if data:
                    # Nothing passed the lenient check, but rows exist for this bus/date.
                    # Return the first one anyway rather than reporting "no schedule".
                    return data[0]
        except Exception as e:
            print(f"Error getting schedule: {e}")

    # JSON fallback
    schedules = load_json('schedules.json')
    matches = [s for s in schedules if s.get('bus_id') == bus_id and s.get('departure_date') == date]
    for s in matches:
        if schedule_is_available(s):
            return s
    return matches[0] if matches else None

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

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return jsonify({'success': False, 'error': 'Unauthorized. Please log in again.'}), 401
        return f(*args, **kwargs)
    return decorated

# ===== GENERIC SUPABASE CRUD (used by admin management routes) =====
def sb_select(table, query=""):
    if DB_CONNECTED:
        try:
            url = f"{SUPABASE_URL}/rest/v1/{table}?select=*"
            if query:
                url += f"&{query}"
            r = requests.get(url, headers=SUPABASE_HEADERS, timeout=10)
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            print(f"sb_select error ({table}): {e}")
    return load_json(f'{table}.json')

def sb_insert(table, data):
    if DB_CONNECTED:
        r = requests.post(f"{SUPABASE_URL}/rest/v1/{table}", headers=SUPABASE_HEADERS, json=data, timeout=10)
        if r.status_code == 201:
            res = r.json()
            return res[0] if res else data
        raise Exception(f"Supabase insert failed ({r.status_code}): {r.text[:300]}")
    items = load_json(f'{table}.json')
    data = dict(data)
    data['id'] = max([int(i.get('id', 0) or 0) for i in items], default=0) + 1
    items.append(data)
    save_json(f'{table}.json', items)
    return data

def sb_update(table, id_value, data):
    if DB_CONNECTED:
        r = requests.patch(f"{SUPABASE_URL}/rest/v1/{table}?id=eq.{id_value}", headers=SUPABASE_HEADERS, json=data, timeout=10)
        if r.status_code in (200, 204):
            return True
        raise Exception(f"Supabase update failed ({r.status_code}): {r.text[:300]}")
    items = load_json(f'{table}.json')
    for item in items:
        if str(item.get('id')) == str(id_value):
            item.update(data)
    save_json(f'{table}.json', items)
    return True

def sb_delete(table, id_value):
    if DB_CONNECTED:
        r = requests.delete(f"{SUPABASE_URL}/rest/v1/{table}?id=eq.{id_value}", headers=SUPABASE_HEADERS, timeout=10)
        if r.status_code in (200, 204):
            return True
        raise Exception(f"Supabase delete failed ({r.status_code}): {r.text[:300]}")
    items = load_json(f'{table}.json')
    items = [i for i in items if str(i.get('id')) != str(id_value)]
    save_json(f'{table}.json', items)
    return True

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

        # 2. Get all buses for this route (lenient active check — missing/odd status no longer hides a bus)
        buses = load_buses()
        results = []

        for bus in buses:
            if bus.get('route_id') != route_id:
                continue
            if not bus_is_active(bus):
                continue

            bus_id = bus.get('id')

            # 3. Check if this bus has a schedule on the selected date (lenient — falls back to
            #    any matching row if none is explicitly "available")
            schedule = get_schedule_by_bus_and_date(bus_id, date)
            if not schedule:
                continue  # No schedule row at all for this bus/date

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

    # Get schedule for this bus on this date (lenient)
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

@app.route('/debug/search')
def debug_search():
    """Debug route to see what's in the database"""
    try:
        # Check what's in schedules
        schedules = load_schedules()

        # Check a specific date
        date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
        buses = load_buses()
        routes = load_routes()

        debug_info = {
            'total_schedules': len(schedules),
            'schedules_sample': schedules[:5] if schedules else [],
            'buses_sample': buses[:5] if buses else [],
            'buses_count': len(buses),
            'routes_count': len(routes),
            'date_checked': date,
            'schedules_for_date': []
        }

        # Find schedules for the date
        for s in schedules:
            if s.get('departure_date') == date:
                bus = get_bus_by_id(s.get('bus_id'))
                if bus:
                    route = get_route_by_id(bus.get('route_id'))
                    debug_info['schedules_for_date'].append({
                        'bus_id': s.get('bus_id'),
                        'bus_status': bus.get('status'),
                        'schedule_status': s.get('status'),
                        'route': f"{route.get('origin')} → {route.get('destination')}" if route else 'Unknown',
                        'departure_time': bus.get('departure_time'),
                        'available_seats': s.get('available_seats')
                    })

        return jsonify(debug_info)
    except Exception as e:
        return jsonify({'error': str(e)})

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

        # Get schedule for this date (lenient)
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

# ================================================================
# ===== ADMIN MANAGEMENT API =====
# ================================================================

# ---------- Bookings management ----------
@app.route('/admin/api/bookings', methods=['GET'])
@admin_required
def admin_api_bookings():
    bookings = load_bookings()
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    status = request.args.get('status', 'all')
    q = request.args.get('q', '').lower().strip()

    def matches(b):
        bd = b.get('booking_date', '') or ''
        if date_from and bd < date_from:
            return False
        if date_to and bd > date_to:
            return False
        if status and status != 'all' and (b.get('status') or '').lower() != status.lower():
            return False
        if q:
            haystack = ' '.join([
                str(b.get('booking_ref', '')),
                str(b.get('passenger_name', '')),
                str(b.get('passenger_phone', '')),
                str(b.get('passenger_email', ''))
            ]).lower()
            if q not in haystack:
                return False
        return True

    filtered = [b for b in bookings if matches(b)]
    filtered.sort(key=lambda b: b.get('created_at', ''), reverse=True)
    return jsonify(filtered)

@app.route('/admin/api/bookings/<booking_ref>/status', methods=['POST'])
@admin_required
def admin_api_booking_status(booking_ref):
    data = request.get_json() or {}
    new_status = (data.get('status') or '').lower()
    if new_status not in ['confirmed', 'pending', 'cancelled', 'completed']:
        return jsonify({'success': False, 'error': 'Invalid status'}), 400

    booking = get_booking_by_ref(booking_ref)
    if not booking:
        return jsonify({'success': False, 'error': 'Booking not found'}), 404

    try:
        if DB_CONNECTED:
            r = requests.patch(
                f"{SUPABASE_URL}/rest/v1/bookings?booking_ref=eq.{booking_ref}",
                headers=SUPABASE_HEADERS,
                json={'status': new_status},
                timeout=10
            )
            if r.status_code not in (200, 204):
                raise Exception(f"Status update failed ({r.status_code}): {r.text[:300]}")
        else:
            bookings = load_json('bookings.json')
            for b in bookings:
                if b.get('booking_ref') == booking_ref:
                    b['status'] = new_status
            save_json('bookings.json', bookings)

        # Cancelling releases the seats back into inventory
        if new_status == 'cancelled':
            bus_id = booking.get('bus_id')
            schedule_id = booking.get('schedule_id')
            booking_date = booking.get('booking_date')
            seats_to_release = [str(s) for s in booking.get('selected_seats', [])]

            if DB_CONNECTED and schedule_id:
                resp = requests.get(
                    f"{SUPABASE_URL}/rest/v1/bus_seats?schedule_id=eq.{schedule_id}&booking_date=eq.{booking_date}",
                    headers=SUPABASE_HEADERS, timeout=10
                )
                if resp.status_code == 200 and resp.json():
                    seat_row = resp.json()[0]
                    current = seat_row.get('booked_seats_list', [])
                    updated = [s for s in current if s not in seats_to_release]
                    requests.patch(
                        f"{SUPABASE_URL}/rest/v1/bus_seats?schedule_id=eq.{schedule_id}&booking_date=eq.{booking_date}",
                        headers=SUPABASE_HEADERS,
                        json={'booked_seats_list': updated, 'booked_seats': len(updated), 'updated_at': datetime.utcnow().isoformat()},
                        timeout=10
                    )
            elif not DB_CONNECTED:
                seat_data = load_bus_seats(bus_id, booking_date)
                current = seat_data.get('booked_seats_list', [])
                updated = [s for s in current if s not in seats_to_release]
                update_bus_seats(bus_id, booking_date, updated)

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/admin/api/bookings/<booking_ref>', methods=['DELETE'])
@admin_required
def admin_api_delete_booking(booking_ref):
    try:
        if DB_CONNECTED:
            r = requests.delete(f"{SUPABASE_URL}/rest/v1/bookings?booking_ref=eq.{booking_ref}", headers=SUPABASE_HEADERS, timeout=10)
            if r.status_code not in (200, 204):
                raise Exception(f"Delete failed ({r.status_code}): {r.text[:300]}")
        else:
            bookings = load_json('bookings.json')
            bookings = [b for b in bookings if b.get('booking_ref') != booking_ref]
            save_json('bookings.json', bookings)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

# ---------- Revenue / bookings trend for dashboard chart ----------
@app.route('/admin/api/stats')
@admin_required
def admin_api_stats():
    days = int(request.args.get('days', 14))
    bookings = load_bookings()
    today = datetime.now().date()

    def safe_float(v):
        try:
            return float(v)
        except (TypeError, ValueError):
            return 0.0

    buckets = {}
    for i in range(days):
        d = (today - timedelta(days=days - 1 - i)).strftime('%Y-%m-%d')
        buckets[d] = {'date': d, 'bookings': 0, 'revenue': 0.0}

    for b in bookings:
        created = (b.get('created_at') or '')[:10]
        if created in buckets and (b.get('status') or '').lower() != 'cancelled':
            buckets[created]['bookings'] += 1
            buckets[created]['revenue'] += safe_float(b.get('total_fare', 0))

    return jsonify(list(buckets.values()))

# ---------- Generic CRUD for buses / routes / vehicles / schedules ----------
@app.route('/admin/api/buses', methods=['GET', 'POST'])
@admin_required
def admin_api_buses():
    if request.method == 'GET':
        return jsonify(sb_select('buses'))
    try:
        result = sb_insert('buses', request.get_json() or {})
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/admin/api/buses/<int:item_id>', methods=['PUT', 'DELETE'])
@admin_required
def admin_api_bus_detail(item_id):
    try:
        if request.method == 'DELETE':
            sb_delete('buses', item_id)
        else:
            sb_update('buses', item_id, request.get_json() or {})
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/admin/api/routes', methods=['GET', 'POST'])
@admin_required
def admin_api_routes():
    if request.method == 'GET':
        return jsonify(sb_select('routes'))
    try:
        result = sb_insert('routes', request.get_json() or {})
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/admin/api/routes/<int:item_id>', methods=['PUT', 'DELETE'])
@admin_required
def admin_api_route_detail(item_id):
    try:
        if request.method == 'DELETE':
            sb_delete('routes', item_id)
        else:
            sb_update('routes', item_id, request.get_json() or {})
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/admin/api/vehicles', methods=['GET', 'POST'])
@admin_required
def admin_api_vehicles():
    if request.method == 'GET':
        return jsonify(sb_select('vehicles'))
    try:
        result = sb_insert('vehicles', request.get_json() or {})
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/admin/api/vehicles/<int:item_id>', methods=['PUT', 'DELETE'])
@admin_required
def admin_api_vehicle_detail(item_id):
    try:
        if request.method == 'DELETE':
            sb_delete('vehicles', item_id)
        else:
            sb_update('vehicles', item_id, request.get_json() or {})
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/admin/api/schedules', methods=['GET', 'POST'])
@admin_required
def admin_api_schedules():
    if request.method == 'GET':
        return jsonify(sb_select('schedules'))
    try:
        result = sb_insert('schedules', request.get_json() or {})
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/admin/api/schedules/<int:item_id>', methods=['PUT', 'DELETE'])
@admin_required
def admin_api_schedule_detail(item_id):
    try:
        if request.method == 'DELETE':
            sb_delete('schedules', item_id)
        else:
            sb_update('schedules', item_id, request.get_json() or {})
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

# ---------- CSV export ----------
@app.route('/admin/export/bookings.csv')
def admin_export_bookings():
    if not session.get('admin_logged_in'):
        flash('Please login to access admin panel', 'error')
        return redirect(url_for('admin_login'))

    import io, csv
    from flask import Response

    bookings = load_bookings()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Booking Ref', 'Passenger', 'Phone', 'Email', 'Seats', 'Fare', 'Status', 'Payment', 'Date', 'Created At'])
    for b in bookings:
        writer.writerow([
            b.get('booking_ref', ''),
            b.get('passenger_name', ''),
            b.get('passenger_phone', ''),
            b.get('passenger_email', ''),
            ', '.join(str(s) for s in b.get('selected_seats', [])),
            b.get('total_fare', ''),
            b.get('status', ''),
            b.get('payment_method', ''),
            b.get('booking_date', ''),
            b.get('created_at', '')
        ])
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=bookings.csv'}
    )

@app.route('/admin')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        flash('Please login to access admin panel', 'error')
        return redirect(url_for('admin_login'))

    bookings = load_bookings()
    vehicles = load_vehicles()
    routes = load_routes()
    buses = load_buses()

    def safe_float(val):
        try:
            return float(val)
        except (TypeError, ValueError):
            return 0.0

    stats = {
        'total_bookings': len(bookings),
        'total_revenue': sum(safe_float(b.get('total_fare', 0)) for b in bookings if b.get('status') == 'confirmed'),
        'total_vehicles': len(vehicles),
        'total_routes': len(routes),
        'total_buses': len(buses),
        'today_bookings': len([b for b in bookings if (b.get('created_at') or '').startswith(datetime.now().strftime('%Y-%m-%d'))]),
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
