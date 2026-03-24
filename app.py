from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import math
from datetime import datetime
import random

app = Flask(__name__)
CORS(app)

def geocode_location(location):
    """Convert location name to coordinates using Nominatim API, with a small fallback map"""
    location = location.strip()
    if not location:
        return None

    # Known fallback coordinates to ensure basic operation when API denies.
    fallback_coords = {
        'new york': (40.7128, -74.0060),
        'boston': (42.3601, -71.0589),
        'san francisco': (37.7749, -122.4194),
        'los angeles': (34.0522, -118.2437),
        'chicago': (41.8781, -87.6298)
    }

    try:
        headers = {
            'User-Agent': 'DelayGuard-AI/1.0 (contact@example.com)',
            'Accept': 'application/json'
        }
        params = {
            'format': 'json',
            'q': location,
            'limit': 1,
            'addressdetails': 0
        }
        response = requests.get(
            'https://nominatim.openstreetmap.org/search',
            headers=headers,
            params=params,
            timeout=10
        )

        if response.status_code != 200:
            print(f"geocode_location: bad status {response.status_code} for {location}")
        else:
            data = response.json()
            if data:
                return float(data[0]['lat']), float(data[0]['lon'])

    except Exception as e:
        print(f"geocode_location: exception {e} for {location}")

    found = fallback_coords.get(location.lower())
    if found:
        print(f"geocode_location: using fallback coords for {location}")
        return found

    return None

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two coordinates in kilometers"""
    R = 6371  # Earth's radius in km

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = math.sin(dlat/2) * math.sin(dlat/2) + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2) * math.sin(dlon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    return R * c

def generate_navigation_steps(distance_km, delay_percentage):
    """Generate realistic turn-by-turn navigation steps"""
    steps = []
    steps.append("📍 Starting route - Follow the directions ahead")

    # Generate realistic meter-based instructions
    segment1_meters = int(distance_km * 0.25 * 1000)
    segment2_meters = int(distance_km * 0.35 * 1000)
    segment3_meters = int(distance_km * 0.25 * 1000)
    segment4_meters = int(distance_km * 0.15 * 1000)

    # Simulate steps based on distance
    if distance_km > 10:
        steps.append(f"🛣️ Go straight for {segment1_meters} meters")
        steps.append("↩️ Turn left onto main road")
        steps.append(f"🛣️ Continue for {segment2_meters} meters")
        if delay_percentage > 30:
            steps.append("⚠️ Traffic ahead - Reduce speed and stay alert")
        steps.append(f"🛣️ Continue for {segment3_meters} meters")
        steps.append("↪️ Turn right onto your destination road")
        steps.append(f"🛣️ Continue for {segment4_meters} meters")
    elif distance_km > 5:
        steps.append(f"🛣️ Go straight for {segment1_meters + segment2_meters} meters")
        steps.append("↩️ Turn left")
        steps.append(f"🛣️ Continue for {segment3_meters + segment4_meters} meters")
    else:
        total_meters = int(distance_km * 1000)
        steps.append(f"🛣️ Go straight for {total_meters} meters")

    # Add conditional warnings
    if delay_percentage >= 60:
        steps.append("🔄 Route recalculation in progress - standby")
    elif delay_percentage > 30:
        steps.append("📊 Heavy traffic detected on main route")
    
    steps.append("🏁 Arriving at destination - Prepare to stop")

    return steps

def get_route_status(delay_percentage):
    """Determine route status based on delay"""
    if delay_percentage >= 60:
        return "rerouting"
    else:
        return "normal"

def get_weather_factor():
    """Simulate weather conditions (in real app, use weather API)"""
    weather_conditions = ['clear', 'rain', 'snow', 'cloudy']
    weather = random.choice(weather_conditions)

    if weather == 'rain':
        return 20  # Rain increases delay by 20%
    elif weather == 'snow':
        return 15  # Snow increases delay by 15%
    elif weather == 'cloudy':
        return 5   # Cloudy weather slight increase
    else:
        return 0   # Clear weather no impact

@app.route('/predict', methods=['POST'])
def predict():
    data = request.get_json()
    start_location = data.get('start', '')
    end_location = data.get('end', '')

    # Step 1: Geocode locations to get coordinates
    start_coords = geocode_location(start_location)
    end_coords = geocode_location(end_location)

    if not start_coords or not end_coords:
        return jsonify({
            "delay": 45,
            "suggestion": "🗺️ Analyzing alternate routes - Please try major cities (NYC, Boston, LA, Chicago, SF)",
            "steps": ["📍 Starting analysis", "🔍 Searching for optimal route", "🏁 Route ready"],
            "status": "normal",
            "factors": {"traffic": 15, "distance": 20, "weather": 10}
        })

    # Step 2: Calculate distance factor
    distance_km = haversine_distance(start_coords[0], start_coords[1], end_coords[0], end_coords[1])
    distance_factor = min(50, distance_km * 1.5)  # Longer distance = higher delay risk, max 50%

    # Step 3: Calculate traffic factor based on time of day
    current_hour = datetime.now().hour
    if 8 <= current_hour <= 10 or 17 <= current_hour <= 20:  # Peak hours: 8-10 AM, 5-8 PM
        traffic_factor = 30  # High traffic during peak hours
    else:
        traffic_factor = 5   # Low traffic during off-peak hours

    # Step 4: Get weather factor
    weather_factor = get_weather_factor()

    # Step 5: Calculate total delay score
    delay_score = traffic_factor + distance_factor + weather_factor
    delay_percentage = min(95, max(5, delay_score))  # Keep between 5-95%

    # Step 6: Generate suggestion based on delay score
    if delay_percentage >= 60:
        suggestion = "🚨 Critical delay detected! AI recommends rerouting for faster arrival"
    elif delay_percentage >= 40:
        suggestion = "⚠️ Moderate delay expected - Consider alternative route or wait time"
    else:
        suggestion = "✅ Clear path ahead - Optimal route selected for your journey"

    # Step 7: Generate navigation steps
    steps = generate_navigation_steps(distance_km, delay_percentage)

    # Step 8: Determine route status
    status = get_route_status(delay_percentage)

    return jsonify({
        "delay": round(delay_percentage),
        "suggestion": suggestion,
        "steps": steps,
        "status": status,
        "factors": {
            "traffic": round(traffic_factor),
            "distance": round(distance_factor, 1),
            "weather": weather_factor
        }
    })

if __name__ == '__main__':
    app.run(debug=True)