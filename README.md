# Athens Urban Air Quality Monitoring & Exposure Assessment System

> A real-time ETL pipeline for air pollution monitoring, geospatial analysis, and population exposure assessment across the Athens metropolitan area.

---

## Research Context

This project aligns with research in **urban air quality modeling** and **population exposure assessment** — key areas of environmental informatics and scientific computing. It demonstrates real-world application of:

- Spatiotemporal data engineering
- Geospatial weighted interpolation (Inverse Distance Weighting)
- Automated environmental monitoring pipelines
- Synthetic agent-based simulation for exposure assessment

---

## Business Question

**"Which neighborhoods in Athens & Piraeus experience the worst air quality, and what is the estimated pollution exposure of workers traveling through these areas daily?"**

---

## Architecture

```
[OpenAQ API] ──────────────────────┐
[Open-Meteo API] ──────────────────┤──► [Ingestion] ──► [DuckDB] ──► [Transforms] ──► [Dashboard]
[data.gov.gr GIS] ─────────────────┘     Python          Star         AQI + IDW        Streamlit
                                         requests         Schema       Exposure          Plotly
                                                                       Scoring           Folium

[Driver Simulation] ──────────────────► [Exposure Scoring] ──► [Alerting System]
 100 Synthetic Agents                    IDW Interpolation       Email Reports
```

---

## Scientific Methods

### Inverse Distance Weighting (IDW)
When a driver is located more than 5km from any monitoring station, pollution exposure is estimated using IDW interpolation:

```
weight_i = 1 / distance_i
exposure = Σ(value_i × weight_i) / Σ(weight_i)
```

This method is standard in environmental science for spatial interpolation of air quality measurements.

### Haversine Distance
All spatial distances are computed using the Haversine formula, which accounts for the curvature of the Earth.

### EU Air Quality Index (AQI)
Measurements are classified using official **European Environment Agency (EEA)** thresholds for PM2.5, PM10, NO2, O3, and CO.

---

## Data Sources

| Source | Data | Update Frequency | API Key |
|--------|------|-----------------|---------|
| [OpenAQ](https://api.openaq.org) | PM2.5, PM10, NO2, O3, CO | Hourly | Required (free) |
| [Open-Meteo](https://open-meteo.com) | Temperature, humidity, wind, precipitation | Hourly | No |
| [data.gov.gr](https://data.gov.gr) | Piraeus health facilities (GIS) | Static | No |

---

## Project Structure

```
athens-air-health-pipeline/
├── ingestion/
│   ├── openaq_ingestor.py      # OpenAQ API client
│   ├── weather_ingestor.py     # Open-Meteo API client
│   ├── drivers.py              # Synthetic driver simulation
│   └── alerting.py             # Email alerting system
├── storage/
│   └── database.py             # DuckDB schema & write functions
├── transform/
│   ├── transforms.py           # EU AQI classification
│   └── exposure_scoring.py     # IDW exposure scoring
├── orchestration/
│   └── pipeline.py             # Prefect flow (DAG)
├── dashboard/
│   └── app.py                  # Streamlit dashboard
├── data/                       # Local data (gitignored)
├── .env                        # API keys (gitignored)
├── .gitignore
└── requirements.txt
```

---

## Tech Stack

- **Python** — pandas, numpy, requests, duckdb
- **DuckDB** — analytical database with star schema
- **Prefect** — pipeline orchestration & scheduling
- **Streamlit** — interactive dashboard
- **Plotly** — data visualization
- **Folium** — interactive geospatial maps

---

## Quick Start

### 1. Clone & Install
```bash
git clone https://github.com/AlexandrosK95/athens-air-health-pipeline.git
cd athens-air-health-pipeline
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 2. Set up API Key
Create a `.env` file:
```
OPENAQ_API_KEY=your_api_key_here
EMAIL_SENDER=your_email
EMAIL_PASSWORD=your_password
EMAIL_RECEIVER=your_email
```
Get a free API key at: https://explore.openaq.org/register

### 3. Run Pipeline
```bash
python orchestration/pipeline.py
```

### 4. Launch Dashboard
```bash
streamlit run dashboard/app.py
```

---

## Dashboard Features

- **KPI Cards** — Active stations, good air quality %, hazardous readings, avg temperature
- **AQI Distribution Chart** — Bar chart with EU color coding
- **Interactive Map** — Stations color-coded by AQI category
- **Weather Charts** — Temperature & humidity for Athens & Piraeus (48h)

---

## AQI Classification (EU EEA Thresholds)

| Category | PM2.5 | PM10 | NO2 |
|----------|-------|------|-----|
| 🟢 Good | ≤10 | ≤20 | ≤40 |
| 🟡 Moderate | ≤20 | ≤40 | ≤90 |
| 🟠 Poor | ≤25 | ≤50 | ≤120 |
| 🔴 Very Poor | ≤50 | ≤100 | ≤230 |
| 🟣 Hazardous | >50 | >100 | >230 |

---

## Roadmap

- [x] Real-time AQ ingestion (OpenAQ API)
- [x] Weather data integration (Open-Meteo API)
- [x] EU AQI classification
- [x] Driver route simulation (100 synthetic agents)
- [x] Pollution exposure scoring (IDW interpolation)
- [x] Automated email alerting system
- [ ] Parallel processing optimization
- [ ] Predictive modeling (ML forecasting)
- [ ] Web API layer (FastAPI)

---

## Author

**Alexandros K.**
MSc Artificial Intelligence & Data Science
Interested in environmental informatics, spatiotemporal data engineering, and scientific computing applications.
[GitHub](https://github.com/AlexandrosK95)
