🌡️ Heat Guardian

Real-time hyperlocal heat-risk monitoring, powered by FortyGuard's Temperature Intelligence.

Built for FortyGuard Hackathon'26 — Track 6: Agentic AI (primary), with Track 1: Resilient Cities & Infrastructure as a bonus angle.

<p align="center">
  <img src="docs/screenshots/dashboard.png.png" alt="Heat Guardian dashboard" width="800"/>
</p><!-- Image path: docs/screenshots/dashboard.png.png -->---

📋 Overview

| 
Project| Heat Guardian
Author| Dawood Ahmad
Primary Track| Track 6 — Agentic AI
Secondary Track| Track 1 — Resilient Cities & Infrastructure
Core data source| FortyGuard Temperature API ("/v1/heatmap")
Fallback data source| Open-Meteo (free, no-key, global)
Reasoning engine| Groq — "openai/gpt-oss-20b"
Frontend| Streamlit

---

🧠 What it does

Heat Guardian doesn't just show a temperature — it watches, reasons, and acts.

A user signs in with Gmail, picks a location, and from that point on three autonomous agents take over: one plans low-heat routes on request, one continuously monitors the user's live location and emails them the moment conditions turn dangerous, and one decides — every single time — whether a new alert is actually warranted or just noise.

<p align="center">
  <img src="docs/screenshots/signin.png.jpeg" alt="Sign in screen" width="400"/>
  <img src="docs/screenshots/risk_card.png.png" alt="Risk level card" width="400"/>
</p><!-- Image paths:
docs/screenshots/signin.png.jpeg
docs/screenshots/risk_card.png.png
-->---

🤖 Track 6 — Agentic AI (Primary)

Judges look for perceive → reason → act loops that run without a human in the loop each step — not a chatbot wrapper. Heat Guardian has three:

Agent| Perceives| Reasons| Acts
AI Route-Planning Agent<br>("route_planner.py")| Free-form natural language question — regex-based entity extraction, no fixed template required| Independently picks FortyGuard vs Open-Meteo depending on whether the question needs live/forecast data or hyperlocal historical data| Queries every stop, ranks by temperature, and returns a synthesized natural-language recommendation via a Groq LLM
Safe Walk Monitoring Agent<br>(continuous loop)| User's live GPS or fixed location, re-sampled on a user-chosen interval via "st_autorefresh"| Evaluates fetched temperature against Normal / High / Extreme risk thresholds| Sends an email autonomously when risk crosses into High/Extreme
Duplicate-Aware Alerting Agent<br>("alert_key" gate)| Every new temperature reading| Decides whether this reading is new information worth an alert, or a repeat that should be suppressed| Either fires or withholds the email

<p align="center">
  <img src="docs/screenshots/ai_chatbot.png.png" alt="AI route planner" width="800"/>
</p><!-- Image path: docs/screenshots/ai_chatbot.png.png --><p align="center">
  <img src="docs/screenshots/safe_walk.png.png" alt="Safe Walk Mode" width="800"/>
</p><!-- Image path: docs/screenshots/safe_walk.png.png -->Why this counts as agentic and not just "an app that calls an LLM": the Safe Walk agent is given an intent once ("watch over me") and then perceives, decides, and acts repeatedly and unattended, for as long as it runs — the defining property of an agent loop, not a single request/response.

---

🏙️ Track 1 — Resilient Cities & Infrastructure (Bonus)

Capability| City-resilience relevance
Hyperlocal heat map (FortyGuard "/v1/heatmap", 2 m resolution)| Street-level heat visibility for 24 US cities + any manual US location
Safe Walk Mode| Functions as pedestrian-protection infrastructure
Risk-colored Folium maps| At-a-glance view of which parts of a city are currently dangerous
Cool-route planning| Guidance for outdoor workers, delivery routes, or transit planning
US-only + "2021-01-01"→today compliance, automatic Open-Meteo fallback| Respects FortyGuard's data-coverage rules and degrades gracefully

<p align="center">
  <img src="docs/screenshots/heat_map.png.png" alt="City heat map" width="800"/>
</p><!-- Image path: docs/screenshots/heat_map.png.png -->---

🗺️ Dashboard walkthrough

Step| What happens
1. Sign in| Gmail-gated entry point — this email becomes the destination for future alerts
2. Choose location| Dropdown (24 US cities) · Manual city + lat/lon · Live GPS
3. Choose data source| FortyGuard (hyperlocal) or Open-Meteo (global fallback)
4. View risk| Temperature card + color-coded risk card (Normal / High / Extreme)
5. On-demand heat map| Separate button for performance
6. Ask the AI| Natural-language route question → agent reasons → ranked route + coolest stop
7. Enable Safe Walk| Continuous unattended monitoring + auto-email on risk escalation

---

🏗️ Architecture

Layer| Tech
Frontend| Streamlit, custom CSS (glassmorphism, dark navy theme, animated backgrounds)
Hyperlocal heat data| FortyGuard Temperature API — "/v1/heatmap"
Fallback / live global weather| Open-Meteo — current + 16-day forecast + geocoding
Agentic reasoning| Groq — "openai/gpt-oss-20b"
Maps| Folium + "streamlit-folium"
Continuous monitoring| "streamlit-autorefresh"
Alerts| Email, tied to the Gmail identity captured at sign-in

User → Streamlit UI → [FortyGuard | Open-Meteo] → Risk Engine → {Map, Cards, Email Agent}
                                                 ↘ AI Route Agent (Groq LLM) ↗

---

📌 Why Track 6 first

Track 1's resilience story only works because of Track 6's agents.

A city can't staff a person to watch every resident's local temperature and email them at the right moment — an agent can.

Heat Guardian's core claim is that hyperlocal temperature data becomes genuinely protective infrastructure only once it's paired with autonomous perceive-reason-act loops, not a dashboard someone has to remember to check.

That's the agent doing the work — Track 1 is what the agent's work is for.

---

Built by Dawood Ahmad for FortyGuard Hackathon'26.
