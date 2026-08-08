import json
import geopandas as gpd
import pandas as pd
import requests

# ==========================================
# 1. Configuration & Initial Setup
# ==========================================
base_url = "https://services5.arcgis.com/NgSjNljtJn9hphOU/arcgis/rest/services/AnonymizedCrime/FeatureServer/0/query"

all_features = []
offset = 0
record_limit = 2000

print("Starting full data extraction for Burnaby Crime Dataset...")

# ==========================================
# 2. Fetch All Records via Pagination Loop
# ==========================================
while True:
    params = {
        "where": "1=1",
        "outFields": "*",
        "outSR": "4326",
        "f": "geojson",
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

        # Exit loop if the last batch is smaller than the limit
        if len(features) < record_limit:
            break
    else:
        print(f"Failed at offset {offset}. Status code: {response.status_code}")
        break

# ==========================================
# 3. Convert to GeoDataFrame & Save Local Files
# ==========================================
if all_features:
    # Build complete GeoJSON structure
    full_geojson = {"type": "FeatureCollection", "features": all_features}
    gdf_burnaby_all = gpd.read_file(json.dumps(full_geojson))

    print("\n--- Extraction Complete ---")
    print(
        f"Total Burnaby Crime Records Retrieved: {len(gdf_burnaby_all):,} rows"
    )

    # Save as GeoJSON (for GeoPandas / Spatial Join)
    geojson_filename = "burnaby_crime_all.geojson"
    gdf_burnaby_all.to_file(geojson_filename, driver="GeoJSON")
    print(f"-> Successfully saved: {geojson_filename}")

    # Save as CSV (for Excel / inspection)
    csv_filename = "burnaby_crime_all.csv"
    gdf_burnaby_all.to_csv(csv_filename, index=False)
    print(f"-> Successfully saved: {csv_filename}")

    print("\n--- Sample Data Preview ---")
    print(
        gdf_burnaby_all[
            ["OBJECTID", "File_Type", "Municipality", "geometry"]
        ].head()
    )
else:
    print("No features were downloaded. Please check the network or URL.")