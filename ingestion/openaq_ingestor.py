import pandas as pd
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os 
import logging

logging.basicConfig(level = logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
API_KEY = os.getenv("OPENAQ_API_KEY")

#API_KEY = "9045034cfc86693653c1a00788fef719a732c3b944f6d9cbcd12ee1925bf197e"

BASE_URL = "https://api.openaq.org/v3"

ATHENS_COORDS = {
    "lat" : 37.97,
    "lon" : 23.72
}

POLLUTANTS = ["pm25", "pm10", "no2", "o3", "co"]

def fetch_stations():
    url = f"{BASE_URL}/locations"
    params = {
        "coordinates": f"{ATHENS_COORDS['lat']},{ATHENS_COORDS['lon']}",
        "radius" : 20000,
        "limit" : 100
    }

    try:
      response = requests.get(url, headers = {"X-API-KEY" : API_KEY}, timeout = 30)
      response.raise_for_status()
    except requests.exceptions.Timeout:
        logger.warning(f"Timeout fetching stations - aborting.")
        return pd.DataFrame()
    except requests.exceptions.HTTPError as e:
        logger.warning(f"HTTP Error fetching stations: {e} - aborting.")
        return pd.DataFrame()
    except requests.exceptions.ConnectionError:
        logger.warning(f"No Internet Connection fetching stations - aborting.")
        return pd.DataFrame()

    data = response.json()
    stations = []

    for location in data.get("results", []):
        try: 
          stations.append( {
            "station_id" : location["id"],
            "station_name" : location.get("name", "Unknown"),
            "latitude" : location["coordinates"]["latitude"],
            "longitude" : location["coordinates"]["longitude"],
        })
        except KeyError as e:
            logger.warning(f"Missing field {e} in station data - Skipping.")
            continue

    df = pd.DataFrame(stations)
    df = df.drop_duplicates(subset=["latitude","longitude"])
    return df
#if __name__ == "__main__":
    #headers = {"X-API-KEY" : API_KEY}
    #url = f"{BASE_URL}/locations"
    #params = {
        #"coordinates": f"{ATHENS_COORDS['lat']},{ATHENS_COORDS['lon']}",
        #"radius": 20000,
        #"limit": 100
    #}


    #response = requests.get(url, params=params, headers=headers, timeout=30)
    #print("Status c
    # ode:", response.status_code)
    #print("Response:", response.text[:500])

def fetch_measurements(station_id, hours_back = 24):
    url = f"{BASE_URL}/locations/{station_id}/sensors"
    headers = {"X-API-KEY" : API_KEY}

    try:
      response = requests.get(url, headers = headers, timeout = 30)
      response.raise_for_status()
    except requests.exceptions.Timeout:
        logger.warning(f"Timeout for station {station_id} - Skipping.")
        return pd.DataFrame()
    except requests.exceptions.HTTPError as e:
        logger.warning(f"HTTP Error for station {station_id}: {e} - Skipping.")
        return pd.DataFrame()
    except requests.exceptions.ConnectionError:
        logger.warning(f"No Internet Connection for station {station_id} - Skipping.")
        return pd.DataFrame()
    
    data = response.json()
    measurements = []

    for sensor in data.get("results", []):
        pollutant = sensor["parameter"]["name"]
        if pollutant not in POLLUTANTS:
            continue
        try:
          measurements.append({
            "station_id" : station_id,
            "pollutant" : pollutant,
            "value" : sensor["latest"]["value"],
            "unit" : sensor["parameter"]["units"],
            "timestamp" : sensor["latest"]["datetime"]["utc"],
            "fetched_at" : datetime.utcnow().isoformat(),
        })
        except KeyError as e:
            logger.warning(f"Missing field {e} for station {station_id} - Skipping sensor..")
            continue

    return pd.DataFrame(measurements)

def run_ingestion():
   print("Fetching stations...")
   stations_df = fetch_stations()
   
   if stations_df.empty:
       logger.error("No fetcing stations - aborting ingerstion.")
       return pd.DataFrame()
   
   all_measaurements = []

   for station_id in stations_df["station_id"]:
       df = fetch_measurements(station_id)
       if not df.empty:
           all_measaurements.append(df)
    
   if not all_measaurements:
       logger.error("No measurements fetched")
       return pd.DataFrame()
   
   combined = pd.concat(all_measaurements, ignore_index = True)
   combined = combined.merge(
       stations_df[["station_id", "station_name", "latitude", "longitude"]], 
       on = "station_id", how = "left")

   print(f"\nIngestion completed: {len(combined)} records fetched")
   return combined

if __name__ == "__main__":
    #df_stations = fetch_stations()
    df = run_ingestion()
    print(df)
    #print("Stations:")
    #print(df_stations)
    #print ("\n--- Measurements for first station ---")
    #first_station_id= df_stations["station_id"].iloc[0]
    #df_measurements = fetch_measurements(first_station_id)
    #print(df_measurements)
