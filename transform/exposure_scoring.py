import sys
sys.path.append(".")
import pandas as pd
import numpy as np
from storage.database import get_connection
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DISTANCE_THRESHOLD_KM  = 5.0

def haversine_distance(lat1,lat2,lon1,lon2):
    lat1, lat2, lon1, lon2 = map(np.radians, [lat1, lat2, lon1, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1
    R = 6371

    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))

    return R * c

def compute_driver_exposure():
    con = get_connection()
    locations_df = con.execute("SELECT * FROM fact_driver_locations").df()

    aq_df = con.execute("""
         SELECT 
                ds.station_id,
                ds.latitude,
                ds.longitude,
                faq.pollutant,
                faq.value
        FROM fact_air_quality faq
        JOIN dim_stations ds ON ds.station_id = faq.station_id""").df()
    
    con.close()

    if locations_df.empty or aq_df.empty:
        logger.warning("no data found for exposure scoring")
        return pd.DataFramne()
    
    results = []
    for _, location in locations_df.iterrows():
        aq_df["distance_km"] = aq_df.apply (
            lambda row: haversine_distance (
                location["latitude"], location["longitude"],
                row["latitude"], row['longitude']
            ), axis = 1
        )
        
        nearby = aq_df[aq_df["distance_km"]<=DISTANCE_THRESHOLD_KM]

        for pollutant in aq_df["pollutant"].unique():
            if not nearby.empty:
                pollutant_data = nearby[nearby["pollutant"]==pollutant]
                if pollutant_data.empty:
                    continue
                exposure_value = pollutant_data["value"].mean()
                method="nearby"
            else:
                pollutant_data = aq_df[aq_df["pollutant"]==pollutant].copy()
                if pollutant_data.empty:
                  continue
                pollutant_data["weight"] = 1/pollutant_data["distance_km"]
                exposure_value = np.average(
                   pollutant_data["value"],
                   weights = pollutant_data["weight"]
                ) 
                method = "weight"

            results.append( {
                "drvier_id" : location["driver_id"],
                "stop_num" : location["stop_num"],
                "latitude" : location["latitude"],
                "longitude" : location["longitude"],
                "pollutant" : pollutant,
                "timestamp" : location["timestamp"],
                "exposure_value" : round(exposure_value,2),
                "method" : method
            })
    df = pd.DataFrame(results)
    logger.info(f"computed exposure for {len(df)} driver-location-pollutant combinations.")
    return df


def save_exposure_scores(df):
    con = get_connection()
    con.execute("CREATE OR REPLACE TABLE mart_driver_exposure AS SELECT * FROM df")
    logger.info(f"Saved {len(df)} exposure records to mart_driver_exposure.")
    con.close()

if __name__== "__main__":
    df = compute_driver_exposure()

    if not df.empty:
        print(f"\nΣυνολικές εγγραφές: {len(df)}")
        print(f"\nΜέθοδοι υπολογισμού:")
        print(df["method"].value_counts())
        print(f"\nΜέσο exposure ανά ρύπο:")
        print(df.groupby("pollutant")["exposure_value"].mean().round(2))

        save_exposure_scores(df)
        print("\Αποθηκεύτηκε στη βάση!")