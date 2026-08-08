import glob
import os
import geopandas as gpd
import pandas as pd

# =========================================================================
# 1. Dynamic Path Resolution
# =========================================================================
# Get the directory where SurreyCrime.py is located (.../Script/CrimeDataCollection)
script_dir = os.path.dirname(os.path.abspath(__file__))

# Navigate to the project root directory (.../GreatVancouverCrimeAndTransport)
project_root = os.path.abspath(os.path.join(script_dir, "..", ".."))

# Define input/output directory paths
crime_data_dir = os.path.join(project_root, "Data", "Crime Data")
processed_dir = os.path.join(project_root, "Data", "Processed")

os.makedirs(processed_dir, exist_ok=True)

print(f"📂 Reading crime data from: {crime_data_dir}")

# =========================================================================
# 2. VPD (Vancouver Police Dept) Crime Data Processing
# =========================================================================
# Category mapping for VPD crime types to standardized project categories
VPD_CATEGORY_MAP = {
    "Other Theft": "Other Theft",
    "Theft from Vehicle": "Theft From Auto",
    "Theft of Bicycle": "Bicycle Theft",
    "Theft of Vehicle": "Theft Of Auto",
    "Break and Enter Commercial": "Commercial B&E",
    "Break and Enter Residential/Other": "Residential B&E",
}

# Find all annual Vancouver crime CSV files (2021-2026)
vpd_csv_pattern = os.path.join(
    crime_data_dir, "crimedata_csv_AllNeighbourhoods_*.csv"
)
vpd_files = sorted(glob.glob(vpd_csv_pattern))

vancouver_features = []

if vpd_files:
    print(f"🔍 Found {len(vpd_files)} Vancouver crime CSV files.")
    for file_path in vpd_files:
        filename = os.path.basename(file_path)
        print(f"   - Processing: {filename}")
        df = pd.read_csv(file_path)

        # Filter valid UTM Zone 10N coordinates and mapped crime categories
        valid_df = df[
            (df["X"] > 0) & (df["Y"] > 0) & (df["TYPE"].isin(VPD_CATEGORY_MAP))
        ].copy()

        for _, row in valid_df.iterrows():
            feature = {
                "City": "Vancouver",
                "YEAR": int(row["YEAR"]),
                "MONTH": int(row["MONTH"]),
                "Original_Type": str(row["TYPE"]),
                "Crime_Category": VPD_CATEGORY_MAP[row["TYPE"]],
                "geometry": gpd.points_from_xy([row["X"]], [row["Y"]])[0],
            }
            vancouver_features.append(feature)

    print(
        f"✅ Successfully processed {len(vancouver_features)} Vancouver crime records."
    )
else:
    print("⚠️ No Vancouver crime CSV files found.")

# =========================================================================
# 3. Surrey / Other Municipality Crime Data Processing (Optional Expansion)
# =========================================================================
surrey_csv_path = os.path.join(crime_data_dir, "SurreyCrime.csv")
surrey_features = []

if os.path.exists(surrey_csv_path):
    print(f"🔍 Found Surrey crime CSV: {os.path.basename(surrey_csv_path)}")
    surrey_df = pd.read_csv(surrey_csv_path)

    # Note: Adjust column names if Surrey dataset has different schemas (e.g., Lat/Lon or X/Y)
    # Example parsing logic:
    if "X" in surrey_df.columns and "Y" in surrey_df.columns:
        valid_surrey = surrey_df[
            (surrey_df["X"] > 0) & (surrey_df["Y"] > 0)
        ].copy()
        for _, row in valid_surrey.iterrows():
            feature = {
                "City": "Surrey",
                "YEAR": int(row.get("YEAR", 2021)),
                "MONTH": int(row.get("MONTH", 1)),
                "Original_Type": str(row.get("TYPE", "General Offence")),
                "Crime_Category": "Other Theft",
                "geometry": gpd.points_from_xy([row["X"]], [row["Y"]])[0],
            }
            surrey_features.append(feature)
    print(
        f"✅ Successfully processed {len(surrey_features)} Surrey crime records."
    )

# =========================================================================
# 4. Harmonize and Export GeoJSON (EPSG:26910)
# =========================================================================
all_features = vancouver_features + surrey_features

if all_features:
    gdf_combined = gpd.GeoDataFrame(all_features, crs="EPSG:26910")

    output_geojson_path = os.path.join(
        processed_dir, "harmonized_crime_data.geojson"
    )
    gdf_combined.to_file(output_geojson_path, driver="GeoJSON")
    print(f"\n🎉 Successfully exported combined GeoJSON to:")
    print(f"   📍 {output_geojson_path}")
    print(f"   📊 Total Features Exported: {len(gdf_combined)}")
else:
    print("\n❌ No valid crime features were processed.")