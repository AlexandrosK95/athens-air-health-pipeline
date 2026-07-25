import sys
sys.path.append(".")

from prefect import flow, task, get_run_logger
from ingestion.openaq_ingestor import run_ingestion
from ingestion.weather_ingestor import run_weather_ingestion
from storage.database import (
    initialize_schema,
    upsert_stations,
    insert_measurements,
    insert_weather
)
from transform.transforms import compute_aqi_classifications, save_aqi_classifications
from transform.exposure_scoring import save_exposure_scores, compute_driver_exposure
from ingestion.drivers import run_driver_simulation
from storage.database import insert_drivers, insert_driver_locations

@task(name = "Initialize Database")
def task_init_db():
    """Αρχικοποιεί τη βάση δεδομένων και δημιουργεί τους πίνακες."""
    logger = get_run_logger()
    logger.info("Initializing Database")

    initialize_schema()

@task(name = "Ingest Air Quality", retries = 3, retry_delay_seconds = 60)
def task_ingest_aq():
    """
    Τραβάει μετρήσεις ρύπων από το OpenAQ API.
    Επαναλαμβάνει έως 3 φορές αν αποτύχει (π.χ. προβλήματα δικτύου).
    """
    logger = get_run_logger()
    logger.info("Fetching air quality data...")

    df = run_ingestion()
    
     # Αν δεν υπάρχουν δεδομένα, σταματάμε
    if df.empty:
       logger.error("No AQ data fetched - skipping.")
       return 0
    
    # Χωρίζουμε σε σταθμούς και μετρήσεις
    stations_df = df[["station_id","station_name","latitude","longitude"]].drop_duplicates()
    measurements_df = df[["station_id", "pollutant", "value", "unit", "timestamp", "fetched_at"]]

    upsert_stations(stations_df)
    insert_measurements(measurements_df)

    logger.info(f"AQ ingestion complete: {len(measurements_df)}, records")
    return len(measurements_df)

@task(name = "Ingest weather", retries = 3, retry_delay_seconds = 60)
def task_ingest_weather():
    """
    Τραβάει ωριαία καιρικά δεδομένα από το Open-Meteo API.
    Επαναλαμβάνει έως 3 φορές αν αποτύχει.
    """
    logger = get_run_logger()
    logger.info("Fetching weather data...")

    df = run_weather_ingestion()

     # Αν δεν υπάρχουν δεδομένα, σταματάμε
    if df.empty:
       logger.error("No weather data fetched - skipping.")
       return 0
    
    insert_weather(df)

    logger.info(f"Weather ingestion complete, {len(df)} records.")
    return len(df)


@task(name = "Run Transforms")
def task_transforms():
    """
    Εκτελεί τους μετασχηματισμούς — AQI classification
    και αποθήκευση στο mart table.
    """
    logger = get_run_logger()
    logger.info("Running Transforms...")

    df = compute_aqi_classifications()
    save_aqi_classifications(df)

    logger.info(f"Transforms complete, {len(df)} records classified.")
    return len(df)

@task(name = "Simulate Drivers")
def task_simulate_drivers():
   logger = get_run_logger()
   logger.info("Running driver simulation...")

   drivers_df, locations_df = run_driver_simulation()
   insert_drivers(drivers_df)
   insert_driver_locations(locations_df)

   logger.info(f"Driver simulation complete: {len(drivers_df)} drivers, {len(locations_df)} locations.")
   return {"drivers": len(drivers_df), "locations": len(locations_df)}

@task(name = "Compute Exposure Scores")
def task_exposure_scores():
    logger = get_run_logger()
    logger.info("Computing driver exposure scores...")

    df = compute_driver_exposure()
    save_exposure_scores(df)

    logger.info(f"Exposure scoring complete, {len(df)} records.")
    return len(df)

@flow(name = "Athens Air and Health Pipeline")
def athens_pipeline():
    """
    Κεντρικό pipeline που ενορχηστρώνει όλα τα tasks:
    1. Αρχικοποίηση βάσης
    2. Ingestion αέρα και καιρού
    3. Transforms και αποθήκευση αποτελεσμάτων
    4. Simulation διαδρομών οδηγών
    """
    task_init_db()
    task_ingest_aq()
    task_ingest_weather()
    task_transforms()
    task_simulate_drivers()
    task_exposure_scores()

if __name__ == "__main__":
    athens_pipeline()
