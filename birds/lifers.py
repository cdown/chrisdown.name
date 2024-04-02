#!/usr/bin/env python

import csv
import json
import sys
from datetime import datetime, timezone

def to_utc(date_string):
    dt = datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S.%f %z")
    return dt.astimezone(timezone.utc).replace(tzinfo=None).strftime("%Y-%m-%d %H:%M")


def process_csv(file_path):
    first_sightings = {}

    with open(file_path, mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            if row["common_name"] not in first_sightings:
                first_sightings[row["common_name"]] = [
                    to_utc(row["date"]),
                    row["common_name"],
                    row["scientific_name"],
                    float(row["latitude"]),
                    float(row["longitude"]),
                ]

    sightings_list = list(first_sightings.values())

    return json.dumps(sightings_list)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Missing CSV")
        sys.exit(1)

    file_path = sys.argv[1]
    js_array = process_csv(file_path)
    print(js_array)
