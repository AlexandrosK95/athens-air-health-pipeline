import duckdb
import pandas as ps
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = "data/athens-air-health.duckdb"

def get_connection():
    Path(DB_PATH).parent.mkdir(parents = True, exist_ok = True)
    return duckdb.connect(DB_PATH)

def initialize_schema():
    con = get_connection()

    con.execute(""" 
                CREATE TABLE IF NOT EXISTS dim_stations (
                    station_id INTEGER PRIMARY KEY,
                    station_name VARCHAR,
                    latitude DOUBLE,
                    longitude DOUBLE,
                )
                """)
    con.execute(""" 
                CREATE TABLE IF NOT EXISTS fact_air_quality (
                    station_id INTEGER,
                    pollutant VARCHAR,
                    value DOUBLE,
                    unit VARCHAR,
                    timestamp TIMESTAMP,
                    fetched_at TIMESTAMP
                )
                """)
    con.execute(""" 
                CREATE TABLE IF NOT EXISTS fact_weather (
                    location VARCHAR,
                    latitude DOUBLE,
                    longitude DOUBLE,
                    timestamp TIMESTAMP,
                    temperature_2m DOUBLE,
                    relative_humidity_2m DOUBLE,
                    wind_speed_10m DOUBLE,
                    precipitation DOUBLE
                )
                """)
    
    logger.info("Schema initialized successfully.")
    con.close()

def upsert_stations(df):
    con = get_connection()
    con.execute("""
                INSERT OR IGNORE INTO dim_stations
                (station_id, station_name,latitude,longitude)
                SELECT station_id, station_name,latitude,longitude
                FROM df
                """)
    logger.info(f"upserted {len(df)} stations.")
    con.close()

def insert_measurements(df):
    con = get_connection()
    con.execute("""
                INSERT INTO fact_air_quality
                (station_id, pollutant, value, unit, timestamp, fetched_at)
                SELECT station_id, pollutant, value, unit,
                      CAST(timestamp AS TIMESTAMP),
                      CAST(fetched_at AS TIMESTAMP)
                FROM df
                WHERE NOT EXISTS (
                   SELECT 1 FROM fact_air_quality faq
                   WHERE faq.station_id = df.station_id
                   AND faq.pollutant = df.pollutant
                   AND CAST(faq.timestamp as TIMESTAMP) = CAST(df.timestamp AS TIMESTAMP)
                )
                """)
    logger.info(f"Inserted {len(df)} air_quality records.")
    con.close()

def insert_weather(df):
    con = get_connection()
    con.execute("""
                INSERT INTO fact_weather
                (location, latitude, longitude, timestamp, temperature_2m, relative_humidity_2m, wind_speed_10m, precipitation)
                SELECT location, latitude, longitude,

                      CAST(timestamp AS TIMESTAMP),
                      temperature_2m, relative_humidity_2m, wind_speed_10m, precipitation
                FROM df
                WHERE NOT EXISTS (
                SELECT 1 FROM fact_weather fw
                WHERE fw.location = df.location
                AND CAST(fw.timestamp AS TIMESTAMP) = CAST(df.timestamp AS TIEMSTAMP) 
                )
                """)
    logger.info(f"Inserted {len(df)} weather records.")
    con.close()

if __name__ == "__main__":
    import sys
    sys.path.append(".")

    from ingestion.openaq_ingestor import run_ingestion
    from ingestion.weather_ingestor import run_weather_ingestion
    
    initialize_schema()

    aq_df = run_ingestion()
    print("AQ columns", aq_df.columns.tolist())
    weather_df = run_weather_ingestion()

    stations_df = aq_df[["station_id", "station_name", "latitude", "longitude"]].drop_duplicates()
    measurements_df = aq_df[["station_id", "pollutant", "value", "unit", "timestamp", "fetched_at"]]

    upsert_stations(stations_df)
    insert_measurements(measurements_df)
    insert_weather(weather_df)

    con = get_connection()
    print("\n---Stations---")
    print(con.execute("SELECT * FROM dim_stations").df())
    print("\n---Air Quality (first 5)---")
    print(con.execute("SELECT * FROM fact_air_quality LIMIT 5").df())
    print("\n---Weather (first 5)---")
    print(con.execute("SELECT * FROM fact_weather LIMIT 5").df())
    con.close()
    