from dotenv import load_dotenv

load_dotenv()

from fortyguard import FortyGuardClient

client = FortyGuardClient()

# Placeholder threshold value required by the API.
DEFAULT_TEMP_THRESHOLD = 35.0


def _extract_value(params, keys):
    """Return the first value found in params for any of the given keys."""
    for key in keys:
        values = params.get(key)

        if values:
            return values[0]

    return None


def _extract_temp_from_parameters(params):
    """
    FortyGuard Environmental Parameters response does not currently
    return a plain temperature_celsius field.

    Therefore, use apparent_temperature_celsius as the fallback
    temperature value for the heat-risk application.
    """

    preferred = [
        "temperature_celsius",
        "air_temperature_celsius",
        "ambient_temperature_celsius",
        "2m_temperature_celsius",
    ]

    # First try actual temperature fields if they ever become available.
    temp = _extract_value(params, preferred)

    if temp is not None:
        return temp

    # Fallback to apparent/feels-like temperature.
    apparent_temp = _extract_value(
        params,
        ["apparent_temperature_celsius"]
    )

    if apparent_temp is not None:
        return apparent_temp

    # Final fallback: search for another temperature-like key.
    for key, values in params.items():
        lower = key.lower()

        if (
            "temp" in lower
            and not any(
                x in lower
                for x in (
                    "apparent",
                    "heat_index",
                    "wet_bulb",
                )
            )
        ):
            if values:
                return values[0]

    return None


def get_temperature_data(lat, lon, date, time):
    """
    FAST path — single-point Environmental Parameters lookup.

    Used by the main "Check Temperature" button and AI route planner.

    FortyGuard currently returns:
        - apparent_temperature_celsius
        - heat_index_celsius
        - relative_humidity_percent
        - wet_bulb_temperature_celsius

    Since raw temperature is not returned, apparent temperature
    is used as the fallback value for `temp`.
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
            f"[ERROR] Environmental Parameters call failed "
            f"for ({lat},{lon}): {e}"
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
            f"[DEBUG][envparams] {lat},{lon} -> "
            f"no locations returned. "
            f"metadata={result.get('metadata', {})}"
        )

        return {
            "temp": None,
            "humidity": None,
            "apparent_temp": None,
            "heat_index": None,
        }

    params = locations[0].get("parameters", {})

    print(
        f"[DEBUG][envparams] {lat},{lon} -> "
        f"parameter keys: {list(params.keys())}"
    )

    # Temperature:
    # Raw temperature is unavailable, so this falls back
    # to apparent_temperature_celsius.
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
        f"[DEBUG][envparams] {lat},{lon} -> "
        f"temp={temp}, "
        f"apparent_temp={apparent_temp}, "
        f"heat_index={heat_index}, "
        f"humidity={humidity}"
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
    SLOW / heavy path — used only when the user explicitly
    requests a visual heat map.
    """

    polygon = _build_polygon(lat, lon, delta)

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
            f"[ERROR] Heatmap API call failed "
            f"for ({lat},{lon}): {e}"
        )

        return {
            "temp": None,
            "tiles": [],
        }

    result = response.get("result", {})

    stats = result.get("stats_data", {})

    features = result.get(
        "map_data",
        {}
    ).get(
        "features",
        []
    )

    print(
        f"[DEBUG][heatmap] {lat},{lon} -> "
        f"features count: {len(features)}, "
        f"stats keys: {list(stats.keys())}"
    )

    tiles = []

    for feature in features:

        props = feature.get("properties", {})

        temp = props.get("average_temperature")

        if temp is None:
            continue

        geom = feature.get("geometry", {})

        coords = geom.get("coordinates")

        centroid = None

        try:
            if geom.get("type") == "Polygon" and coords:

                ring = coords[0]

                lons = [point[0] for point in ring]
                lats = [point[1] for point in ring]

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

    if features:

        temps = [
            feature["properties"].get(
                "average_temperature"
            )
            for feature in features
            if feature["properties"].get(
                "average_temperature"
            ) is not None
        ]

        if temps:
            mean_temp = sum(temps) / len(temps)

    if mean_temp is None and "temperature_stats" in stats:

        temperature_stats = stats["temperature_stats"]

        mean_temp = (
            temperature_stats.get("mean")
            or temperature_stats.get("average")
        )

    return {
        "temp": mean_temp,
        "tiles": tiles,
    }