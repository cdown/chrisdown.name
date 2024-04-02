#!/usr/bin/env python

import csv
import json
import time
import sys
from datetime import datetime, timezone
from geopy.geocoders import Nominatim

geolocator = Nominatim(user_agent="lifers")


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def to_utc(date_string):
    dt = datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S.%f %z")
    return dt.astimezone(timezone.utc).replace(tzinfo=None).strftime("%Y-%m-%d %H:%M")


def get_country(latitude, longitude, cache):
    tolerance_deg = 0.1  # 11.1km

    lat_rounded = round(float(latitude), 1)
    long_rounded = round(float(longitude), 1)

    eprint("Checking ({}, {})".format(lat_rounded, long_rounded))

    for (cached_lat, cached_long), country in cache.items():
        if (
            abs(lat_rounded - cached_lat) <= tolerance_deg
            and abs(long_rounded - cached_long) <= tolerance_deg
        ):
            eprint(f"Found in cache: {country}")
            return country

    eprint("Not in cache, doing lookup")

    time.sleep(1)  # No heavy uses (an absolute maximum of 1 request per second).
    location = geolocator.reverse(
        (latitude, longitude), exactly_one=True, language="en"
    )
    address = location.raw["address"]
    country = address.get("country", "Unknown")

    cache[(lat_rounded, long_rounded)] = country
    eprint(f"Got {country}")
    return country


def process_csv(file_path):
    first_sightings = {}
    cache = {}

    with open(file_path, mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            if row["common_name"] not in first_sightings:
                country_name = get_country(row["latitude"], row["longitude"], cache)
                first_sightings[row["common_name"]] = [
                    to_utc(row["date"]),
                    row["common_name"],
                    row["scientific_name"],
                    float(row["latitude"]),
                    float(row["longitude"]),
                    country_name,
                ]

    sightings_list = list(first_sightings.values())

    return json.dumps(sightings_list)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        eprint("Missing CSV")
        sys.exit(1)

    file_path = sys.argv[1]
    js_array = process_csv(file_path)
    print(js_array)
