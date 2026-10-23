"""
Download contextual features from OpenStreetMap via Overpass API.

Gets land use, roads, and industrial areas near each Mumbai monitoring station.
Attribution: (C) OpenStreetMap contributors, ODbL licence.

Usage:
    python -m src.ingest.osm_context
"""
import json
import time
from pathlib import Path
import pandas as pd
import requests

RAW_DIR = Path("data/raw/osm")
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

MUMBAI_STATION_COORDS = {
    "Bandra Kurla Complex": {"lat": 19.0596, "lon": 72.8613, "zone": "Western Suburbs", "env_type": "Commercial / Financial"},
    "Colaba": {"lat": 18.9067, "lon": 72.8147, "zone": "South Mumbai", "env_type": "Coastal / Residential"},
    "Kurla": {"lat": 19.0726, "lon": 72.8794, "zone": "Eastern Suburbs", "env_type": "Dense Urban / Transit Hub"},
    "Powai": {"lat": 19.1195, "lon": 72.9064, "zone": "Eastern Suburbs", "env_type": "Lake / Institutional / Mixed"},
    "Borivali East": {"lat": 19.2307, "lon": 72.8567, "zone": "Western Suburbs", "env_type": "Residential / Near National Park"},
    "Chembur": {"lat": 19.0522, "lon": 72.8949, "zone": "Eastern Suburbs", "env_type": "Industrial / Refinery corridor"},
    "Worli": {"lat": 19.0176, "lon": 72.8151, "zone": "South Mumbai", "env_type": "Coastal / Commercial"},
    "Sion": {"lat": 19.0437, "lon": 72.8640, "zone": "Central Mumbai", "env_type": "Heavy Traffic Highway Junction"},
    "Chhatrapati Shivaji Intl. Airport (T2)": {"lat": 19.0974, "lon": 72.8745, "zone": "Western Suburbs", "env_type": "Aviation / High Traffic"},
    "Vile Parle West": {"lat": 19.0990, "lon": 72.8432, "zone": "Western Suburbs", "env_type": "Suburban Residential"},
    "Mazgaon": {"lat": 18.9628, "lon": 72.8483, "zone": "South Mumbai", "env_type": "Port / Docks / Industrial"},
    "Malad West": {"lat": 19.1857, "lon": 72.8485, "zone": "Western Suburbs", "env_type": "Commercial / Tech Park"},
    "Chakala-Andheri East": {"lat": 19.1136, "lon": 72.8697, "zone": "Western Suburbs", "env_type": "Industrial Belt (MIDC)"},
    "Deonar": {"lat": 19.0553, "lon": 72.9167, "zone": "Eastern Suburbs", "env_type": "Solid Waste Dumping Ground / Abattoir"},
    "Mahape Navi Mumbai": {"lat": 19.1098, "lon": 73.0232, "zone": "Navi Mumbai", "env_type": "Industrial Corridor (TTC MIDC)"},
    "Nerul Navi Mumbai": {"lat": 19.0330, "lon": 73.0169, "zone": "Navi Mumbai", "env_type": "Planned Residential"},
    "Kandivali East": {"lat": 19.2065, "lon": 72.8675, "zone": "Western Suburbs", "env_type": "Suburban Highway"},
    "Mulund West": {"lat": 19.1764, "lon": 72.9467, "zone": "Eastern Suburbs", "env_type": "Foothill / Suburban"},
}

HEADERS = {
    "User-Agent": "CityPulse-Mumbai-Research/1.0 (academic decision-support; contact: citypulse@example.org)",
    "Accept": "application/json"
}

def query_osm_station(name: str, lat: float, lon: float, radius: int = 1500) -> dict:
    """Query OSM Overpass for features within radius (meters)."""
    query = f"""
    [out:json][timeout:25];
    (
      way["highway"~"motorway|trunk|primary|secondary"](around:{radius},{lat},{lon});
      way["landuse"~"industrial|construction|commercial|residential"](around:{radius},{lat},{lon});
      way["leisure"="park"](around:{radius},{lat},{lon});
    );
    out tags;
    """
    stats = {
        "station": name,
        "latitude": lat,
        "longitude": lon,
        "zone": MUMBAI_STATION_COORDS[name]["zone"],
        "env_type": MUMBAI_STATION_COORDS[name]["env_type"],
        "major_roads_count": 0,
        "industrial_areas_count": 0,
        "construction_sites_count": 0,
        "commercial_zones_count": 0,
        "residential_zones_count": 0,
        "parks_count": 0,
        "is_coastal": 1 if MUMBAI_STATION_COORDS[name]["zone"] == "South Mumbai" or "Coastal" in MUMBAI_STATION_COORDS[name]["env_type"] else 0,
    }
    try:
        resp = requests.post(OVERPASS_URL, data={"data": query}, headers=HEADERS, timeout=25)
        if resp.status_code == 200:
            data = resp.json()
            elements = data.get("elements", [])
            for el in elements:
                tags = el.get("tags", {})
                if "highway" in tags:
                    stats["major_roads_count"] += 1
                landuse = tags.get("landuse")
                if landuse == "industrial":
                    stats["industrial_areas_count"] += 1
                elif landuse == "construction":
                    stats["construction_sites_count"] += 1
                elif landuse == "commercial":
                    stats["commercial_zones_count"] += 1
                elif landuse == "residential":
                    stats["residential_zones_count"] += 1
                if tags.get("leisure") == "park":
                    stats["parks_count"] += 1
        else:
            print(f"  Overpass HTTP {resp.status_code} for {name}")
    except Exception as e:
        print(f"  OSM query error for {name}: {e}")

    return stats

def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = RAW_DIR / "mumbai_stations_osm_context.csv"

    if cache_path.exists():
        print(f"[CACHED] Reading existing OSM context from {cache_path}")
        df = pd.read_csv(cache_path)
        print(df.to_string())
        return df

    print(f"Querying OpenStreetMap for {len(MUMBAI_STATION_COORDS)} Mumbai stations...")
    rows = []
    for name, info in MUMBAI_STATION_COORDS.items():
        print(f"  Querying {name}...")
        res = query_osm_station(name, info["lat"], info["lon"])
        rows.append(res)
        time.sleep(2)

    df = pd.DataFrame(rows)
    df.to_csv(cache_path, index=False)
    print(f"\nSaved OSM station context to {cache_path}")
    print(df.to_string())
    return df

if __name__ == "__main__":
    main()
