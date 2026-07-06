import pandas as pd
import requests
from datetime import datetime, timedelta
import logging

logging.basicConfig(level = logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "https://api.open-meteo.com/v1/forecast"

LOCATIONS = {
    "Athens" : {"lat" : 37.9838, "lon" : 23.7275}, 
    "Peiraeus" : {"lat" : 37.9467, "lon" : 23.6463}
}

HOURLY_VARS = {
    "temperature_2m",
    "relative_humidity_2m",
    "wind_speed_10m",
    "precipitation"
}

def fetch_weather(location_name, days_back=1):
    if location_name not in LOCATIONS:
        logger.error(f"Unknown location: {location_name}")
        return pd.DataFrame()
    
    loc = LOCATIONS[location_name]
    today = datetime.utcnow().date()
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
      df = pd.DataFrame(data["hourly"])
      df.rename(columns = {"time" : "timestamp"}, inplace = True)
      df["location"] = location_name
      df["latitude"] = loc["lat"]
      df["longitude"] = loc["lon"]
      return df
    
    except (KeyError,ValueError) as e:
         logger.warning(f"Error parsing weather data for {location_name}: {e}")
         return pd.DataFrame()
    
def run_weather_ingestion(days_back=1):
    all_weather = []

    for location_name in LOCATIONS:
        print(f"Fetching weather for {location_name}...")
        df = fetch_weather(location_name, days_back = days_back)
        all_weather.append(df)

        combined = pd.concat(all_weather, ignore_index = True)
        print(f"The weather ingestion complete: {len(combined)} records fetched.")
    return combined

#if __name__ == "__main__":
    #loc = LOCATIONS["Athens"]
    #today = datetime.utcnow().date()
    #start_date = (datetime.utcnow() - timedelta(days=1)).date()

    #params = {
        #"latitude" : loc["lat"],
        #"longitude" : loc["lon"],
        #"hourly": ",".join(HOURLY_VARS),
        #"start_date" : start_date.isoformat(),
        #"end_date" : today.isoformat(),
        #"timezone" : "Europe/Athens"
    #}
  
    #response = requests.get(BASE_URL, params=params, timeout=30)
    #print("Status code:", response.status_code)
    #print("Response:", response.text[:500])

if __name__ == "__main__":
    #df_stations = fetch_stations()
    df = run_weather_ingestion(days_back=1)
    print(df)