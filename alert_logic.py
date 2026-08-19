def get_risk(temp_c):
    if temp_c is None:
        return "unknown", "Data unavailable"
    if temp_c >= 40:
        return "extreme", f"⚠️ EXTREME HEAT: {temp_c:.1f}°C — Stay indoors, hydrate."
    elif temp_c >= 30:
        return "high", f"🔶 HIGH HEAT: {temp_c:.1f}°C — Avoid prolonged sun exposure."
    else:
        return "normal", f"✅ Normal: {temp_c:.1f}°C — Safe conditions."