import streamlit as st # type: ignore[import-not-found]
import folium # type: ignore[import-not-found]
from streamlit_folium import st_folium # pyright: ignore[reportMissingImports]

from temperature_api import get_temperature_data
from alert_logic import get_risk
from email_alert import send_alert_email


# ---------- Page config ----------
st.set_page_config(
    page_title="Heat Guardian",
    page_icon="🌡️",
    layout="centered"
)


# ---------- Custom CSS ----------
st.markdown("""
<style>
.header {
    background-color: #0a2540;
    color: white;
    padding: 26px;
    border-radius: 0 0 20px 20px;
    text-align: center;
    margin-bottom: 20px;
}

.header h1 {
    margin: 0;
    font-size: 30px;
}

.header p {
    margin: 6px 0 0 0;
    font-size: 42px;
    font-weight: bold;
}

.card-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px;
    margin-top: 10px;
}

.card {
    background-color: #f5f7fa;
    border-radius: 18px;
    padding: 22px 16px;
    text-align: center;
    box-shadow: 0 2px 6px rgba(0,0,0,0.06);
}

.card .icon {
    font-size: 30px;
    margin-bottom: 8px;
}

.card h3 {
    margin: 0 0 10px 0;
    font-size: 14px;
    letter-spacing: 1px;
    color: #0a2540;
    font-weight: 700;
}

.card p {
    margin: 0;
    font-size: 20px;
    font-weight: bold;
    color: #0a2540;
}

.map-label {
    background-color: #f5f7fa;
    border-radius: 18px;
    padding: 16px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.06);
    margin-top: 14px;
}

.map-label h3 {
    margin: 0 0 10px 4px;
    font-size: 14px;
    letter-spacing: 1px;
    color: #0a2540;
    font-weight: 700;
}
</style>
""", unsafe_allow_html=True)


# ---------- Sample US locations ----------
LOCATIONS = {
    "Phoenix, AZ": (33.4484, -112.0740),
    "San Jose, CA": (37.3382, -121.8863),
    "New York, NY": (40.7128, -74.0060),
    "Miami, FL": (25.7617, -80.1918),
}


# ---------- Session State ----------
# Ye result ko Streamlit reruns ke baad bhi save rakhega.
if "weather_result" not in st.session_state:
    st.session_state.weather_result = None


# ---------- Input controls ----------
st.title("🌡️ Heat Guardian")
st.caption("Real-time hyperlocal heat risk monitoring")

location_name = st.selectbox(
    "📍 Search Location",
    list(LOCATIONS.keys())
)

date = st.date_input("📅 Date")

time_str = st.slider(
    "🕐 Hour",
    0,
    23,
    14
)

time_formatted = f"{time_str:02d}:00"

check = st.button(
    "Check Temperature",
    type="primary",
    use_container_width=True
)


# ==========================================================
# MAIN LOGIC
# ==========================================================

# ---------- Fetch new data only when button is clicked ----------
if check:

    lat, lon = LOCATIONS[location_name]

    with st.spinner("Fetching temperature data..."):

        try:
            # ------------------------------------------------
            # YOUR EXISTING TEMPERATURE API
            # ------------------------------------------------
            data = get_temperature_data(
                lat,
                lon,
                str(date),
                time_formatted
            )

            temp = data["temp"]
            humidity = data["humidity"]
            apparent_temp = data["apparent_temp"]

            # ------------------------------------------------
            # YOUR EXISTING ALERT/RISK LOGIC
            # ------------------------------------------------
            risk, message = get_risk(temp)

            # ------------------------------------------------
            # EMAIL ALERT
            # Same existing function — NOT disturbed
            # ------------------------------------------------
            email_sent = False
            email_info = None

            if temp is not None and temp > 30:

                sent, info = send_alert_email(
                    location_name,
                    temp
                )

                email_sent = sent
                email_info = info

            # ------------------------------------------------
            # SAVE EVERYTHING IN SESSION STATE
            # ------------------------------------------------
            st.session_state.weather_result = {
                "location_name": location_name,
                "lat": lat,
                "lon": lon,
                "date": str(date),
                "time": time_formatted,
                "temp": temp,
                "humidity": humidity,
                "apparent_temp": apparent_temp,
                "risk": risk,
                "message": message,
                "email_sent": email_sent,
                "email_info": email_info,
            }

        except Exception as e:
            st.error(f"Error fetching data: {e}")


# ==========================================================
# DISPLAY SAVED RESULT
# This part is OUTSIDE "if check"
# so result won't disappear after rerun.
# ==========================================================

if st.session_state.weather_result is not None:

    result = st.session_state.weather_result

    location_name = result["location_name"]
    lat = result["lat"]
    lon = result["lon"]
    temp = result["temp"]
    humidity = result["humidity"]
    apparent_temp = result["apparent_temp"]
    risk = result["risk"]
    message = result["message"]

    # ---------- Header ----------
    st.markdown(f"""
    <div class="header">
        <h1>{location_name}</h1>
        <p>{temp:.1f}°C</p>
    </div>
    """, unsafe_allow_html=True)


    # ---------- Card grid ----------
    # ---------- Alert box ----------
    if risk == "extreme":
        st.error(message)

    elif risk == "high":
        st.warning(message)

    elif risk == "normal":
        st.success(message)

    else:
        st.info(message)


    # ---------- Email status ----------
    # Email sirf button click ke waqt send hoti hai.
    # Yahan sirf saved status display ho raha hai.
    if temp is not None and temp > 30:

        if result["email_sent"]:
            st.info("📧 Alert email sent!")

        elif result["email_info"]:
            st.warning(
                f"Email not sent: {result['email_info']}"
            )


    # ---------- Heat map box ----------
    st.markdown("""
    <div class="map-label">
        <h3>🗺️ HEAT MAP</h3>
    </div>
    """, unsafe_allow_html=True)


    # ---------- Heat map ----------
    m = folium.Map(
        location=[lat, lon],
        zoom_start=13,
        tiles="CartoDB positron"
    )

    color_map = {
        "extreme": "red",
        "high": "orange",
        "normal": "green",
        "unknown": "gray"
    }

    folium.CircleMarker(
        [lat, lon],
        radius=18,
        color=color_map.get(risk, "gray"),
        fill=True,
        fill_color=color_map.get(risk, "gray"),
        fill_opacity=0.6,
        popup=(
            f"{location_name}: {temp:.1f}°C"
            if temp is not None
            else location_name
        ),
    ).add_to(m)

    st_folium(
        m,
        width=700,
        height=350
    )
