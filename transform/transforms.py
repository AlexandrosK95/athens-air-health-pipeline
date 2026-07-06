import sys
sys.path.append(".")

import pandas as pd
import duckdb
from storage.database import get_connection
import logging

logging.basicConfig(level = logging.INFO)
logger = logging.getLogger(__name__)

EU_THRESHOLDS = {
    "pm25"  : {"good" : 10, "moderate" : 20, "poor" : 25, "very poor" : 50},
    "pm10"  : {"good" : 20, "moderate" : 40, "poor" : 50, "very poor" : 100},
    "no2"  : {"good" : 40, "moderate" : 90, "poor" : 120, "very poor" : 230},
    "o3"  : {"good" : 60, "moderate" : 100, "poor" : 130, "very poor" : 240},
    "co"  : {"good" : 4, "moderate" : 7, "poor" : 10, "very poor" : 30},
}

def classify_aqi(pollutant, value):
    if pollutant not in EU_THRESHOLDS:
        return "unknown"
    
    t = EU_THRESHOLDS[pollutant]
    if value <= t["good"]:
        return "good"
    elif value <= t["moderate"]:
        return "moderate"
    elif value <= t["poor"]:
        return "poor"
    elif value <= t["very poor"]:
        return "very poor"
    else:
        return "hazardous"

def compute_aqi_classifications():
    con = get_connection()

    df = con.execute("""
            SELECT
                faq.station_id,
                ds.station_name,
                ds.latitude,
                ds.longitude,
                faq.unit,
                faq.timestamp,
                faq.pollutant,
                faq.value
            FROM fact_air_quality faq
            JOIN dim_stations ds ON faq.station_id=ds.station_id
            """).df()
    
    con.close()

    if df.empty:
        logging.warning(f"No AQ data found in database")
        return df
    
    df["aqi_class"] = df.apply(
        lambda row: classify_aqi(row["pollutant"], row["value"]), axis = 1
    )

    logger.info(f"Classified {len(df)} AQ readings")
    return df

def save_aqi_classifications(df):
    con = get_connection()

    con.execute("CREATE OR REPLACE TABLE mart_aqi_classifications AS SELECT * FROM df")

    logger.info(f"Saved {len(df)} classified records to mart_aqi_classifications")
    con.close()

if __name__  == "__main__":
    import sys
    sys.path.append(".")
    
    df = compute_aqi_classifications()
    print(df)
    print("\nΚατανομή Κατηγοριών:")
    print(df["aqi_class"].value_counts())
    save_aqi_classifications(df)
    print("\nΑποθηκεύτηκε στη βάση!:")