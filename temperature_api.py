from dotenv import load_dotenv
load_dotenv()
from fortyguard import FortyGuardClient

client = FortyGuardClient()

def get_temperature_data(lat, lon, date, time):
    delta = 0.005  # thoda bada box, zyada tiles ke liye
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

    try:
        response = client.create_heatmap(
            polygon_aoi=polygon,
            start_date=date,
            start_time=time,
            filter_type=1,
            granularity=60,
        )
    except Exception as e:
        print(f"[ERROR] API call failed for ({lat},{lon}): {e}")
        return {"temp": None, "humidity": None, "apparent_temp": None}

    result = response.get("result", {})
    stats = result.get("stats_data", {})
    features = result.get("map_data", {}).get("features", [])

    print(f"[DEBUG] {lat},{lon} -> features count: {len(features)}, stats keys: {list(stats.keys())}")

    temp = None
    if features:
        temps = [f["properties"].get("average_temperature") for f in features if f["properties"].get("average_temperature") is not None]
        if temps:
            temp = sum(temps) / len(temps)

    if temp is None and "temperature_stats" in stats:
        temp = stats["temperature_stats"].get("mean") or stats["temperature_stats"].get("average")

    return {
        "temp": temp,
        "humidity": None,
        "apparent_temp": None,
    }