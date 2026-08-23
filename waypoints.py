US_CITIES = {
    # Arizona
    "Phoenix": (33.4484, -112.0740),
    "Tucson": (32.2226, -110.9747),
    "Flagstaff": (35.1983, -111.6513),
    "Mesa": (33.4152, -111.8315),
    "Scottsdale": (33.4942, -111.9261),

    # California
    "Los Angeles": (34.0522, -118.2437),
    "San Jose": (37.3382, -121.8863),
    "San Francisco": (37.7749, -122.4194),
    "Sacramento": (38.5816, -121.4944),

    # Other major cities
    "Las Vegas": (36.1699, -115.1398),
    "Denver": (39.7392, -104.9903),
    "Albuquerque": (35.0844, -106.6504),
    "Oklahoma City": (35.4676, -97.5164),
    "Dallas": (32.7767, -96.7970),
    "St. Louis": (38.6270, -90.1994),
    "Chicago": (41.8781, -87.6298),
    "Indianapolis": (39.7684, -86.1581),
    "Columbus": (39.9612, -82.9988),
    "Pittsburgh": (40.4406, -79.9959),
    "Philadelphia": (39.9526, -75.1652),
    "New York": (40.7128, -74.0060),
    "Miami": (25.7617, -80.1918),
    "Atlanta": (33.7490, -84.3880),
}


def get_route_cities(start, end, num_points=4):
    """
    Start aur end ke beech, seedha coordinates interpolate karke
    waypoints nikalta hai — kisi bhi do cities ke liye kaam karega,
    chahe predefined route ho ya na ho (jaise ek hi state ke andar).
    """
    if start not in US_CITIES or end not in US_CITIES:
        return [start, end]

    lat1, lon1 = US_CITIES[start]
    lat2, lon2 = US_CITIES[end]

    route = [start]

    # Beech ke coordinates nikalo (seedhi line pe points)
    for i in range(1, num_points - 1):
        frac = i / (num_points - 1)
        lat = lat1 + (lat2 - lat1) * frac
        lon = lon1 + (lon2 - lon1) * frac
        # Sabse nazdeeki known city dhundo is point ke
        nearest = min(
            US_CITIES.items(),
            key=lambda c: (c[1][0] - lat) ** 2 + (c[1][1] - lon) ** 2
        )[0]
        if nearest not in route and nearest != end:
            route.append(nearest)

    route.append(end)
    return route