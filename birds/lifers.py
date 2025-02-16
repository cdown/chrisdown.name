#!/usr/bin/env python

import csv
import json
import time
import sys
import zipfile
from datetime import datetime, timezone
from io import TextIOWrapper
from geopy.geocoders import Nominatim

CACHE_FILE = "loc_cache.json"

geolocator = Nominatim(user_agent="lifers")


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def load_cache():
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        eprint(f"Problem loading file: {e}")
        return {"coordinates": {}, "countries": []}


def save_cache(cache):
    # Make determinstic so source control deltas are small
    cache["coordinates"] = dict(sorted(cache["coordinates"].items()))
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=4)


def round_coordinate_for_cache(coord):
    whole, fraction = coord.split(".")
    return f"{whole}.{fraction[:1]}"


def round_coordinate(coord):
    """
    Rounds a coordinate to 5 decimal places (~1.1 meter accuracy).
    This reduces the number of digits to shrink the size of the array in the
    document.
    """
    return round(coord, 5)


def get_country(lat, lng, cache):
    lat_rounded = round_coordinate_for_cache(lat)
    lng_rounded = round_coordinate_for_cache(lng)
    coord_key = f"{lat_rounded},{lng_rounded}"

    eprint(f"Checking ({lat_rounded}, {lng_rounded})")

    if coord_key in cache["coordinates"]:
        country_index = cache["coordinates"][coord_key]
        country = cache["countries"][country_index]
        eprint(f"Found in cache: {country}")
        return country

    eprint("Not in cache, doing lookup")

    time.sleep(1)  # No heavy uses (an absolute maximum of 1 request per second).
    location = geolocator.reverse((lat, lng), exactly_one=True, language="en")
    country = location.raw["address"]["country"]

    if country not in cache["countries"]:
        cache["countries"].append(country)
    country_index = cache["countries"].index(country)
    cache["coordinates"][coord_key] = country_index
    eprint(f"Got {country}")
    return country


def process_csv(file):
    first_sightings = {}
    cache = load_cache()
    reader = csv.DictReader(file)

    base_time = datetime(2017, 1, 1, 0, 0, tzinfo=timezone.utc)

    raw_sightings = []
    for row in reader:
        if row["commonName"] and row["commonName"] not in first_sightings:
            get_country(row["latitude"], row["longitude"], cache)
            lat = round_coordinate(float(row["latitude"]))
            lng = round_coordinate(float(row["longitude"]))
            dt = datetime.fromisoformat(row["date"])
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            minutes_since = int((dt - base_time).total_seconds() // 60)
            raw_sightings.append([
                minutes_since,
                row["commonName"],
                row["scientificName"],
                lat,
                lng
            ])
            first_sightings[row["commonName"]] = True

    save_cache(cache)
    sightings = list(reversed(raw_sightings))

    countries_json = json.dumps(cache["countries"])
    lat_long_map_json = json.dumps(cache["coordinates"])
    sightings_json = json.dumps(sightings)

    output_lines = [
        f"const countries = {countries_json};",
        f"const lat_long_map = {lat_long_map_json};",
        f"const sightings = {sightings_json};"
    ]
    return "\n".join(output_lines)


def main():
    if len(sys.argv) != 2:
        eprint("Missing zip file")
        sys.exit(1)

    zip_path = sys.argv[1]

    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            csv_files = [name for name in z.namelist() if name.endswith(".csv")]

            if len(csv_files) != 1:
                eprint("Zip file must contain exactly one CSV file")
                sys.exit(1)

            with z.open(csv_files[0]) as csv_file:
                file = TextIOWrapper(csv_file, encoding="utf-8")
                js_output = process_csv(file)
                print(js_output)

    except zipfile.BadZipFile:
        eprint("Invalid zip file")
        sys.exit(1)


if __name__ == "__main__":
    main()
