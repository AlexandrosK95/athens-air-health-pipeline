import pandas as pd
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os 
import logging

logging.basicConfig(level = logging.INFO)
logger = logging.getLogger(__name__)

# Φορτώνουμε το API key από το .env αρχείο
load_dotenv()
API_KEY = os.getenv("OPENAQ_API_KEY")

# Βασική διεύθυνση του OpenAQ API
BASE_URL = "https://api.openaq.org/v3"

# Συντεταγμένες κέντρου Αθήνας
ATHENS_COORDS = {
    "lat" : 37.97,
    "lon" : 23.72
}

# Ρύποι που μας ενδιαφέρουν
POLLUTANTS = ["pm25", "pm10", "no2", "o3", "co"]

def fetch_stations():
    """
    Τραβάει όλους τους σταθμούς μέτρησης
    σε ακτίνα 20km από το κέντρο της Αθήνας.
    """
    url = f"{BASE_URL}/locations"
    params = {
        "coordinates": f"{ATHENS_COORDS['lat']},{ATHENS_COORDS['lon']}",
        "radius" : 20000,
        "limit" : 100
    }

    try:
      response = requests.get(url, params = params, headers = {"X-API-KEY" : API_KEY}, timeout = 30)
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
     # Αφαιρούμε σταθμούς με ίδιες συντεταγμένες
    df = df.drop_duplicates(subset=["latitude","longitude"])
    return df

def fetch_measurements(station_id):
    """
    Τραβάει τις τελευταίες μετρήσεις ρύπων
    για έναν συγκεκριμένο σταθμό.
    """
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
        # Κρατάμε μόνο τους ρύπους που μας ενδιαφέρουν
        if pollutant not in POLLUTANTS:
            continue
        
        # Παραλείπουμε sensors χωρίς πρόσφατες μετρήσεις
        if not sensor.get("latest"):
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
    logger.info(f"Fetched {len(measurements)} measurements for station {station_id}")
    return pd.DataFrame(measurements)

def run_ingestion():
   """
    Κεντρική συνάρτηση ingestion — τραβάει όλους
    τους σταθμούς και τις μετρήσεις τους.
    """
   logger.info("Fetching stations...")
   stations_df = fetch_stations()
   
   # Αν δεν βρέθηκαν σταθμοί, δεν συνεχίζουμε
   if stations_df.empty:
       logger.error("No fetcing stations - aborting ingestion.")
       return pd.DataFrame()
   
   all_measurements = []

   for station_id in stations_df["station_id"]:
       df = fetch_measurements(station_id)
       if not df.empty:
           all_measurements.append(df)

   # Αν κανένας σταθμός δεν επέστρεψε μετρήσεις
   if not all_measurements:
       logger.error("No measurements fetched")
       return pd.DataFrame()
   
   # Ενώνουμε όλες τις μετρήσεις σε ένα DataFrame
   combined = pd.concat(all_measurements, ignore_index = True)

   # Προσθέτουμε metadata σταθμού σε κάθε μέτρηση
   combined = combined.merge(
       stations_df[["station_id", "station_name", "latitude", "longitude"]], 
       on = "station_id", how = "left")

   logger.info(f"Ingestion complete: {len(combined)} records fetched.")
   return combined

if __name__ == "__main__": 
    df = run_ingestion()
    print(df)
