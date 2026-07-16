import duckdb
import pandas as pd
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Path της τοπικής βάσης δεδομένων
DB_PATH = "data/athens-air-health.duckdb"

def get_connection():
    """
    Επιστρέφει σύνδεση με τη βάση DuckDB.
    Δημιουργεί τον φάκελο data/ αν δεν υπάρχει.
    """
    Path(DB_PATH).parent.mkdir(parents = True, exist_ok = True)
    return duckdb.connect(DB_PATH)

def initialize_schema():
    """
    Δημιουργεί τους πίνακες της βάσης αν δεν υπάρχουν.
    Ασφαλές να τρέχει πολλές φορές (idempotent).
    """
    con = get_connection()

    # Dimension table: μοναδικοί σταθμοί μέτρησης
    con.execute(""" 
                CREATE TABLE IF NOT EXISTS dim_stations (
                    station_id INTEGER PRIMARY KEY,
                    station_name VARCHAR,
                    latitude DOUBLE,
                    longitude DOUBLE,
                )
                """)
    
    # Fact table: ωριαίες μετρήσεις ρύπων ανά σταθμό
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
    
    # Fact table: ωριαία καιρικά δεδομένα ανά τοποθεσία
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
    """
    Εισάγει νέους σταθμούς στη βάση.
    Αγνοεί σταθμούς που υπάρχουν ήδη (INSERT OR IGNORE).
    """
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
    """
    Εισάγει μετρήσεις ρύπων στη βάση.
    Αποφεύγει διπλότυπα βάσει station_id + pollutant + timestamp.
    """
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
    """
    Εισάγει καιρικά δεδομένα στη βάση.
    Αποφεύγει διπλότυπα βάσει location + timestamp.
    """
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
                AND CAST(fw.timestamp AS TIMESTAMP) = CAST(df.timestamp AS TIMESTAMP) 
                )
                """)
    logger.info(f"Inserted {len(df)} weather records.")
    con.close()

def insert_drivers(df):
    con = get_connection()
    con.execute("CREATE OR REPLACE TABLE dim_drivers AS SELECT * FROM df")
    logger.info(f"Inserted {len(df)} drivers.")
    con.close()

def insert_driver_locations(df):
    con = get_connection()
    con.execute("CREATE OR REPLACE TABLE fact_driver_locations AS SELECT * FROM df")
    logger.info(f"Inserted {len(df)} driver locations records.")
    con.close()

if __name__ == "__main__":
    initialize_schema()
    print("Database initialized at:", DB_PATH)
