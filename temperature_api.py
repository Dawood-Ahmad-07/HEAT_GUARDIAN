from dotenv import load_dotenv
load_dotenv()
from fortyguard import FortyGuardClient

client = FortyGuardClient()

def get_temperature_data(lat, lon, date, time):
    """Returns dict: temp, humidity, apparent_temp — ya None agar data na mile"""
    delta = 0.002
    polygon = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature", "properties": {},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [lon - delta, lat - delta],
                    [lon + delta, lat - delta],
                    [lon + delta, lat + delta],
                    [lon - delta, lat + delta],
                    [lon - delta, lat - delta],
                ]],
            },
        }],
    }

    response = client.create_heatmap(
        polygon_aoi=polygon,
        start_date=date,
        start_time=time,
        filter_type=1,
        granularity=60,
    )

    result = response.get("result", {})
    stats = result.get("stats_data", {})
    features = result.get("map_data", {}).get("features", [])

    def extract(field_names, stats_key=None):
        # pehle stats_data se try karo
        if stats_key and stats_key in stats:
            val = stats[stats_key].get("mean")
            if val is not None:
                return val
        # fallback: tiles se average nikalo
        for f_name in field_names:
            vals = [f["properties"].get(f_name) for f in features if f["properties"].get(f_name) is not None]
            if vals:
                return sum(vals) / len(vals)
        return None

    temp = extract(["average_temperature", "temperature"], "temperature_stats")
    humidity = extract(["relative_humidity_percent", "humidity"], "humidity_stats")
    apparent = extract(["apparent_temperature_celsius", "apparent_temperature"], "apparent_temperature_stats")

    return {
        "temp": temp,
        "humidity": humidity,
        "apparent_temp": apparent,
    }