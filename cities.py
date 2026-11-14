"""The only locations EstateMind accepts: Indian cities with 1 lakh or more people.

The list comes from the official Census of India 2011 table, converted by
scripts/build_city_list.py. Each state's cities are ordered largest first.
"""

import csv
from pathlib import Path

CITY_FILE = Path(__file__).parent / "data" / "indian_cities.csv"


def load_cities():
    cities = {}
    with CITY_FILE.open(encoding="utf-8") as file:
        for row in csv.DictReader(file):
            cities.setdefault(row["state"], []).append(row["city"])
    return dict(sorted(cities.items()))


INDIAN_CITIES = load_cities()


def is_supported(state, city):
    return city in INDIAN_CITIES.get(state, [])


def to_location(state, city):
    """The text the agents receive. Including the state separates cities with the same name."""
    return city if city == state else f"{city}, {state}"
