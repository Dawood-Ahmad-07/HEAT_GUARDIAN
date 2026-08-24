from dotenv import load_dotenv
from fortyguard import FortyGuardClient

load_dotenv()

client = FortyGuardClient()

DEFAULT_TEMP_THRESHOLD = 35.0


def _extract_value(params, keys):
    """Get the first available value from the given parameter keys."""
    for key in keys:
        values = params.get(key)

        if values:
            return values[0]

    return None


def _extract_temp_from_parameters(params):
    """Extract temperature from FortyGuard response."""

    preferred_keys = [
        "temperature_celsius",
        "air_temperature_celsius",
        "ambient_temperature_celsius",
        "2m_temperature_celsius",
    ]

    # Try actual temperature first
    temp = _extract_value(params, preferred_keys)

    if temp is not None:
        return temp

    # Fallback to apparent temperature
    temp = _extract_value(
        params,
        ["apparent_temperature_celsius"]
    )

    if temp is not None:
        return temp

    # Final temperature-like fallback
    for key, values in params.items():

        if not values:
            continue

        key_lower = key.lower()

        if (
            "temp" in key_lower
            and "apparent" not in key_lower
            and "heat_index" not in key_lower
            and "wet_bulb" not in key_lower
        ):
            return values[0]

    return None


def get_temperature_data(lat, lon, date, time):
    """
    Get temperature/environmental data directly from FortyGuard.
    """

    try:

        response = client.environmental_parameters(
            latitude=float(lat),
            longitude=float(lon),

            temperature=DEFAULT_TEMP_THRESHOLD,

            start_date=date,
            start_time=time,

            end_date=date,
            end_time=time,

            filter_type=1,
        )

    except Exception as e:

        print(
            f"[ERROR] FortyGuard request failed "
            f"({lat}, {lon}): {e}"
        )

        return {
            "temp": None,
            "humidity": None,
            "apparent_temp": None,
            "heat_index": None,
        }

    result = response.get("result", {})

    locations = result.get("locations", [])

    if not locations:

        print(
            f"[DEBUG] FortyGuard returned no location "
            f"for ({lat}, {lon})"
        )

        return {
            "temp": None,
            "humidity": None,
            "apparent_temp": None,
            "heat_index": None,
        }

    params = locations[0].get("parameters", {})

    print(
        f"[DEBUG] FortyGuard parameters "
        f"({lat}, {lon}): {list(params.keys())}"
    )

    temp = _extract_temp_from_parameters(params)

    humidity = _extract_value(
        params,
        ["relative_humidity_percent"]
    )

    apparent_temp = _extract_value(
        params,
        ["apparent_temperature_celsius"]
    )

    heat_index = _extract_value(
        params,
        ["heat_index_celsius"]
    )

    print(
        f"[DEBUG] ({lat}, {lon}) "
        f"temp={temp}, "
        f"humidity={humidity}, "
        f"apparent={apparent_temp}, "
        f"heat_index={heat_index}"
    )

    return {
        "temp": temp,
        "humidity": humidity,
        "apparent_temp": apparent_temp,
        "heat_index": heat_index,
    }


def _build_polygon(lat, lon, delta):

    return {
        "type": "FeatureCollection",

        "features": [
            {
                "type": "Feature",

                "properties": {},

                "geometry": {
                    "type": "Polygon",

                    "coordinates": [
                        [
                            [lon - delta, lat - delta],
                            [lon + delta, lat - delta],
                            [lon + delta, lat + delta],
                            [lon - delta, lat + delta],
                            [lon - delta, lat - delta],
                        ]
                    ],
                },
            }
        ],
    }


def get_heatmap_tiles(
    lat,
    lon,
    date,
    time,
    delta=0.01,
    granularity=60,
):
    """
    Heavy FortyGuard heatmap request.
    Only call this when the user requests heatmap.
    """

    polygon = _build_polygon(
        lat,
        lon,
        delta
    )

    try:

        response = client.create_heatmap(
            polygon_aoi=polygon,

            start_date=date,
            start_time=time,

            filter_type=1,

            granularity=granularity,
        )

    except Exception as e:

        print(
            f"[ERROR] FortyGuard heatmap failed "
            f"({lat}, {lon}): {e}"
        )

        return {
            "temp": None,
            "tiles": [],
        }

    result = response.get(
        "result",
        {}
    )

    stats = result.get(
        "stats_data",
        {}
    )

    map_data = result.get(
        "map_data",
        {}
    )

    features = map_data.get(
        "features",
        []
    )

    tiles = []

    for feature in features:

        properties = feature.get(
            "properties",
            {}
        )

        temp = properties.get(
            "average_temperature"
        )

        if temp is None:
            continue

        geometry = feature.get(
            "geometry",
            {}
        )

        coords = geometry.get(
            "coordinates"
        )

        centroid = None

        try:

            if geometry.get("type") == "Polygon" and coords:

                ring = coords[0]

                lons = [
                    point[0]
                    for point in ring
                ]

                lats = [
                    point[1]
                    for point in ring
                ]

                centroid = (
                    sum(lats) / len(lats),
                    sum(lons) / len(lons),
                )

        except Exception:

            centroid = None

        if centroid:

            tiles.append(
                {
                    "lat": centroid[0],
                    "lon": centroid[1],
                    "temp": temp,
                }
            )

    mean_temp = None

    temps = []

    for feature in features:

        temp = feature.get(
            "properties",
            {}
        ).get(
            "average_temperature"
        )

        if temp is not None:
            temps.append(temp)

    if temps:

        mean_temp = sum(temps) / len(temps)

    if (
        mean_temp is None
        and "temperature_stats" in stats
    ):

        temperature_stats = stats[
            "temperature_stats"
        ]

        mean_temp = (
            temperature_stats.get("mean")
            or temperature_stats.get("average")
        )

    return {
        "temp": mean_temp,
        "tiles": tiles,
    }