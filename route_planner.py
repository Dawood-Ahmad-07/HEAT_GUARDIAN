import os
from datetime import date
from concurrent.futures import ThreadPoolExecutor, as_completed
from groq import Groq
from temperature_api import get_temperature_data
from waypoints import US_CITIES, get_route_cities

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def _fetch_city_temp(city, date_str, time_str):
    lat, lon = US_CITIES[city]
    data = get_temperature_data(lat, lon, date_str, time_str)
    return {"city": city, "temp": data["temp"]}


def plan_route(start_city, end_city, travel_date=None, travel_hour=14):
    if travel_date is None:
        travel_date = str(date.today())
    time_str = f"{travel_hour:02d}:00"

    cities = get_route_cities(start_city, end_city)
    results = [None] * len(cities)

    with ThreadPoolExecutor(max_workers=len(cities)) as executor:
        future_to_index = {
            executor.submit(_fetch_city_temp, city, travel_date, time_str): i
            for i, city in enumerate(cities)
        }
        for future in as_completed(future_to_index):
            i = future_to_index[future]
            try:
                results[i] = future.result()
            except Exception:
                results[i] = {"city": cities[i], "temp": None}

    valid = [r for r in results if r["temp"] is not None]
    coolest = min(valid, key=lambda r: r["temp"]) if valid else None

    return {
        "route": results,
        "coolest_stop": coolest,
    }


def ask_ai_route(user_question, start_city, end_city, travel_date=None, travel_hour=14):
    plan = plan_route(start_city, end_city, travel_date, travel_hour)

    summary_lines = [f"{r['city']}: {r['temp']:.1f}°C" if r['temp'] is not None else f"{r['city']}: N/A" for r in plan["route"]]
    summary_text = "\n".join(summary_lines)
    coolest = plan["coolest_stop"]
    coolest_text = f"{coolest['city']} at {coolest['temp']:.1f}°C" if coolest else "unavailable"

    prompt = f"""You are Heat Guardian's travel assistant. A user asked: "{user_question}"

Route from {start_city} to {end_city}, with temperatures at each stop:
{summary_text}

The coolest stop is: {coolest_text}

Give a short, friendly, helpful answer (3-5 sentences) recommending the best route based on this temperature data, and mention which stop is coolest."""

    response = groq_client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[{"role": "user", "content": prompt}],
    )

    return response.choices[0].message.content, plan