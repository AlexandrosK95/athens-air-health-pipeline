import pandas as pd
import requests
from datetime import datetime, timedelta
import logging

logging.basicConfig(level = logging.INFO)
logger = logging.getLogger(__name__)

# Βασική διεύθυνση του Open-Meteo API (δωρεάν, χωρίς API key)
BASE_URL = "https://api.open-meteo.com/v1/forecast"

# Τοποθεσίες για τις οποίες τραβάμε καιρικά δεδομένα
LOCATIONS = {
    "Athens" : {"lat" : 37.9838, "lon" : 23.7275}, 
    "Peiraeus" : {"lat" : 37.9467, "lon" : 23.6463}
}
# Μετεωρολογικές μεταβλητές που μας ενδιαφέρουν
HOURLY_VARS = [
    "temperature_2m",
    "relative_humidity_2m",
    "wind_speed_10m",
    "precipitation"
]

def fetch_weather(location_name, days_back=1):
    if location_name not in LOCATIONS:
        logger.error(f"Unknown location: {location_name}")
        return pd.DataFrame()
    
    loc = LOCATIONS[location_name]
    today = datetime.utcnow().date()

    # Υπολογίζουμε την ημερομηνία έναρξης αφαιρώντας τις μέρες
    start_date = (datetime.utcnow() - timedelta(days=days_back)).date()

    params = {
        "latitude" : loc["lat"],
        "longitude" : loc["lon"],
        "hourly": ",".join(HOURLY_VARS),
        "start_date" : start_date.isoformat(),
        "end_date" : today.isoformat(),
        "timezone" : "Europe/Athens"
    }
    try:
      response = requests.get(BASE_URL, params = params, timeout = 30)
      response.raise_for_status()
    except requests.exceptions.Timeout:
        logger.warning(f"Timeout for station {location_name} - Skipping.")
        return pd.DataFrame()
    except requests.exceptions.HTTPError as e:
        logger.warning(f"HTTP Error for station {location_name}: {e} - Skipping.")
        return pd.DataFrame()
    except requests.exceptions.ConnectionError:
        logger.warning(f"No Internet Connection for station {location_name} - Skipping.")
        return pd.DataFrame()
    
    try:
      data = response.json()
       # Το Open-Meteo επιστρέφει τα δεδομένα στο key "hourly"
      df = pd.DataFrame(data["hourly"])
      # Μετονομάζουμε "time" σε "timestamp" για συνέπεια με το υπόλοιπο project
      df.rename(columns = {"time" : "timestamp"}, inplace = True)
      df["location"] = location_name
      df["latitude"] = loc["lat"]
      df["longitude"] = loc["lon"]
      return df
    
    except (KeyError,ValueError) as e:
         # KeyError: αν λείπει το "hourly" key
         # ValueError: αν τα δεδομένα έχουν απροσδόκητη μορφή
         logger.warning(f"Error parsing weather data for {location_name}: {e}")
         return pd.DataFrame()
    
def run_weather_ingestion(days_back=1):
    """
    Τραβάει καιρικά δεδομένα για όλες τις τοποθεσίες
    και τα ενώνει σε ένα DataFrame.
    """
    all_weather = []

    for location_name in LOCATIONS:
        print(f"Fetching weather for {location_name}...")
        df = fetch_weather(location_name, days_back = days_back)
        # Προσθέτουμε μόνο αν υπάρχουν δεδομένα
        if not df.empty:
          all_weather.append(df)
    
    # Αν καμία τοποθεσία δεν επέστρεψε δεδομένα
    if not all_weather:
        logger.error("No weather data fetched")
        return pd.DataFrame()
    
    # Ενώνουμε Αθήνα και Πειραιά σε ένα DataFrame
    combined = pd.concat(all_weather, ignore_index = True)
    logger.info(f"Weather ingestion complete: {len(combined)} records fetched.")
    return combined


if __name__ == "__main__":
    df = run_weather_ingestion(days_back=1)
    print(df)