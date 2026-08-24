import os
from datetime import date
from concurrent.futures import ThreadPoolExecutor, as_completed

from dotenv import load_dotenv
from groq import Groq

from temperature_api import get_temperature_data
from waypoints import US_CITIES, get_route_cities


load_dotenv()

groq_api_key = os.getenv("GROQ_API_KEY")

if not groq_api_key:
    raise RuntimeError(
        "GROQ_API_KEY is missing. Please add it to your .env file."
    )

groq_client = Groq(api_key=groq_api_key)


# ---------------------------------------------------------
# FortyGuard temperature
# ---------------------------------------------------------

def _fetch_fortyguard_temp(city, date_str, time_str):
    lat, lon = US_CITIES[city]

    data = get_temperature_data(
        lat,
        lon,
        date_str,
        time_str
    )

    return {
        "city": city,
        "temp": data.get("temp")
    }


# ---------------------------------------------------------
# Open-Meteo temperature
# ---------------------------------------------------------

def _fetch_openmeteo_temp(city, date_str):
    import requests

    lat, lon = US_CITIES[city]

    today = date.today()

    if date_str == str(today):

        response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m",
                "timezone": "auto",
            },
            timeout=10,
        )

        response.raise_for_status()

        data = response.json()

        temp = data.get("current", {}).get("temperature_2m")

    else:

        response = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "daily": "temperature_2m_max",
                "forecast_days": 16,
                "timezone": "auto",
            },
            timeout=10,
        )

        response.raise_for_status()

        data = response.json()

        dates = data.get("daily", {}).get("time", [])
        temps = data.get("daily", {}).get("temperature_2m_max", [])

        if date_str not in dates:
            temp = None
        else:
            index = dates.index(date_str)
            temp = temps[index]

    return {
        "city": city,
        "temp": temp
    }


# ---------------------------------------------------------
# Route planner
# ---------------------------------------------------------

def plan_route(
    start_city,
    end_city,
    travel_date=None,
    travel_hour=14,
    weather_source="FortyGuard Data",
):

    if travel_date is None:
        travel_date = str(date.today())

    time_str = f"{travel_hour:02d}:00"

    cities = get_route_cities(start_city, end_city)

    results = [None] * len(cities)

    # -----------------------------------------------------
    # Select weather source
    # -----------------------------------------------------

    if weather_source == "Open-Meteo Live":

        fetch_function = lambda city: _fetch_openmeteo_temp(
            city,
            travel_date
        )

    else:

        fetch_function = lambda city: _fetch_fortyguard_temp(
            city,
            travel_date,
            time_str
        )

    # -----------------------------------------------------
    # Parallel API calls
    # -----------------------------------------------------

    max_workers = min(len(cities), 5)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:

        future_to_index = {
            executor.submit(fetch_function, city): i
            for i, city in enumerate(cities)
        }

        for future in as_completed(future_to_index):

            index = future_to_index[future]

            try:

                results[index] = future.result()

            except Exception as e:

                results[index] = {
                    "city": cities[index],
                    "temp": None,
                    "error": str(e)
                }

    # -----------------------------------------------------
    # Find coolest valid stop
    # -----------------------------------------------------

    valid = [
        r for r in results
        if r and r.get("temp") is not None
    ]

    coolest = (
        min(valid, key=lambda r: r["temp"])
        if valid
        else None
    )

    return {
        "route": results,
        "coolest_stop": coolest,
        "weather_source": weather_source,
    }


# ---------------------------------------------------------
# AI explanation
# ---------------------------------------------------------

def ask_ai_route(
    user_question,
    start_city,
    end_city,
    travel_date=None,
    travel_hour=14,
    weather_source="FortyGuard Data",
):

    plan = plan_route(
        start_city,
        end_city,
        travel_date=travel_date,
        travel_hour=travel_hour,
        weather_source=weather_source,
    )

    summary_lines = []

    for r in plan["route"]:

        if r["temp"] is not None:

            summary_lines.append(
                f"{r['city']}: {r['temp']:.1f}°C"
            )

        else:

            summary_lines.append(
                f"{r['city']}: Temperature unavailable"
            )

    summary_text = "\n".join(summary_lines)

    coolest = plan["coolest_stop"]

    if coolest:

        coolest_text = (
            f"{coolest['city']} "
            f"at {coolest['temp']:.1f}°C"
        )

    else:

        coolest_text = "No temperature data available."

    prompt = f"""
You are Heat Guardian's travel assistant.

The user asked:
"{user_question}"

Weather data source:
{weather_source}

Route:
{start_city} → {end_city}

Temperature data collected from {weather_source}:

{summary_text}

Coolest stop:
{coolest_text}

IMPORTANT:
Do NOT invent temperatures.
Use ONLY the temperature data provided above.

Give a short, friendly explanation in 3-5 sentences.

Explain:
1. Which stop is coolest.
2. Which route/stops are better from a heat perspective.
3. Mention if any temperature data is unavailable.

The weather data has already been collected.
Your job is ONLY to explain and recommend based on it.
"""

    response = groq_client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
    )

    return (
        response.choices[0].message.content,
        plan
    )


# ---------------------------------------------------------
# App chatbot wrapper
# ---------------------------------------------------------

def ask_ai(
    user_question,
    mentioned_cities,
    travel_date=None,
    travel_hour=14,
    weather_source="FortyGuard Data",
):

    if not mentioned_cities or len(mentioned_cities) < 2:

        return (
            "I couldn't detect two valid U.S. cities in your question. "
            "Please mention both a starting city and a destination city, "
            "e.g. 'route from Phoenix to New York'.",
            None,
        )

    start_city = mentioned_cities[0]
    end_city = mentioned_cities[-1]

    return ask_ai_route(
        user_question,
        start_city,
        end_city,
        travel_date=travel_date,
        travel_hour=travel_hour,
        weather_source=weather_source,
    )