import json
import geopandas as gpd
import pandas as pd
import requests

# ==========================================
# 1. Layer Mapping Configuration
# ==========================================
wfs_url = "https://csgeo.richmond.ca/geoserver/wfs"

# List of 6 crime layers found from GeoServer
layers_info = {
    "rcsgeo:rcam_count_rbes_cmp23": "Residential Break & Enter",
    "rcsgeo:rcam_count_cbes_cmp23": "Commercial Break & Enter",
    "rcsgeo:rcam_count_tfas_cmp23": "Theft From Auto",
    "rcsgeo:rcam_count_toas_cmp23": "Theft of Auto",
    "rcsgeo:rcam_count_bike_cmp23": "Bicycle Theft",
    "rcsgeo:rcam_count_mail_cmp23": "Mail Theft",
}

gdfs = []

print("Starting extraction for all 6 Richmond crime layers...")

# ==========================================
# 2. Iterate and Fetch Data for Each Layer
# ==========================================
for layer_name, crime_type in layers_info.items():
    params = {
        "service": "WFS",
        "version": "1.1.0",
        "request": "GetFeature",
        "typeName": layer_name,
        "outputFormat": "application/json",
        "srsName": "EPSG:4326",
    }

    try:
        response = requests.get(wfs_url, params=params, verify=False)
        if response.status_code == 200:
            gdf_layer = gpd.read_file(response.text)

            # Standardize crime type column
            gdf_layer["Crime_Category"] = crime_type

            gdfs.append(gdf_layer)
            print(
                f"-> Success: '{crime_type}' fetched ({len(gdf_layer):,} records)"
            )
        else:
            print(
                f"-> Failed layer: {layer_name} (Status: {response.status_code})"
            )
    except Exception as e:
        print(f"-> Error fetching {layer_name}: {e}")

# ==========================================
# 3. Concatenate, Preprocess Datetime & Save Files
# ==========================================
if gdfs:
    # Merge all 6 GeoDataFrames into one single dataset
    gdf_richmond_all = pd.concat(gdfs, ignore_index=True)
    gdf_richmond_all = gpd.GeoDataFrame(gdf_richmond_all, crs="EPSG:4326")

    # Convert Unix Timestamp (q_date) to readable Vancouver Local Time
    if "q_date" in gdf_richmond_all.columns:
        gdf_richmond_all["date_formatted"] = pd.to_datetime(
            gdf_richmond_all["q_date"], unit="s", utc=True
        ).dt.tz_convert("America/Vancouver")
        gdf_richmond_all["YEAR"] = gdf_richmond_all["date_formatted"].dt.year
        gdf_richmond_all["MONTH"] = gdf_richmond_all["date_formatted"].dt.month
        gdf_richmond_all["HOUR"] = gdf_richmond_all["date_formatted"].dt.hour

    print("\n--- Download & Merge Complete ---")
    print(
        f"Total Combined Richmond Crime Records: {len(gdf_richmond_all):,} rows"
    )

    # Save as GeoJSON & CSV
    geojson_filename = "richmond_crime_all.geojson"
    csv_filename = "richmond_crime_all.csv"

    gdf_richmond_all.to_file(geojson_filename, driver="GeoJSON")
    gdf_richmond_all.to_csv(csv_filename, index=False)

    print(f"-> Saved: {geojson_filename}")
    print(f"-> Saved: {csv_filename}")

    print("\n--- Combined Dataset Sample ---")
    print(
        gdf_richmond_all[
            ["Crime_Category", "q_date", "date_formatted", "geometry"]
        ].head()
    )
else:
    print("No data was retrieved.")