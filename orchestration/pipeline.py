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

@task(name = "Initialize Database")
def task_init_db():
    logger = get_run_logger()
    logger.info("Initializing Database")

    initialize_schema()

@task(name = "Ingest Air Quality", retries = 3, retry_delay_seconds = 60)
def task_ingest_aq():
    logger = get_run_logger()
    logger.info("Fetching air quality data...")

    df = run_ingestion()

    stations_df = df[["station_id","station_name","latitude","longitude"]].drop_duplicates()
    measurements_df = df[["station_id", "pollutant", "value", "unit", "timestamp", "fetched_at"]]

    upsert_stations(stations_df)
    insert_measurements(measurements_df)

    logger.info(f"AQ ingestion complete: {len(measurements_df)}, records")
    return len(measurements_df)

@task(name = "Ingest weather", retries = 3, retry_delay_seconds = 60)
def task_ingest_weather():
    logger = get_run_logger()
    logger.info("Fetching weather data...")

    df = run_weather_ingestion()
    insert_weather(df)

    logger.info(f"Weather ingestion complete, {len(df)} records.")
    return len(df)


@task(name = "Run Transforms")
def task_transforms():
    logger = get_run_logger()
    logger.info("Running Transforms...")

    df = compute_aqi_classifications()
    save_aqi_classifications(df)

    logger.info(f"Transforms complete, {len(df)} records classified.")
    return len(df)


flow(name = "Athens Air & Health Pipeline")
def athens_pipeline():
    task_init_db()
    task_ingest_aq()
    task_ingest_weather()
    task_transforms()


if __name__ == "__main__":
    athens_pipeline()
