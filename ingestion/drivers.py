import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import logging
import sys
sys.path.append(".")
from storage.database import insert_drivers, insert_driver_locations

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ATHENS_BBOX = {
    "lat_min" : 37.90,
    "lat_max" : 38.10,
    "lon_min" : 23.60,
    "lon_max" : 23.85
}

SHIFTS = {
    "morning" : {"start" : 8, "end" : 16},
    "afternoon" : {"start" : 14, "end" : 22},
}

NUM_DRIVERS = 100

def generate_drivers():
    greek_names = [
        "Γιώργης", "Νίκος", "Κώστας", "Δημήτρης", "Παναγιώτης",
        "Βασίλης", "Χρήστος", "Γιάννης", "Αντώνης", "Σταύρος",
        "Μιχάλης", "Θανάσης", "Πέτρος", "Λευτέρης", "Σπύρος",
        "Μανώλης", "Τάκης", "Στέφανος", "Αλέξης", "Θεόδωρος"
    ]

    greek_surnames = [
        "Παπαδόπουλος", "Παπαδημητρίου", "Γεωργίου", "Νικολάου",
        "Κωνσταντίνου", "Παπανικολάου", "Αντωνίου", "Δημητρίου",
        "Χριστοδούλου", "Καραγιάννης", "Οικονόμου", "Αθανασίου",
        "Σταματίου", "Βασιλείου", "Κυριακίδης", "Παπαγεωργίου"
    ]

    drivers = []

    for i in range(NUM_DRIVERS):
      shift = "morning" if i < 50 else "afternoon"
      start_lat = random.uniform(ATHENS_BBOX["lat_max"],  ATHENS_BBOX["lat_min"])
      start_lon = random.uniform(ATHENS_BBOX["lon_max"], ATHENS_BBOX["lon_min"])

      drivers.append ({
        "driver_id" : i + 1,
        "name" : f"{random.choice(greek_names)} {random.choice(greek_surnames)}",
        "shift" : shift,
        "shift_start" : SHIFTS[shift]["start"],
        "shift_end" : SHIFTS[shift]["end"],
        "start_lat" : round(start_lat, 6),
        "start_lon" : round(start_lon, 6),
        "created_at" : datetime.utcnow().isoformat()
     })

    df = pd.DataFrame(drivers)
    logger.info(f"Generated {len(df)} drivers")
    return df


def simulate_driver_route(driver, num_stops=10):
       locations =[]
       current_lat = driver["start_lat"]
       current_lon= driver["start_lon"]

       now = datetime.utcnow().replace(hour = driver["shift_start"], minute=0, second=0)

       shift_duration = (driver["shift_end"] - driver["shift_start"])*60
       timer_per_stop = shift_duration//num_stops
       for stop in range(num_stops):
          
          current_lat += random.uniform(-0.01, 0.01)
          current_lon += random.uniform(-0.01, 0.01)

          current_lat = max(ATHENS_BBOX["lat_min"], min (ATHENS_BBOX["lat_max"], current_lat))
          current_lon = max(ATHENS_BBOX["lon_min"], min (ATHENS_BBOX["lon_max"], current_lon))
          
          arrival_time = now + timedelta(minutes=stop*timer_per_stop)
          
          #print(f"Stop {stop}: lat={current_lat}, lon={current_lon}")
          locations.append ({
             "driver_id" : driver["driver_id"],
             "stop_num" : stop + 1,
             "latitude" : round(current_lat, 6),
             "longitude" : round(current_lon, 6),
             "timestamp" : arrival_time.isoformat(),
             "recorded_at" : datetime.utcnow().isoformat()
          })
       return locations

def run_driver_simulation():
       drivers_df = generate_drivers()
       all_locations = []
       for _, driver in drivers_df.iterrows():
          locations = simulate_driver_route(driver)
          all_locations.extend(locations)

       locations_df = pd.DataFrame(all_locations)

       logger.info(f"Simulation complete: {len(drivers_df)} drivers, {len(locations_df)} locations records")
       return drivers_df, locations_df
    
if __name__ == "__main__" :
    drivers_df, locations_df = run_driver_simulation()
    print("\n--- Drivers ---")
    print(drivers_df.head())
    print("\n--- Locations ---")
    print(locations_df.head(10))

    insert_drivers(drivers_df)
    insert_driver_locations(locations_df)
    print("\Αποθηκεύτηκαν στη βάση!")