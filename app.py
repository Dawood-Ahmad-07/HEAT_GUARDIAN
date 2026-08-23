import streamlit as st
import folium
from streamlit_folium import st_folium
from datetime import date, timedelta
from temperature_api import get_temperature_data
from alert_logic import get_risk
from email_alert import send_alert_email
from route_planner import ask_ai_route
from waypoints import US_CITIES
from streamlit_geolocation import streamlit_geolocation
from streamlit_autorefresh import st_autorefresh
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
location_mode = st.radio(
    "📍 Location Input Method",
    ["Select from List", "Manual (City + Lat/Lon)"],
    horizontal=True
)

manual_lat = None
manual_lon = None

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
else:
    c1, c2, c3, c4, c5 = st.columns([2, 1, 1, 1.3, 1.3])
    with c1:
        location_name = st.text_input("📍 City Name (manual)", placeholder="e.g. Multan, PK")
    with c2:
        manual_lat = st.number_input("🌐 Latitude", value=33.4484, format="%.4f")
    with c3:
        manual_lon = st.number_input("🌐 Longitude", value=-112.0740, format="%.4f")
    with c4:
        check_date = st.date_input("📅 Date", value=DEFAULT_DATE)
    with c5:
        hour = st.slider("🕐 Hour", 0, 23, 14)
    check = st.button("🌡️ Check Temperature", type="primary", use_container_width=True)

time_formatted = f"{hour:02d}:00"

# ---------- Session state defaults (FAKE static data — no API call on load) ----------
if "temp_result" not in st.session_state:
    st.session_state.temp_result = {"temp": 41.3, "humidity": None, "apparent_temp": None}
    st.session_state.temp_location = ("Phoenix, AZ", 33.4484, -112.0740)

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

# ---------- On button click, real API call ----------
if check:
    if location_mode == "Select from List":
        lat, lon = LOCATIONS[location_name]
        loc_display = location_name
    else:
        if not location_name:
            st.error("Please enter a city name.")
            st.stop()
        if manual_lat is None or manual_lon is None:
            st.error("Please enter valid latitude and longitude.")
            st.stop()
        lat, lon = manual_lat, manual_lon
        loc_display = location_name

    with st.spinner("Fetching temperature data this may take 8-10 seconds..."):
        try:
            data = get_temperature_data(lat, lon, str(check_date), time_formatted)
            st.session_state.temp_result = data
            st.session_state.temp_location = (loc_display, lat, lon)
        except Exception as e:
            st.error(f"Error fetching data: {e}")

# ---------- Display temperature result ----------
if st.session_state.temp_result is not None:
    data = st.session_state.temp_result
    location_name_disp, lat, lon = st.session_state.temp_location
    temp = data["temp"]
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
                <div class="lbl">🌡️ Temperature</div>
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

if temp is not None and temp > 30:
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

    with col_right:
        st.markdown('<div class="map-box"><h4>🗺️ Heat Map</h4>', unsafe_allow_html=True)
        m = folium.Map(location=[lat, lon], zoom_start=11, tiles="CartoDB positron")
        color_map = {"extreme": "red", "high": "orange", "normal": "green", "unknown": "gray"}
        folium.CircleMarker(
            [lat, lon], radius=16, color=color_map[risk], fill=True,
            fill_color=color_map[risk], fill_opacity=0.7,
            popup=f"{location_name_disp}: {temp:.1f}°C" if temp else location_name_disp,
        ).add_to(m)
        st_folium(m, width=None, height=380)
        st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)


# ---------- AI Chatbot ----------
col_a, col_b = st.columns([1, 1.3])

with col_a:
    with st.container(border=True):
        st.subheader("✨ Ask Heat Guardian AI")
        st.caption("Get intelligent route recommendations based on temperature data")

        user_question = st.text_input(
            "Your travel question",
            value="I need to go from Phoenix to New York, suggest a route with low temperature"
        )
        ai_date = st.date_input("Date for route check", value=DEFAULT_DATE, key="ai_date_input")
        ask = st.button("✨ Ask Heat Guardian AI", type="primary", use_container_width=True)

if ask:
    if user_question:
        mentioned = [c for c in US_CITIES if c.lower() in user_question.lower()]
        with st.spinner("Checking temperatures... this may take 10-20 seconds"):
            try:
                from route_planner import ask_ai
                answer, result = ask_ai(user_question, mentioned, travel_date=str(ai_date))
                st.session_state.ai_answer = answer
                st.session_state.ai_result = result
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

            if st.session_state.ai_plan:
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

                if coolest:
                    st.markdown(f"""
                    <div class="email-banner" style="text-align:center;">
                        ❄️ Coolest stop: <b>{coolest['city']}</b> at {coolest['temp']:.1f}°C
                    </div>
                    """, unsafe_allow_html=True)

           
        st.markdown('</div>', unsafe_allow_html=True)
        
st.markdown("---")

with st.container(border=True):
    st.subheader("🚶 Safe Walk Mode")
    st.caption("Enable to continuously monitor your live location and get instant alert only for US states")
    st.caption("Disclaimer: Currently not available because Fortyguard API does not support live location monitoring.")

    interval_options = {
        "Every 30 seconds": 30,
        "Every 1 minute": 60,
        "Every 5 minutes": 300,
        "Every 15 minutes": 900,
        "Every 30 minutes": 1800,
        "Every 1 hour": 3600,
    }
    selected_interval_label = st.selectbox("⏱️ Check location every:", list(interval_options.keys()))
    selected_interval_seconds = interval_options[selected_interval_label]

    toggle = st.toggle("Enable Safe Walk Mode", value=st.session_state.safe_walk_active)
    st.session_state.safe_walk_active = toggle

    if st.session_state.safe_walk_active:
        st.info(f"📡 Live monitoring active — checking your location {selected_interval_label.lower()}")
        st_autorefresh(interval=selected_interval_seconds * 1000, key="safe_walk_refresh")

        location_data = streamlit_geolocation()

        if location_data and location_data.get("latitude") is not None:
            live_lat = location_data["latitude"]
            live_lon = location_data["longitude"]

            with st.spinner("Checking current heat risk..."):
                try:
                    data = get_temperature_data(live_lat, live_lon, str(DEFAULT_DATE), "14:00")
                    temp = data["temp"]
                    if temp is not None:
                        risk, message = get_risk(temp)

                        st.write(f"📍 Current location: ({live_lat:.3f}, {live_lon:.3f})")
                        st.write(f"🌡️ Temperature: {temp:.1f}°C — Risk: **{risk.upper()}**")

                        if risk in ["high", "extreme"] and st.session_state.safe_walk_last_risk != risk:
                            sent, info = send_alert_email(f"Live location ({live_lat:.2f}, {live_lon:.2f})", temp, receiver=st.session_state.user_email)
                            if sent:
                                st.warning(f"⚠️ You've entered a {risk.upper()} heat zone! Alert email sent.")
                            st.session_state.safe_walk_last_risk = risk
                        elif risk == "normal":
                            st.session_state.safe_walk_last_risk = None
                    else:
                        st.warning("No temperature data available for this location (may be outside U.S. coverage).")
                except Exception as e:
                    st.error(f"Error checking location: {e}")
        else:
            st.info("Waiting for location permission — please allow location access in your browser.")
st.markdown("<br><div style='text-align:center; color:#5a6b85; font-size:12px;'>Heat Guardian • Intelligent Heat Risk Monitoring • Powered by FortyGuard • Created by Dawood </div>", unsafe_allow_html=True)