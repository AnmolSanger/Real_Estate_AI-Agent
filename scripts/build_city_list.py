"""Build data/indian_cities.csv from the official Census of India 2011 table.

Source: "Urban Agglomerations/Cities having population 1 lakh and above",
Provisional Population Totals, Census of India 2011 (Office of the Registrar General).
The original censusindia.gov.in link is gone; an archived copy is at:
https://web.archive.org/web/20170101050957/http://www.censusindia.gov.in/2011-prov-results/paper2/data_files/India2/Table_3_PR_UA_Citiees_1Lakh_and_Above.pdf

Usage: python scripts/build_city_list.py path/to/downloaded.pdf
"""

import csv
import re
import sys
from pathlib import Path

import pdfplumber

OUTPUT = Path(__file__).parent.parent / "data" / "indian_cities.csv"

ROW = re.compile(r"^(\d{2}) (.+?) (\d{2}) (.+?) (UA|City|CT) ([\d,]+) ")

# State names as they are today.
STATE_NAMES = {
    "JAMMU & KASHMIR": "Jammu and Kashmir",
    "NCT OF DELHI": "Delhi",
    "ORISSA": "Odisha",
    "ANDAMAN & NICOBAR ISLANDS": "Andaman and Nicobar Islands",
}

# Telangana split from Andhra Pradesh in 2014. In this table its cities sit in
# Andhra Pradesh districts 01-10, and Hyderabad is listed with code 99.
TELANGANA_DISTRICTS = {f"{code:02d}" for code in range(1, 11)}

# Census labels and places renamed since 2011, mapped to the names people use now.
CITY_NAMES = {
    "GVMC": "Visakhapatnam",
    "BANGALORE": "Bengaluru",
    "Mysore": "Mysuru",
    "Hubli-Dharwad *": "Hubballi-Dharwad",
    "Mangalore": "Mangaluru",
    "Belgaum": "Belagavi",
    "Gulbarga": "Kalaburagi",
    "Bellary": "Ballari",
    "Bijapur": "Vijayapura",
    "Shimoga": "Shivamogga",
    "Tumkur": "Tumakuru",
    "Hospet": "Hosapete",
    "Chikmagalur": "Chikkamagaluru",
    "Gurgaon": "Gurugram",
    "Allahabad": "Prayagraj",
    "Faizabad": "Ayodhya",
    "Mughalsarai": "Deen Dayal Upadhyaya Nagar",
    "Haldwani-cum-Kathgodam": "Haldwani",
    "Hardwar": "Haridwar",
    "Greater Mumbai": "Mumbai",
    "Navi Mumbai Panvel Raigad": "Navi Mumbai",
    "Vasai Virar City": "Vasai-Virar",
    "Aurangabad|Maharashtra": "Chhatrapati Sambhajinagar",
    "Osmanabad": "Dharashiv",
    "Ahmadnagar": "Ahilyanagar",
    "Nanded Waghala": "Nanded",
    "Sangali": "Sangli",
    "Bid": "Beed",
    "Ahmadabad": "Ahmedabad",
    "Morvi": "Morbi",
    "Mahesana": "Mehsana",
    "Dohad": "Dahod",
    "Anklesvar": "Ankleshwar",
    "Raurkela": "Rourkela",
    "Brahmapur Town": "Berhampur",
    "Puri Town": "Puri",
    "Baleshwar": "Balasore",
    "Durg-Bhilainagar": "Durg-Bhilai",
    "Total Hanumangarh": "Hanumangarh",
    "Ganganagar": "Sri Ganganagar",
    "Jhunjhunun": "Jhunjhunu",
    "Chittaurgarh": "Chittorgarh",
    "Dhaulpur": "Dholpur",
    "S.A.S. Nagar": "Mohali",
    "Barddhaman": "Bardhaman",
    "Darjiling": "Darjeeling",
    "Koch Bihar": "Cooch Behar",
    "Puruliya": "Purulia",
    "Hoshangabad": "Narmadapuram",
    "Murwara (Katni)": "Katni",
}


def clean_census_name(name):
    """Drop the urban-area and civic-body labels, like "Ambala UA" or "Ambala (M Cl)"."""
    name = re.sub(r"\s+UA$", "", name.strip())
    if name != "Murwara (Katni)":
        name = re.sub(r"\s*\([^)]*\)\s*$", "", name)
    return name.strip()


def to_state(census_state, district_code, census_name):
    if census_state == "ANDHRA PRADESH":
        if district_code in TELANGANA_DISTRICTS or census_name == "Hyderabad":
            return "Telangana"
        return "Andhra Pradesh"
    return STATE_NAMES.get(census_state, census_state.title())


def read_rows(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            for line in (page.extract_text() or "").splitlines():
                match = ROW.match(line)
                if match:
                    yield match


def build(pdf_path):
    cities = {}
    for match in read_rows(pdf_path):
        census_state, district_code, raw_name = match[2], match[3], match[4]
        census_name = clean_census_name(raw_name)
        state = to_state(census_state, district_code, census_name)
        city = CITY_NAMES.get(f"{census_name}|{state}", CITY_NAMES.get(census_name, census_name))
        population = int(match[6].replace(",", ""))

        # The table lists an urban area and its main city separately. Keep one, with the larger figure.
        key = (state, city)
        if key not in cities or population > cities[key]["population_2011"]:
            cities[key] = {
                "state": state,
                "city": city,
                "census_name": raw_name,
                "population_2011": population,
            }

    rows = sorted(cities.values(), key=lambda row: (row["state"], -row["population_2011"]))
    OUTPUT.parent.mkdir(exist_ok=True)
    with OUTPUT.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=["state", "city", "census_name", "population_2011"])
        writer.writeheader()
        writer.writerows(rows)
    return rows


if __name__ == "__main__":
    rows = build(sys.argv[1])
    print(f"Wrote {len(rows)} cities in {len({row['state'] for row in rows})} states to {OUTPUT}")
