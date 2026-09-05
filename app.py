import streamlit as st
import requests
import os
import re
import folium
from streamlit_folium import st_folium
from datetime import date, timedelta
from temperature_api import get_temperature_data, get_heatmap_tiles
from alert_logic import get_risk
from email_alert import send_alert_email
from route_planner import ask_ai_route
from waypoints import US_CITIES
from streamlit_geolocation import streamlit_geolocation
from streamlit_autorefresh import st_autorefresh

# ---------- Open-Meteo helpers ----------
OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"

def get_openmeteo_current(lat, lon):
    """Get current weather from Open-Meteo. No API key is required."""
    response = requests.get(
        OPEN_METEO_FORECAST_URL,
        params={
            "latitude": float(lat),
            "longitude": float(lon),
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code",
            "timezone": "auto",
        },
        timeout=10,
    )
    response.raise_for_status()
    payload = response.json()
    current = payload.get("current", {})

    if current.get("temperature_2m") is None:
        raise RuntimeError("Open-Meteo returned no current temperature.")

    return {
        "temp": current.get("temperature_2m"),
        "humidity": current.get("relative_humidity_2m"),
        "apparent_temp": current.get("apparent_temperature"),
        "weather_code": current.get("weather_code"),
        "city": "",
        "country": "",
        "source": "Open-Meteo",
    }

def get_openmeteo_forecast(lat, lon, target_date=None):
    """Get the selected day's max temperature from Open-Meteo forecast."""
    target = target_date or date.today()
    response = requests.get(
        OPEN_METEO_FORECAST_URL,
        params={
            "latitude": float(lat),
            "longitude": float(lon),
            "daily": "temperature_2m_max,temperature_2m_min,apparent_temperature_max",
            "forecast_days": 16,
            "timezone": "auto",
        },
        timeout=10,
    )
    response.raise_for_status()
    payload = response.json()
    daily = payload.get("daily", {})
    dates = daily.get("time", [])

    target_str = str(target)
    if target_str not in dates:
        raise RuntimeError(
            f"Open-Meteo forecast does not contain {target_str}. "
            "Choose today or a near-term date."
        )

    idx = dates.index(target_str)
    temps = daily.get("temperature_2m_max", [])
    mins = daily.get("temperature_2m_min", [])
    feels = daily.get("apparent_temperature_max", [])

    return {
        "temp": temps[idx] if idx < len(temps) else None,
        "min_temp": mins[idx] if idx < len(mins) else None,
        "apparent_temp": feels[idx] if idx < len(feels) else None,
        "humidity": None,
        "date": target_str,
        "source": "Open-Meteo",
    }

def geocode_openmeteo(location_query):
    """Convert a typed city/place into coordinates using Open-Meteo Geocoding."""
    query = location_query.strip()
    if not query:
        return None

    response = requests.get(
        OPEN_METEO_GEOCODING_URL,
        params={
            "name": query,
            "count": 1,
            "language": "en",
            "format": "json",
        },
        timeout=10,
    )
    response.raise_for_status()
    results = response.json().get("results", [])

    if not results:
        return None

    item = results[0]
    display = item.get("name", query)
    if item.get("admin1"):
        display += f", {item['admin1']}"
    if item.get("country"):
        display += f", {item['country']}"

    return {
        "lat": item["latitude"],
        "lon": item["longitude"],
        "name": display,
    }

def get_openmeteo_city(city_name, target_date=None):
    location = geocode_openmeteo(city_name)
    if not location:
        return None

    target = target_date or date.today()
    weather = (
        get_openmeteo_current(location["lat"], location["lon"])
        if target == date.today()
        else get_openmeteo_forecast(location["lat"], location["lon"], target)
    )

    return {
        **weather,
        "city": location["name"],
        "lat": location["lat"],
        "lon": location["lon"],
    }

def extract_openmeteo_cities(question):
    """Extract simple route city names such as 'from Lahore to Islamabad'."""
    q = " ".join(question.strip().split())
    candidates = []

    m = re.search(r"\bfrom\s+(.+?)\s+to\s+(.+?)(?:,|\.|$)", q, re.I)
    if m:
        candidates.extend([m.group(1).strip(), m.group(2).strip()])

    if not candidates:
        m = re.search(
            r"\b([A-Za-z][A-Za-z .'-]{1,40}?)\s+to\s+([A-Za-z][A-Za-z .'-]{1,40})(?:,|\.|$)",
            q, re.I
        )
        if m:
            candidates.extend([m.group(1).strip(), m.group(2).strip()])

    if not candidates:
        m = re.search(r"\b(?:in|at|near)\s+([A-Za-z][A-Za-z .'-]{1,40})(?:\?|,|\.|$)", q, re.I)
        if m:
            candidates.append(m.group(1).strip())

    cleaned=[]
    for item in candidates:
        item = re.sub(
            r"\b(suggest|recommend|route|with|low|lower|temperature|weather|today|tomorrow)\b",
            " ", item, flags=re.I
        )
        item = re.sub(r"\s+", " ", item).strip(" ,.")
        if item:
            cleaned.append(item)

    result=[]
    seen=set()
    for item in cleaned:
        key=item.lower()
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result[:8]

def ask_ai_with_openmeteo(question, mentioned_cities, travel_date):
    requested = date.fromisoformat(travel_date)
    today = date.today()
    q = question.lower()

    if "tomorrow" in q:
        target = today + timedelta(days=1)
    elif requested < today:
        target = today
    else:
        target = requested

    if target > today + timedelta(days=15):
        target = today

    cities = mentioned_cities[:8] if mentioned_cities else extract_openmeteo_cities(question)
    if not cities:
        return (
            "Please mention city names, for example: "
            "'From Gujranwala to Lahore, suggest a cooler route.'",
            None,
        )

    route=[]
    errors=[]
    for city in cities:
        try:
            item=get_openmeteo_city(city, target)
            if item and item.get("temp") is not None:
                route.append({
                    "city": item["city"].split(",")[0],
                    "temp": float(item["temp"]),
                    "lat": item["lat"],
                    "lon": item["lon"],
                })
        except Exception as exc:
            errors.append(f"{city}: {exc}")

    if not route:
        detail = errors[0] if errors else "No weather result was returned."
        return f"Open-Meteo could not return weather: {detail}", None

    route_sorted=sorted(route, key=lambda x: x["temp"])
    coolest=route_sorted[0]
    kind="forecast" if target != today else "current"

    answer=(
        f"Using Open-Meteo {kind} data, the coolest checked stop is "
        f"{coolest['city']} at {coolest['temp']:.1f}°C. "
        f"For a heat-safe route, prefer the lower-temperature stops."
    )
    return answer, {"route": route, "coolest_stop": coolest}

st.set_page_config(page_title="Heat Guardian", page_icon="🌡️", layout="wide")
# ---------- Sign-in gate ----------
# ---------- Sign-in gate ----------
if "user_email" not in st.session_state:
    st.session_state.user_email = None

if st.session_state.user_email is None:
    st.markdown("""
    <style>
    /* Hide default streamlit chrome on the sign-in screen */
    #MainMenu, footer, header { visibility: hidden; }

    .stApp {
        background:
            radial-gradient(circle at 15% 20%, rgba(255,92,92,0.18), transparent 42%),
            radial-gradient(circle at 85% 15%, rgba(255,140,66,0.14), transparent 40%),
            radial-gradient(circle at 50% 90%, rgba(74,222,128,0.08), transparent 45%),
            linear-gradient(160deg, #050b16 0%, #0a1628 45%, #0d1c33 100%);
        background-attachment: fixed;
    }

    @keyframes floatUp {
        0%   { transform: translateY(0px); }
        50%  { transform: translateY(-8px); }
        100% { transform: translateY(0px); }
    }
    @keyframes fadeSlideIn {
        0%   { opacity: 0; transform: translateY(18px); }
        100% { opacity: 1; transform: translateY(0); }
    }
    @keyframes glowPulse {
        0%, 100% { box-shadow: 0 8px 30px rgba(255,92,92,0.35), 0 0 0 0 rgba(255,140,66,0.0); }
        50%      { box-shadow: 0 8px 40px rgba(255,92,92,0.5), 0 0 0 8px rgba(255,140,66,0.06); }
    }

    .signin-wrap {
        display:flex;
        flex-direction:column;
        align-items:center;
        justify-content:center;
        padding-top: 54px;
        animation: fadeSlideIn 0.7s ease-out;
    }
    .signin-logo {
        background:linear-gradient(135deg,#ff5c5c,#ff8c42);
        width:76px; height:76px;
        border-radius:22px;
        display:flex; align-items:center; justify-content:center;
        font-size:38px;
        margin-bottom:20px;
        animation: floatUp 3.5s ease-in-out infinite, glowPulse 3.5s ease-in-out infinite;
    }
    .signin-title {
        font-size:38px;
        font-weight:800;
        background: linear-gradient(90deg, #ffffff, #b9c9e4);
        -webkit-background-clip: text;
        background-clip: text;
        color: transparent;
        margin:0;
        letter-spacing:-0.8px;
    }
    .signin-sub {
        color:#8fa3bf;
        font-size:15.5px;
        margin-top:8px;
        margin-bottom:8px;
        text-align:center;
        max-width: 420px;
        line-height: 1.5;
    }
    .signin-badge {
        display:inline-flex;
        align-items:center;
        gap:6px;
        background: rgba(74,222,128,0.1);
        border: 1px solid rgba(74,222,128,0.25);
        color:#4ade80;
        font-size:12px;
        font-weight:600;
        padding:5px 14px;
        border-radius:20px;
        margin-bottom: 30px;
        letter-spacing: 0.3px;
    }

    .feature-row {
        display:flex;
        gap:14px;
        justify-content:center;
        flex-wrap:wrap;
        max-width: 480px;
        margin: 0 auto 30px auto;
    }
    .feature-chip {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px;
        padding: 10px 14px;
        text-align:center;
        min-width: 118px;
        backdrop-filter: blur(6px);
    }
    .feature-chip .fi { font-size: 18px; margin-bottom: 4px; }
    .feature-chip .ft { font-size: 11.5px; color:#8fa3bf; font-weight:600; letter-spacing:0.2px; }

    .signin-footer {
        text-align:center;
        color:#4c5c78;
        font-size:12px;
        margin-top: 26px;
        letter-spacing: 0.2px;
    }

    /* Glassmorphism card override for the sign-in form container */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: linear-gradient(160deg, rgba(18,34,61,0.85), rgba(10,22,40,0.9)) !important;
        border: 1px solid rgba(255,255,255,0.12) !important;
        border-radius: 20px !important;
        box-shadow: 0 20px 60px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.05) !important;
        padding: 6px !important;
        animation: fadeSlideIn 0.9s ease-out;
    }

    div[data-testid="stTextInput"] input {
        border-radius: 10px !important;
        border: 1px solid rgba(255,255,255,0.12) !important;
        padding: 12px 14px !important;
        font-size: 14.5px !important;
    }
    div[data-testid="stTextInput"] input:focus {
        border-color: #ff8c42 !important;
        box-shadow: 0 0 0 3px rgba(255,140,66,0.15) !important;
    }

    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg,#ff5c5c,#ff8c42) !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 700 !important;
        letter-spacing: 0.2px;
        padding: 12px 0 !important;
        box-shadow: 0 6px 18px rgba(255,92,92,0.35) !important;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    div.stButton > button[kind="primary"]:hover {
        transform: translateY(-1px);
        box-shadow: 0 10px 24px rgba(255,92,92,0.45) !important;
    }
    </style>

    <div class="signin-wrap">
        <div class="signin-logo">🌡️</div>
        <p class="signin-title">Heat Guardian</p>
        <p class="signin-sub">Real-time hyperlocal heat risk monitoring with instant Gmail alerts — stay safe wherever you go.</p>
        <div class="signin-badge">● Live temperature data</div>
    </div>

    <div class="feature-row">
        <div class="feature-chip"><div class="fi">📍</div><div class="ft">Hyperlocal Data</div></div>
        <div class="feature-chip"><div class="fi">📧</div><div class="ft">Instant Alerts</div></div>
        <div class="feature-chip"><div class="fi">🗺️</div><div class="ft">Route Planning</div></div>
        <div class="feature-chip"><div class="fi">🚶</div><div class="ft">Safe Walk Mode</div></div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.15, 1])
    with col2:
        with st.container(border=True):
            st.markdown(
                "<div style='padding:22px 20px 6px 20px;'>"
                "<div style='font-size:13px; font-weight:700; color:#cfe0f5; margin-bottom:14px; "
                "letter-spacing:0.3px;'>🔐 SIGN IN TO CONTINUE</div></div>",
                unsafe_allow_html=True,
            )
            email_input = st.text_input(
                "Gmail address",
                placeholder="you@gmail.com",
                label_visibility="collapsed",
            )
            st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
            if st.button("Sign in with Gmail →", type="primary", use_container_width=True):
                if email_input and "@gmail.com" in email_input:
                    st.session_state.user_email = email_input
                    st.rerun()
                else:
                    st.warning("Please enter a valid Gmail address.")
            st.markdown(
                "<div style='padding:10px 20px 18px 20px; text-align:center; font-size:11.5px; "
                "color:#5a6b85;'>We'll only use this to send you heat safety alerts.</div>",
                unsafe_allow_html=True,
            )

    st.markdown(
        "<div class='signin-footer'>Heat Guardian • Powered by FortyGuard</div>",
        unsafe_allow_html=True,
    )

    st.stop()
# ---------- CSS ----------
st.markdown("""
<style>
@keyframes bgSwitch {
    0%, 49%   { background-image: url('app/static/image1.png'); }
    50%, 100% { background-image: url('app/static/image2.png'); }
}
.stApp {
    animation: bgSwitch 2s steps(1) infinite;
    background-size: cover;
    background-position: center;
}
.stApp::before {
    content: "";
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(10,22,40,0.75);
    z-index: -1;
}
</style>
""", unsafe_allow_html=True)
st.markdown("""
<style>
.stApp { background-color: #0a1628; }
.stApp, .stApp p, .stApp label, .stApp span { color: #ffffff; }

.stTextInput input, .stSelectbox div[data-baseweb="select"], .stDateInput input {
    background-color: #12223d !important;
    color: #ffffff !important;
}
.top-header h1 {
    margin: 0;
    font-size: 32px;
    font-weight: 800;
    letter-spacing: -0.5px;
    color: #ffffff;
}
.top-header p {
    margin: 4px 0 0 0;
    color: #7a92b5;
    font-size: 14px;
    letter-spacing: 0.3px;
}

.live-badge {
    background-color: #163a2b;
    color: #4ade80;
    padding: 4px 12px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: 600;
}

.temp-card {
    background: linear-gradient(135deg, #7a1f1f, #a83232);
    border-radius: 16px;
    padding: 24px;
    height: 100%;
    backdrop-filter: blur(10px);
-webkit-backdrop-filter: blur(10px);
}
.temp-card .loc { font-size: 15px; color: #ffd9d9; margin-bottom: 6px; }
.temp-card .val { font-size: 52px; font-weight: 800; margin: 0; }
.temp-card .lbl { font-size: 13px; color: #ffd9d9; margin-top: 8px; }

.risk-card {
    background-color: #2a1414;
    border-radius: 16px;
    padding: 24px;
    height: 100%;
    backdrop-filter: blur(10px);
-webkit-backdrop-filter: blur(10px);
}
.risk-card.high { background-color: #2a2214; }
.risk-card.normal { background-color: #14261a; }
.risk-card .title { font-size: 14px; color: #cccccc; margin-bottom: 10px; }
.risk-card .level { font-size: 26px; font-weight: 800; margin: 6px 0; }
.risk-card .level.extreme { color: #ff5c5c; }
.risk-card .level.high { color: #ffb347; }
.risk-card .level.normal { color: #4ade80; }
.risk-card .desc { font-size: 13px; color: #cccccc; }

.stat-card {
    background-color: #12223d;
    border-radius: 14px;
    padding: 18px;
    text-align: left;
    backdrop-filter: blur(10px);
-webkit-backdrop-filter: blur(10px);
}
.stat-card .icon { font-size: 22px; margin-bottom: 6px; }
.stat-card .lbl { font-size: 13px; color: #8fa3bf; }
.stat-card .val { font-size: 22px; font-weight: 700; }

.map-box {
    background-color: #12223d;
    border-radius: 16px;
    padding: 14px;
    backdrop-filter: blur(10px);
-webkit-backdrop-filter: blur(10px);
}
.map-box h4 { margin: 0 0 10px 4px; font-size: 14px; color: #ffffff; }

.email-banner {
    background-color: #14261a;
    border-radius: 12px;
    padding: 14px 20px;
    color: #4ade80;
    margin-top: 12px;
}

.ai-panel {
    background-color: #12223d;
    border-radius: 16px;
    padding: 20px;
}
.route-card {
    background-color: #1d3a63;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px;
    padding: 16px;
    text-align: center;
}
.route-card.coolest { border: 2px solid #4ade80; }
.route-card h5 { margin: 0; font-size: 14px; color: #dbe6f5; }
.route-card p { margin: 6px 0 0 0; font-size: 20px; font-weight: 700; color: #ffffff; }

footer, #MainMenu { visibility: hidden; }
div[data-testid="stVerticalBlockBorderWrapper"],
div[data-testid="stVerticalBlockBorderWrapper"] > div,
[class*="stVerticalBlockBorderWrapper"] {
    background-color: rgba(23, 45, 79, 0.92) !important;
    backdrop-filter: blur(12px) !important;
    -webkit-backdrop-filter: blur(12px) !important;
    border-radius: 16px !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
}
</style>

""", unsafe_allow_html=True)

LOCATIONS = {
    "Phoenix, AZ": (33.4484, -112.0740),
    "Tucson, AZ": (32.2226, -110.9747),
    "Los Angeles, CA": (34.0522, -118.2437),
    "San Jose, CA": (37.3382, -121.8863),
    "San Francisco, CA": (37.7749, -122.4194),
    "Sacramento, CA": (38.5816, -121.4944),
    "Las Vegas, NV": (36.1699, -115.1398),
    "Denver, CO": (39.7392, -104.9903),
    "Albuquerque, NM": (35.0844, -106.6504),
    "Dallas, TX": (32.7767, -96.7970),
    "Houston, TX": (29.7604, -95.3698),
    "Oklahoma City, OK": (35.4676, -97.5164),
    "St. Louis, MO": (38.6270, -90.1994),
    "Chicago, IL": (41.8781, -87.6298),
    "Indianapolis, IN": (39.7684, -86.1581),
    "Columbus, OH": (39.9612, -82.9988),
    "Pittsburgh, PA": (40.4406, -79.9959),
    "Philadelphia, PA": (39.9526, -75.1652),
    "New York, NY": (40.7128, -74.0060),
    "Boston, MA": (42.3601, -71.0589),
    "Miami, FL": (25.7617, -80.1918),
    "Atlanta, GA": (33.7490, -84.3880),
    "Seattle, WA": (47.6062, -122.3321),
    "Portland, OR": (45.5152, -122.6784),
}
DEFAULT_DATE = date.today() - timedelta(days=10)

# ---------- Header ----------
h1, h2 = st.columns([3, 1])
with h1:
   st.markdown("""
<div class="top-header" style="display:flex; align-items:center; gap:14px; margin-bottom:28px;">
    <div style="background:linear-gradient(135deg,#ff5c5c,#ff8c42); width:52px; height:52px; border-radius:14px; display:flex; align-items:center; justify-content:center; font-size:26px; box-shadow:0 4px 12px rgba(255,92,92,0.3);">🌡️</div>
    <div>
        <h1>Heat Guardian</h1>
        <p>Real-time hyperlocal heat risk monitoring</p>
    </div>
</div>
""", unsafe_allow_html=True)
with h2:
    st.markdown('<div style="text-align:right; padding-top:15px;"><span class="live-badge">● LIVE DATA</span></div>', unsafe_allow_html=True)

# ---------- Controls ----------
weather_source = st.radio(
    "🌐 Weather Data Source",
    ["FortyGuard Data", "Open-Meteo"],
    horizontal=True,
    key="main_weather_source",
)

location_mode = st.radio(
    "📍 Location Input Method",
    ["Select from List", "Manual (City + Lat/Lon)", "📡 Live Location"],
    horizontal=True,
)

manual_lat = None
manual_lon = None
live_location_data = None

if location_mode == "Select from List":
    c1, c2, c3, c4 = st.columns([2, 1.5, 2, 1.5])
    with c1:
        location_name = st.selectbox("📍 Search Location", list(LOCATIONS.keys()))
    with c2:
        check_date = st.date_input("📅 Date", value=DEFAULT_DATE)
    with c3:
        hour = st.slider("🕐 Hour", 0, 23, 14)
    with c4:
        st.write("")
        check = st.button("🌡️ Check Temperature", type="primary", use_container_width=True)

elif location_mode == "Manual (City + Lat/Lon)":
    c1, c2, c3, c4, c5 = st.columns([2, 1, 1, 1.3, 1.3])
    with c1:
        location_name = st.text_input("📍 City Name", placeholder="e.g. Gujranwala, Pakistan")
    with c2:
        manual_lat = st.number_input("🌐 Latitude", value=32.1617, format="%.4f")
    with c3:
        manual_lon = st.number_input("🌐 Longitude", value=74.1883, format="%.4f")
    with c4:
        check_date = st.date_input("📅 Date", value=DEFAULT_DATE)
    with c5:
        hour = st.slider("🕐 Hour", 0, 23, 14)
    check = st.button("🌡️ Check Temperature", type="primary", use_container_width=True)

else:
    location_name = "Live Location"
    check_date = date.today()
    hour = 14
    st.info(
        "📡 Allow browser location access. "
        "For live GPS, use Open-Meteo because FortyGuard does not provide arbitrary live-location weather."
    )
    if st.session_state.get("safe_walk_active", False):
        live_location_data = None
    else:
        live_location_data = streamlit_geolocation()
    check = st.button("📍 Get Live Temperature", type="primary", use_container_width=True)

time_formatted = f"{hour:02d}:00"

# ---------- Session state defaults (FAKE static data — no API call on load) ----------
if "temp_source" not in st.session_state:
    st.session_state.temp_source = "FortyGuard"

if "temp_result" not in st.session_state:
    st.session_state.temp_result = {"temp": 41.3, "humidity": None, "apparent_temp": None}
    st.session_state.temp_location = ("Phoenix, AZ", 33.4484, -112.0740)
    st.session_state.temp_query = {"date": str(DEFAULT_DATE), "time": "14:00"}

if "ai_plan" not in st.session_state:
    st.session_state.ai_plan = None

if "ai_answer" not in st.session_state:
    st.session_state.ai_answer = (
        "Here's a cool-friendly plan: start in Chicago (the coolest stop at 11.0°C), "
        "head east to Pittsburgh (18.7°C), and then finish in New York (18.0°C). "
        "This route skips the warmer Columbus leg, keeping the overall temperature on the lower side."
    )
    st.session_state.ai_plan = {
        "route": [
            {"city": "Phoenix", "temp": 41.3},
            {"city": "Denver", "temp": 24.6},
            {"city": "Chicago", "temp": 11.0},
            {"city": "Pittsburgh", "temp": 18.7},
            {"city": "New York", "temp": 18.0},
        ],
        "coolest_stop": {"city": "Chicago", "temp": 11.0},
    }
if "safe_walk_active" not in st.session_state:
    st.session_state.safe_walk_active = False
if "safe_walk_last_risk" not in st.session_state:
    st.session_state.safe_walk_last_risk = None
if "show_heat_map" not in st.session_state:
    st.session_state.show_heat_map = False
if "heat_map_data" not in st.session_state:
    st.session_state.heat_map_data = None

# ---------- On button click, real API call (FAST temp-only, no heat map) ----------
if check:
    try:
        if location_mode == "Select from List":
            lat, lon = LOCATIONS[location_name]
            loc_display = location_name

            if weather_source == "FortyGuard Data":
                with st.spinner("Fetching FortyGuard temperature data..."):
                    data = get_temperature_data(lat, lon, str(check_date), time_formatted)
            else:
                with st.spinner("Fetching Open-Meteo temperature data..."):
                    if check_date == date.today():
                        data = get_openmeteo_current(lat, lon)
                    else:
                        data = get_openmeteo_forecast(lat, lon, check_date)

        elif location_mode == "Manual (City + Lat/Lon)":
            if not location_name:
                st.error("Please enter a city name.")
                st.stop()

            lat, lon = manual_lat, manual_lon
            loc_display = location_name

            if weather_source == "FortyGuard Data":
                with st.spinner("Fetching FortyGuard temperature data..."):
                    data = get_temperature_data(lat, lon, str(check_date), time_formatted)
            else:
                with st.spinner("Fetching Open-Meteo temperature data..."):
                    if check_date == date.today():
                        data = get_openmeteo_current(lat, lon)
                    else:
                        data = get_openmeteo_forecast(lat, lon, check_date)

        else:
            if weather_source != "Open-Meteo":
                st.error(
                    "FortyGuard does not provide arbitrary live GPS temperature. "
                    "Select Open-Meteo for Live Location."
                )
                st.stop()

            if not live_location_data or live_location_data.get("latitude") is None:
                st.error("Live location is not available. Allow browser location permission and try again.")
                st.stop()

            lat = live_location_data["latitude"]
            lon = live_location_data["longitude"]

            with st.spinner("Fetching live temperature from Open-Meteo..."):
                data = get_openmeteo_current(lat, lon)

            loc_display = "Live Location"

        st.session_state.temp_result = data
        st.session_state.temp_location = (loc_display, lat, lon)
        st.session_state.temp_source = weather_source
        st.session_state.temp_query = {"date": str(check_date), "time": time_formatted}

        # New temp check invalidates any previously generated heat map,
        # since it was for a different location/date/time.
        st.session_state.show_heat_map = False
        st.session_state.heat_map_data = None

    except Exception as e:
        st.error(f"Error fetching {weather_source} data: {e}")

# ---------- Display temperature result ----------
if st.session_state.temp_result is not None:
    data = st.session_state.temp_result
    location_name_disp, lat, lon = st.session_state.temp_location
    temp = data["temp"]
    temp_source = st.session_state.get("temp_source", "FortyGuard")

    if temp is None:
        st.warning(
            f"⚠️ No temperature data available for **{location_name_disp}** "
            f"from **{temp_source}** at the selected date/time. "
            "Try a different date, time, location, or switch weather source."
        )
    else:
        risk, message = get_risk(temp)
        risk_class = risk if risk in ["extreme", "high", "normal"] else "normal"

        col_left, col_right = st.columns([1, 1.6])

        with col_left:
            sub1, sub2 = st.columns(2)
            with sub1:
                st.markdown(f"""
                <div class="temp-card">
                    <div class="loc">📍 {location_name_disp}</div>
                    <p class="val">{temp:.1f}°C</p>
                    <div class="lbl">🌡️ Temperature • {temp_source}</div>
                </div>
                """, unsafe_allow_html=True)
            with sub2:
                st.markdown(f"""
                <div class="risk-card {risk_class}">
                    <div class="title">🏠 Heat Risk Level</div>
                    <div class="level {risk_class}">⚠️ {risk.upper()}</div>
                    <div class="desc">{message}</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(f"""
            <div class="stat-card">
                <div class="icon">🌡️</div>
                <div class="lbl">Temperature</div>
                <div class="val">{temp:.1f}°C</div>
            </div>
            """, unsafe_allow_html=True)

        alert_key = f"{location_name_disp}_{temp:.1f}"

        if temp > 30:
            if st.session_state.get("last_alert_key") != alert_key:
                sent, info = send_alert_email(location_name_disp, temp, receiver=st.session_state.user_email)
                if sent:
                    st.session_state.last_alert_key = alert_key
                    st.markdown("""
                    <div class="email-banner">
                        📧 <b>Heat alert email sent successfully.</b><br>
                        <span style="color:#8fa3bf; font-size:13px;">Stay safe and take care!</span>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.warning(f"Email not sent: {info}")
            else:
                st.markdown("""
                <div class="email-banner">
                    📧 <b>Heat alert already sent for this check.</b><br>
                    <span style="color:#8fa3bf; font-size:13px;">Stay safe and take care!</span>
                </div>
                """, unsafe_allow_html=True)

        # ---------------- Heat Map — separate & on-demand only ----------------
        with col_right:
            st.markdown('<div class="map-box"><h4>🗺️ Heat Map</h4>', unsafe_allow_html=True)

            gen_map = st.button(
                "🗺️ Generate Heat Map",
                use_container_width=True,
                help="Only fetches the visual heat map when clicked — separate from the fast temperature check above.",
            )

            if gen_map:
                q = st.session_state.get("temp_query", {"date": str(check_date if 'check_date' in dir() else date.today()), "time": time_formatted})
                if temp_source == "FortyGuard Data":
                    with st.spinner("Generating FortyGuard heat map... this can take a while."):
                        hm = get_heatmap_tiles(lat, lon, q["date"], q["time"], delta=0.01, granularity=60)
                    st.session_state.heat_map_data = {
                        "lat": lat, "lon": lon,
                        "tiles": hm.get("tiles", []),
                        "risk": risk, "temp": temp,
                        "location": location_name_disp,
                    }
                    st.session_state.show_heat_map = True
                else:
                    # Open-Meteo is fast — just show a simple marker immediately.
                    st.session_state.heat_map_data = {
                        "lat": lat, "lon": lon,
                        "tiles": [],
                        "risk": risk, "temp": temp,
                        "location": location_name_disp,
                    }
                    st.session_state.show_heat_map = True

            if st.session_state.show_heat_map and st.session_state.heat_map_data:
                hmd = st.session_state.heat_map_data
                m_lat, m_lon = hmd["lat"], hmd["lon"]
                m_risk = hmd["risk"]
                m_temp = hmd["temp"]
                m_loc = hmd["location"]
                tiles = hmd.get("tiles", [])

                color_map = {"extreme": "red", "high": "orange", "normal": "green", "unknown": "gray"}
                m = folium.Map(location=[m_lat, m_lon], zoom_start=13, tiles="OpenStreetMap")

                if tiles:
                    tile_temps = [t["temp"] for t in tiles]
                    tmin, tmax = min(tile_temps), max(tile_temps)
                    span = (tmax - tmin) or 1.0

                    def tile_color(t):
                        ratio = (t - tmin) / span
                        if ratio < 0.34:
                            return "green"
                        elif ratio < 0.67:
                            return "orange"
                        else:
                            return "red"

                    for tile in tiles:
                        folium.CircleMarker(
                            [tile["lat"], tile["lon"]],
                            radius=8,
                            color=tile_color(tile["temp"]),
                            fill=True,
                            fill_color=tile_color(tile["temp"]),
                            fill_opacity=0.6,
                            popup=f"{tile['temp']:.1f}°C",
                        ).add_to(m)
                else:
                    folium.CircleMarker(
                        [m_lat, m_lon], radius=16, color=color_map.get(m_risk, "gray"), fill=True,
                        fill_color=color_map.get(m_risk, "gray"), fill_opacity=0.7,
                        popup=f"{m_loc}: {m_temp:.1f}°C",
                    ).add_to(m)

                st_folium(m, width=None, height=380)
            else:
                st.info("👆 Click 'Generate Heat Map' to fetch and render the visual heat map for this location.")

            st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)


# ---------- AI Chatbot ----------
col_a, col_b = st.columns([1, 1.3])

with col_a:
    with st.container(border=True):
        st.subheader("✨ Ask Heat Guardian AI")
        st.caption("Choose the weather source for your AI route recommendation.")

        ai_source = st.radio(
            "🌐 AI Weather Data Source",
            ["FortyGuard Data", "Open-Meteo Live"],
            horizontal=True,
            key="ai_weather_source",
        )

        user_question = st.text_input(
            "Your travel question",
            value="I need to go from Phoenix to New York, suggest a route with low temperature"
        )
        ai_date = st.date_input(
            "Date for route check",
            value=DEFAULT_DATE,
            key="ai_date_input"
        )
        st.caption(
            "Open-Meteo is best for live/today/tomorrow and near-term forecast checks."
            if ai_source == "Open-Meteo Live"
            else "FortyGuard uses the project's existing temperature data."
        )
        ask = st.button("✨ Ask Heat Guardian AI", type="primary", use_container_width=True)

if ask:
    if user_question:
        mentioned = [c for c in US_CITIES if c.lower() in user_question.lower()]
        with st.spinner(
            "Checking Open-Meteo live/forecast data..."
            if ai_source == "Open-Meteo Live"
            else "Checking FortyGuard temperatures..."
        ):
            try:
                if ai_source == "Open-Meteo Live":
                    answer, result = ask_ai_with_openmeteo(
                        user_question,
                        mentioned,
                        travel_date=str(ai_date)
                    )
                else:
                    from route_planner import ask_ai
                    answer, result = ask_ai(
                        user_question,
                        mentioned,
                        travel_date=str(ai_date)
                    )

                st.session_state.ai_answer = answer
                st.session_state.ai_result = result

                if result:
                    st.session_state.ai_plan = result
            except Exception as e:
                st.session_state.ai_answer = f"Error: {e}"
                st.session_state.ai_result = None
    else:
        st.warning("Please type a question first.")

with col_b:
    if st.session_state.ai_answer:
        with st.container(border=True):
            st.markdown("#### 🤖 AI Recommendation")
            st.write(st.session_state.ai_answer)

            if st.session_state.get("ai_plan"):
                st.markdown("##### 🗺️ Route Temperature Analysis")
                route = st.session_state.ai_plan["route"]
                coolest = st.session_state.ai_plan["coolest_stop"]
                cols = st.columns(len(route))
                for i, r in enumerate(route):
                    is_coolest = coolest and r["city"] == coolest["city"]
                    temp_display = f"{r['temp']:.1f}°C" if r["temp"] is not None else "N/A"
                    css_class = "route-card coolest" if is_coolest else "route-card"
                    badge = '<div style="color:#4ade80; font-size:11px; margin-top:4px;">Coolest Stop</div>' if is_coolest else ""
                    with cols[i]:
                        st.markdown(f"""
                        <div class="{css_class}">
                            <h5>{r['city']}</h5>
                            <p>{temp_display}</p>
                            {badge}
                        </div>
                        """, unsafe_allow_html=True)

                if coolest and coolest.get("temp") is not None:
                    st.markdown(f"""
                    <div class="email-banner" style="text-align:center;">
                        ❄️ Coolest stop: <b>{coolest['city']}</b> at {coolest['temp']:.1f}°C
                    </div>
                    """, unsafe_allow_html=True)

st.markdown("---")

with st.container(border=True):
    st.subheader("🚶 Safe Walk Mode")
    st.caption(
        "Monitor heat risk continuously using live GPS or a typed location with Open-Meteo."
    )

    safe_source = "Open-Meteo"

    safe_location_mode = st.radio(
        "📍 Safe Walk Location",
        ["📡 Live Location", "⌨️ Manual Location"],
        horizontal=True,
        key="safe_walk_location_mode",
    )

    safe_manual_city = ""
    safe_manual_lat = None
    safe_manual_lon = None

    if safe_location_mode == "⌨️ Manual Location":
        sc1, sc2, sc3 = st.columns([2, 1, 1])
        with sc1:
            safe_manual_city = st.text_input(
                "📍 Type City / Location",
                placeholder="e.g. Gujranwala, Pakistan",
                key="safe_manual_city",
            )
        with sc2:
            safe_manual_lat = st.number_input(
                "🌐 Latitude",
                value=32.1617,
                format="%.4f",
                key="safe_manual_lat",
            )
        with sc3:
            safe_manual_lon = st.number_input(
                "🌐 Longitude",
                value=74.1883,
                format="%.4f",
                key="safe_manual_lon",
            )

    interval_options = {
        "Every 10 seconds": 10,
        "Every 30 seconds": 30,
        "Every 60 seconds": 60,
        "Every 2 minutes": 120,
        "Every 5 minutes": 300,
        "Every 10 minutes": 600,
        "Every 15 minutes": 900,
        "Every 30 minutes": 1800,
        "Every 1 hour": 3600,
    }
    selected_interval_label = st.selectbox(
        "⏱️ Update location/weather every:",
        list(interval_options.keys()),
        key="safe_walk_interval",
    )
    selected_interval_seconds = interval_options[selected_interval_label]

    toggle = st.toggle(
        "Enable Safe Walk Mode",
        value=st.session_state.safe_walk_active,
        key="safe_walk_toggle",
    )
    st.session_state.safe_walk_active = toggle

    if st.session_state.safe_walk_active:
        st.info(
            f"📡 Live monitoring active — updating {selected_interval_label.lower()} "
            f"using {safe_source}."
        )
        st_autorefresh(
            interval=selected_interval_seconds * 1000,
            key="safe_walk_refresh"
        )

        try:
            if safe_location_mode == "📡 Live Location":
                location_data = streamlit_geolocation()

                if not location_data or location_data.get("latitude") is None:
                    st.info(
                        "Waiting for location permission — please allow location access "
                        "in your browser."
                    )
                    st.stop()

                safe_lat = float(location_data["latitude"])
                safe_lon = float(location_data["longitude"])
                safe_display = f"Live Location ({safe_lat:.4f}, {safe_lon:.4f})"

            else:
                if not safe_manual_city.strip():
                    st.warning("Type a city/location for Manual Location.")
                    st.stop()

                geo = geocode_openmeteo(safe_manual_city)
                if not geo:
                    st.error("Location not found. Try 'Gujranwala, Pakistan' or another clear city name.")
                    st.stop()
                safe_lat = float(geo["lat"])
                safe_lon = float(geo["lon"])
                safe_display = geo["name"]

            safe_data = get_openmeteo_current(safe_lat, safe_lon)

            safe_temp = safe_data.get("temp")
            if safe_temp is None:
                st.warning("No temperature data returned for this location.")
                st.stop()

            risk, message = get_risk(safe_temp)

            st.write(f"📍 Location: **{safe_display}**")
            st.write(
                f"🌡️ Temperature: **{safe_temp:.1f}°C** — "
                f"Risk: **{risk.upper()}** — Source: **{safe_source}**"
            )

            if safe_data.get("humidity") is not None:
                st.write(f"💧 Humidity: **{safe_data['humidity']}%**")

            if safe_data.get("apparent_temp") is not None:
                st.write(f"🥵 Feels like: **{safe_data['apparent_temp']:.1f}°C**")

            sent, info = send_alert_email(
                f"Safe Walk - {safe_display}",
                safe_temp,
                receiver=st.session_state.user_email
            )

            if sent:
                if risk in ["high", "extreme"]:
                    st.warning(
                        f"⚠️ {risk.upper()} heat zone! Latest temperature emailed successfully."
                    )
                else:
                    st.success("📧 Latest Safe Walk temperature emailed successfully.")
            else:
                st.warning(f"Safe Walk temperature was checked, but email was not sent: {info}")

            st.session_state.safe_walk_last_risk = risk

            m = folium.Map(
                location=[safe_lat, safe_lon],
                zoom_start=12,
                tiles="OpenStreetMap"
            )
            color_map = {
                "extreme": "red",
                "high": "orange",
                "normal": "green",
                "unknown": "gray"
            }
            folium.CircleMarker(
                [safe_lat, safe_lon],
                radius=12,
                color=color_map.get(risk, "gray"),
                fill=True,
                fill_color=color_map.get(risk, "gray"),
                fill_opacity=0.7,
                popup=f"{safe_display}: {safe_temp:.1f}°C",
            ).add_to(m)
            st_folium(m, width=None, height=300)

        except Exception as e:
            st.error(f"Safe Walk {safe_source} error: {e}")

st.markdown("<br><div style='text-align:center; color:#5a6b85; font-size:12px;'>Heat Guardian • Intelligent Heat Risk Monitoring • Powered by FortyGuard • Created by Dawood </div>", unsafe_allow_html=True)
