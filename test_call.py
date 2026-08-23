from dotenv import load_dotenv
load_dotenv()
from fortyguard import FortyGuardClient
import json

client = FortyGuardClient()

response = client.create_heatmap(
    polygon_aoi={
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature", "properties": {},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [-112.076, 33.4464], [-112.072, 33.4464],
                    [-112.072, 33.4504], [-112.076, 33.4504],
                    [-112.076, 33.4464],
                ]],
            },
        }],
    },
    start_date="2024-07-15",
    start_time="14:00",
    filter_type=1,
    granularity=60,
)

with open("sample_response.json", "w") as f:
    json.dump(response, f, indent=2)

print("Saved!")
print("stats_data keys:", response["result"]["stats_data"].keys())
print("first feature properties:", response["result"]["map_data"]["features"][0]["properties"])