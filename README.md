# 🌍 Athens Air Quality & Urban Health Pipeline

> Automated ETL pipeline for real-time air quality monitoring across Athens & Piraeus, with driver exposure scoring and automated alerting.

---

## 📌 Business Question

**"Which neighborhoods in Athens & Piraeus experience the worst air quality, and how does it affect people who work and travel there daily?"**

---

## 🏗️ Architecture

[OpenAQ API] ──────────────────────┐
[Open-Meteo API] ──────────────────┤──► [Ingestion Layer] ──► [DuckDB] ──► [Transforms] ──► [Dashboard]
[data.gov.gr GIS] ─────────────────┘         Python              Star         AQI EU           Streamlit
requests            Schema      Thresholds         Plotly
Prefect            Folium

---

## 📊 Data Sources

| Source | Data | Update Frequency | API Key |
|--------|------|-----------------|---------|
| [OpenAQ](https://api.openaq.org) | PM2.5, PM10, NO2, O3, CO | Hourly | Required (free) |
| [Open-Meteo](https://open-meteo.com) | Temperature, humidity, wind, precipitation | Hourly | No |
| [data.gov.gr](https://data.gov.gr) | Piraeus health facilities (GIS) | Static | No |

---

## 🗂️ Project Structure

athens-air-health-pipeline/
├── ingestion/
│   ├── openaq_ingestor.py      # OpenAQ API client
│   └── weather_ingestor.py     # Open-Meteo API client
├── storage/
│   └── database.py             # DuckDB schema & write functions
├── transform/
│   └── transforms.py           # EU AQI classification
├── orchestration/
│   └── pipeline.py             # Prefect flow (DAG)
├── dashboard/
│   └── app.py                  # Streamlit dashboard
├── data/                       # Local data (gitignored)
├── .env                        # API keys (gitignored)
├── .gitignore
└── requirements.txt

---

## ⚙️ Tech Stack

- **Python** — pandas, requests, duckdb
- **DuckDB** — analytical database with star schema
- **Prefect** — pipeline orchestration & scheduling
- **Streamlit** — interactive dashboard
- **Plotly** — data visualization
- **Folium** — interactive maps

---

## 🚀 Quick Start

### 1. Clone & Install
```bash
git clone https://github.com/AlexandrosK95/athens-air-health-pipeline.git
cd athens-air-health-pipeline
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 2. Set up API Key
Δημιούργησε αρχείο `.env`:

OPENAQ_API_KEY=your_api_key_here

Αποκτήστε δωρεάν API key: https://explore.openaq.org/register

### 3. Run Pipeline
```bash
python orchestration/pipeline.py
```

### 4. Launch Dashboard
```bash
streamlit run dashboard/app.py
```

---

## 📈 Dashboard Features

- **KPI Cards** — Active stations, good air quality %, hazardous readings, avg temperature
- **AQI Distribution Chart** — Bar chart με EU color coding
- **Interactive Map** — Σταθμοί χρωματισμένοι ανά κατηγορία AQI
- **Weather Charts** — Θερμοκρασία & υγρασία για Αθήνα & Πειραιά (48h)

---

## 🔬 AQI Classification

Βάσει επίσημων ορίων της **European Environment Agency (EEA)**:

| Category | PM2.5 | PM10 | NO2 |
|----------|-------|------|-----|
| 🟢 Good | ≤10 | ≤20 | ≤40 |
| 🟡 Moderate | ≤20 | ≤40 | ≤90 |
| 🟠 Poor | ≤25 | ≤50 | ≤120 |
| 🔴 Very Poor | ≤50 | ≤100 | ≤230 |
| 🟣 Hazardous | >50 | >100 | >230 |

---

## 🔮 Roadmap

- [ ] Driver route simulation (100+ synthetic drivers)
- [ ] Pollution exposure scoring per driver
- [ ] Email alerting system for high-pollution zones
- [ ] Streamlit Cloud deployment

---

## 👤 Author

**Alexandros K.**  
MSc Artificial Intelligence & Data Science  
[GitHub](https://github.com/AlexandrosK95)