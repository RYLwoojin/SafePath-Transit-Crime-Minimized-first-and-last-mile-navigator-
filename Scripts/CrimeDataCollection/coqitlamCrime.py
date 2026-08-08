import json
import geopandas as gpd
import pandas as pd
import requests

# ==========================================
# 1. Configuration & Endpoint Setup
# ==========================================
# Coquitlam ArcGIS REST API Base Endpoint
base_url = "https://services2.arcgis.com/Q6Lq3evZUGfPrN7o/arcgis/rest/services/Property_Crime_Data_Layer_Coquitlam/FeatureServer/0/query"

all_features = []
offset = 0
record_limit = 2000

print("Starting full data extraction for Coquitlam Crime Dataset...")

# ==========================================
# 2. Fetch All Records via Pagination Loop
# ==========================================
while True:
    params = {
        "where": "1=1",  # Unfiltered query for all records
        "outFields": "*",  # Retrieve all columns
        "outSR": "4326",  # WGS84 Lat/Lon
        "f": "geojson",  # GeoJSON format
        "resultOffset": offset,
        "resultRecordCount": record_limit,
    }

    response = requests.get(base_url, params=params)

    if response.status_code == 200:
        geojson_data = response.json()
        features = geojson_data.get("features", [])

        if not features:
            break

        all_features.extend(features)
        print(
            f"-> Fetched records {offset:,} to {offset + len(features):,}..."
        )

        offset += len(features)

        if len(features) < record_limit:
            break
    else:
        print(f"Failed at offset {offset}. Status code: {response.status_code}")
        break

# ==========================================
# 3. Convert to GeoDataFrame & Save Local Files
# ==========================================
if all_features:
    full_geojson = {"type": "FeatureCollection", "features": all_features}
    gdf_coquitlam_all = gpd.read_file(json.dumps(full_geojson))

    print("\n--- Extraction Complete ---")
    print(
        f"Total Coquitlam Crime Records Retrieved: {len(gdf_coquitlam_all):,} rows"
    )

    # Save as GeoJSON & CSV
    geojson_filename = "coquitlam_crime_all.geojson"
    csv_filename = "coquitlam_crime_all.csv"

    gdf_coquitlam_all.to_file(geojson_filename, driver="GeoJSON")
    gdf_coquitlam_all.to_csv(csv_filename, index=False)

    print(f"-> Successfully saved: {geojson_filename}")
    print(f"-> Successfully saved: {csv_filename}")

    print("\n--- Sample Data Preview ---")
    print(gdf_coquitlam_all.head())
else:
    print("No features were downloaded. Please check connection.")