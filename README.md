# 🌡️ Heat Guardian

**Real-time, hyperlocal heat-risk monitoring — powered by FortyGuard's Temperature Intelligence.**

Built for **FortyGuard Hackathon '26** — Track 6: Agentic AI (primary), with Track 1: Resilient Cities & Infrastructure as a bonus angle.

 **GitHub Repo:** [github.com/Dawood-Ahmad-07/HEAT_GUARDIAN](https://github.com/Dawood-Ahmad-07/HEAT_GUARDIAN) &nbsp;

**LinkedIn:** [linkedin.com/in/dawood-ahmad-b16bba378](https://www.linkedin.com/in/dawood-ahmad-b16bba378)


 **Live App Demo:** [fortygurad-heat-guardian.streamlit.app](https://fortygurad-heat-guardian-8rtge5gtmxckvrkmflylef.streamlit.app/)

<p align="center">
  <img src="docs/screenshots/dashboard.png.png" alt="Heat Guardian dashboard" width="1000"/>
</p>

---

## 📋 Overview

| **Field** | **Details** |
|---|---|
| **Project** | Heat Guardian |
| **Author** | Dawood Ahmad |
| **Primary Track** | Track 6 — Agentic AI |
| **Secondary Track** | Track 1 — Resilient Cities & Infrastructure |
| **Core Data Source** | FortyGuard Temperature API (`/v1/heatmap`) |
| **Fallback Data Source** | Open-Meteo (free, no API key required, global coverage) |
| **Reasoning Engine** | Groq — `openai/gpt-oss-20b` |
| **Frontend** | Streamlit |

---

## 🧠 What It Does

Heat Guardian doesn't just display a temperature — it **watches, reasons, and acts**. A user signs in with Gmail, selects a location, and from that point forward three autonomous agents take over:

- One **plans low-heat routes** on request.
- One **continuously monitors** the user's live location and emails them the moment conditions turn dangerous.
- One **decides — every single time** — whether a new alert is genuinely warranted or just noise.

<p align="center">
  <img src="docs/screenshots/signin.png.jpeg" alt="Sign in screen" width="300"/>
  <img src="docs/screenshots/risk_card.png.png" alt="Risk level card" width="400"/>
</p>

---

## 🤖 Track 6 — Agentic AI (Primary)

Judges look for genuine **perceive → reason → act** loops that run without a human in the loop at each step — not a chatbot wrapper. Heat Guardian implements three such agents.

| **Agent** | **Perceives** | **Reasons** | **Acts** |
|---|---|---|---|
| **AI Route-Planning Agent**<br>`route_planner.py` | Free-form natural-language questions (e.g. *"Phoenix to New York, suggest a route with low temperature"*) via regex-based entity extraction — no fixed template required | Independently selects FortyGuard vs. Open-Meteo depending on whether the question needs live/forecast data or hyperlocal historical data | Queries every stop, ranks by temperature, and returns a synthesized natural-language recommendation via a Groq LLM — a justified decision, not just raw numbers |
| **Safe Walk Monitoring Agent**<br>(continuous loop) | The user's live GPS or fixed location, re-sampled on a user-chosen interval (10 sec → 1 hr) via `st_autorefresh` | Evaluates each fetched temperature reading against Normal / High / Extreme risk thresholds | Sends an email autonomously the instant risk crosses into High or Extreme — zero further input from the user once the loop is started |
| **Duplicate-Aware Alerting Agent**<br>(`alert_key` gate) | Every new temperature reading | Determines whether the reading constitutes new information worth an alert, or a repeat that should be suppressed | Either fires or withholds the email — a genuine judgment call applied at every check, not a blunt "temp > X → email" rule |

<p align="center">
  <img src="docs/screenshots/ai_chatbot.png.png" alt="AI route planner" width="900"/>
</p>

<p align="center">
  <img src="docs/screenshots/safe_walk.png.png" alt="Safe Walk Mode" width="900"/>
</p>

**Why this counts as agentic, not just "an app that calls an LLM":** the Safe Walk agent is given an intent once (*"watch over me"*) and then perceives, decides, and acts repeatedly and unattended for as long as it runs — the defining property of an agent loop, not a single request/response exchange.

---

## 🏙️ Track 1 — Resilient Cities & Infrastructure (Bonus)

| **Capability** | **City-Resilience Relevance** |
|---|---|
| **Hyperlocal heat map**<br>(FortyGuard `/v1/heatmap`, 2 m resolution) | Street-level heat visibility for 24 US cities plus any manual US location — the granularity real urban planning requires, not a citywide average |
| **Safe Walk Mode** | Functions as pedestrian-protection infrastructure — the same category of intervention a city public-health department would want deployed at scale |
| **Risk-colored Folium maps** | At-a-glance visibility for residents, planners, or emergency services into which parts of a city are currently dangerous |
| **Cool-route planning** | Reframable as guidance for outdoor workers, delivery routes, or transit planning to minimize city-wide heat exposure |
| **US-only + `2021-01-01` → today compliance, automatic Open-Meteo fallback** | Respects FortyGuard's data-coverage rules and degrades gracefully instead of failing outside them |

<p align="center">
  <img src="docs/screenshots/heat_map.png.png" alt="City heat map" width="800"/>
</p>

---

## 🗺️ Dashboard Walkthrough

| **Step** | **What Happens** |
|---|---|
| **1. Sign In** | Gmail-gated entry point — this email becomes the destination for all future alerts |
| **2. Choose Location** | Dropdown (24 US cities) · Manual city + lat/lon · Live GPS |
| **3. Choose Data Source** | FortyGuard (hyperlocal) or Open-Meteo (global fallback) — user can override the agent's default |
| **4. View Risk** | Temperature card + color-coded risk card (Normal / High / Extreme) + stat card |
| **5. On-Demand Heat Map** | Separate button, kept decoupled from the fast temperature check for performance |
| **6. Ask the AI** | Natural-language route question → agent reasons → ranked route + coolest stop |
| **7. Enable Safe Walk** | Continuous unattended monitoring with automatic email alerts on risk escalation |

---

## 🏗️ Architecture

| **Layer** | **Technology** |
|---|---|
| **Frontend** | Streamlit, custom CSS (glassmorphism, dark navy theme, animated backgrounds) |
| **Hyperlocal Heat Data** | FortyGuard Temperature API — `/v1/heatmap` (async submit-and-poll) |
| **Fallback / Live Global Weather** | Open-Meteo — current conditions, 16-day forecast, and geocoding |
| **Agentic Reasoning** | Groq — `openai/gpt-oss-20b` |
| **Maps** | Folium + `streamlit-folium` |
| **Continuous Monitoring** | `streamlit-autorefresh` |
| **Alerts** | Email, tied to the Gmail identity captured at sign-in |

```
User → Streamlit UI → [FortyGuard | Open-Meteo] → Risk Engine → {Map, Cards, Email Agent}
                                                 ↘ AI Route Agent (Groq LLM) ↗
```

---

## 📌 Why Track 6 First

Track 1's resilience story only works **because of** Track 6's agents. A city cannot staff a person to watch every resident's local temperature and email them at the right moment — an agent can. Heat Guardian's core claim is that hyperlocal temperature data becomes genuinely protective infrastructure only once it is paired with autonomous perceive-reason-act loops, rather than a dashboard someone has to remember to check. The agent does the work; Track 1 is what that work is for.

---

**Built by Dawood Ahmad for FortyGuard Hackathon '26.**
