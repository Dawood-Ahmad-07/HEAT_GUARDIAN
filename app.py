import streamlit as st
import folium
from streamlit_folium import st_folium
from datetime import date, timedelta
from temperature_api import get_temperature_data
from alert_logic import get_risk
from email_alert import send_alert_email
from route_planner import ask_ai_route
from waypoints import US_CITIES

st.set_page_config(page_title="Heat Guardian", page_icon="🌡️", layout="wide")
# ---------- Sign-in gate ----------
# ---------- Sign-in gate ----------
if "user_email" not in st.session_state:
    st.session_state.user_email = None

if st.session_state.user_email is None:
    st.markdown("""
    <style>
    .signin-wrap {
        display:flex;
        flex-direction:column;
        align-items:center;
        justify-content:center;
        padding-top: 60px;
    }
    .signin-logo {
        background:linear-gradient(135deg,#ff5c5c,#ff8c42);
        width:72px; height:72px;
        border-radius:20px;
        display:flex; align-items:center; justify-content:center;
        font-size:36px;
        box-shadow:0 8px 24px rgba(255,92,92,0.35);
        margin-bottom:18px;
    }
    .signin-title {
        font-size:34px;
        font-weight:800;
        color:#ffffff;
        margin:0;
        letter-spacing:-0.5px;
    }
    .signin-sub {
        color:#7a92b5;
        font-size:15px;
        margin-top:6px;
        margin-bottom:36px;
        text-align:center;
    }
    </style>

    <div class="signin-wrap">
        <div class="signin-logo">🌡️</div>
        <p class="signin-title">Heat Guardian</p>
        <p class="signin-sub">Sign in to receive real-time heat alerts on your Gmail</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        with st.container(border=True):
            email_input = st.text_input("📧 Gmail address", placeholder="you@gmail.com")
            if st.button("Sign in with Gmail", type="primary", use_container_width=True):
                if email_input and "@gmail.com" in email_input:
                    st.session_state.user_email = email_input
                    st.rerun()
                else:
                    st.warning("Please enter a valid Gmail address.")

    st.stop()
# ---------- CSS ----------
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
}
.temp-card .loc { font-size: 15px; color: #ffd9d9; margin-bottom: 6px; }
.temp-card .val { font-size: 52px; font-weight: 800; margin: 0; }
.temp-card .lbl { font-size: 13px; color: #ffd9d9; margin-top: 8px; }

.risk-card {
    background-color: #2a1414;
    border-radius: 16px;
    padding: 24px;
    height: 100%;
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
}
.stat-card .icon { font-size: 22px; margin-bottom: 6px; }
.stat-card .lbl { font-size: 13px; color: #8fa3bf; }
.stat-card .val { font-size: 22px; font-weight: 700; }

.map-box {
    background-color: #12223d;
    border-radius: 16px;
    padding: 14px;
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
    background-color: #0e1a30;
    border-radius: 12px;
    padding: 16px;
    text-align: center;
}
.route-card.coolest { border: 2px solid #4ade80; }
.route-card h5 { margin: 0; font-size: 14px; color: #cccccc; }
.route-card p { margin: 6px 0 0 0; font-size: 20px; font-weight: 700; }

footer, #MainMenu { visibility: hidden; }
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

# ---------- On button click, real API call ----------
if check:
    lat, lon = LOCATIONS[location_name]
    with st.spinner("Fetching temperature data please wait..."):
        try:
            data = get_temperature_data(lat, lon, str(check_date), time_formatted)
            st.session_state.temp_result = data
            st.session_state.temp_location = (location_name, lat, lon)
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
st.markdown("---")

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
        if len(mentioned) >= 2:
            start_city, end_city = mentioned[0], mentioned[1]
            with st.spinner("Checking temperatures across route... this may take 10-20 seconds"):
                try:
                    answer, plan = ask_ai_route(user_question, start_city, end_city, travel_date=str(ai_date))
                    st.session_state.ai_answer = answer
                    st.session_state.ai_plan = plan
                except Exception as e:
                    st.session_state.ai_answer = f"Error: {e}"
                    st.session_state.ai_plan = None
        else:
            st.warning("Please mention two valid US city names.")
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

st.markdown("<br><div style='text-align:center; color:#5a6b85; font-size:12px;'>Heat Guardian • Intelligent Heat Risk Monitoring • Powered by FortyGuard • Created by Dawood </div>", unsafe_allow_html=True)