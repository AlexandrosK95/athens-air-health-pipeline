import sys
sys.path.append(".")

import streamlit as st
import plotly.express as px
import folium
from streamlit_folium import st_folium
from storage.database import get_connection

# Ρύθμιση σελίδας — πρέπει να είναι η πρώτη Streamlit εντολή
st.set_page_config(
    page_title = "Athens Air Quality & Health Pipeline",
    page_icon = "🌍",
    layout = "wide"
)

st.title("🌍 Athens Air Quality & Urban Health Dashboard")
st.markdown("Real time air quality monitoring across Athens & Piraeus")

# Χρώματα ανά κατηγορία AQI — χρησιμοποιείται σε γράφημα και χάρτη
color_map = {
    "good" : "#2ecc71",
    "moderate" : "#f1c40f",
    "poor" : "#e67e22",
    "very_poor" : "#e74c3c",
    "hazardous" : "#8e44ad"
}

# Σειρά σοβαρότητας για εύρεση χειρότερης κατηγορίας ανά σταθμό
SEVERITY = ["good", "moderate", "poor", "very_poor", "hazardous"]

@st.cache_data(ttl = 3600)
def load_data():
    """
    Φορτώνει δεδομένα από τη βάση.
    Cache για 1 ώρα ώστε να μην ξαναδιαβάζει τη βάση
    σε κάθε αλληλεπίδραση του χρήστη.
    """
    con = get_connection()
    aqi_df = con.execute("SELECT * FROM mart_aqi_classifications").df()
    weather_df = con.execute("SELECT * FROM fact_weather ORDER BY timestamp DESC LIMIT 96").df()
    stations_df = con.execute("SELECT * FROM dim_stations").df()
    return aqi_df, weather_df, stations_df

aqi_df, weather_df, stations_df = load_data()

# ── KPI Cards ─────────────────────────────────────────────────────────────────

col1, col2, col3, col4 = st.columns(4)

with col1:
     # Συνολικός αριθμός σταθμών στη βάση
    st.metric("Active Stations", len(stations_df))

with col2:
    # Ποσοστό μετρήσεων με καλή ποιότητα αέρα
    good_pct = (aqi_df["aqi_class"] == "good").mean() * 100
    st.metric("Good Air Quality", f"{good_pct:.0f}%")

with col3:
     # Αριθμός επικίνδυνων μετρήσεων
    hazardous_count = (aqi_df["aqi_class"] == "hazardous").sum()
    st.metric("Hazardous Readings", hazardous_count)

with col4:
     # Μέση θερμοκρασία από τα καιρικά δεδομένα
    avg_temp = (weather_df["temperature_2m"]).mean()
    st.metric("Avg Temperature", f"{avg_temp:.1f}°C")

# ── Bar Chart: Κατανομή AQI ───────────────────────────────────────────────────

st.subheader("Air Quality Distribution")

# Μετράμε πόσες φορές εμφανίζεται κάθε κατηγορία
aqi_counts =  (aqi_df["aqi_class"]).value_counts().reset_index()
aqi_counts.columns = ["aqi_class", "count"]

fix = px.bar(
    aqi_counts, 
    x = "aqi_class",
    y = "count",
    # Χρωματίζουμε κάθε μπάρα ανάλογα με την κατηγορία
    color = "aqi_class",
    color_discrete_map = color_map,
    title = "Readings by AQI category"
)

st.plotly_chart(fix, use_container_width = True)

# ── Χάρτης σταθμών ────────────────────────────────────────────────────────────

st.subheader("Station Map")

def get_worst_class(classes):
    return max(classes, key = lambda c: SEVERITY.index(c))

# Παίρνουμε μία γραμμή ανά σταθμό με τη χειρότερη κατηγορία του
station_latest = aqi_df.groupby("station_id").agg(
    station_name = ("station_name", "first"),
    latitude = ("latitude", "first"),
    longitude = ("longitude", "first"),
    worst_class = ("aqi_class", get_worst_class)
).reset_index()

# Δημιουργούμε χάρτη κεντραρισμένο στην Αθήνα
m = folium.Map(location =[37.97, 23.72], zoom_start = 11 )

for _,row in station_latest.iterrows():
   color = color_map.get(row["worst_class"], "gray")
   # Προσθέτουμε έναν κύκλο για κάθε σταθμό
   folium.CircleMarker(
       location = [row["latitude"], row["longitude"]],
       popup = f"{row['station_name']} : {row['worst_class']}",
       color = color,
       radious = 8,
       fill = True,
       fillColor = color,
       fillOpacity = 0.7
   ).add_to(m)

st_folium(m, width = 1200, height = 500)

# ── Γραφήματα καιρού ──────────────────────────────────────────────────────────

st.subheader("Weather - last 48 hours")

col1, col2 = st.columns(2)

with col1:
    # Γράφημα θερμοκρασίας για Αθήνα και Πειραιά
    fig_temp = px.line(
        weather_df,
        x = "timestamp",
        y = "temperature_2m",
        color = "location",
        title = "Temperature (°C)"
    )
    st.plotly_chart(fig_temp, use_container_width = True)

with col2:
    # Γράφημα σχετικής υγρασίας για Αθήνα και Πειραιά
    fig_humidity = px.line(
        weather_df,
        x = "timestamp",
        y = "relative_humidity_2m",
        color = "location",
        title = "Relative Humidity (%)"
    )
    st.plotly_chart(fig_humidity, use_container_width = True)
