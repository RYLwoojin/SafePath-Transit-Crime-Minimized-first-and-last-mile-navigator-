import os
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from shapely import wkt

DATA_DIR = os.path.join("Data", "Crime Data")

 
# 1. Load Vancouver Data
vancouver_files = [
    "crimedata_csv_AllNeighbourhoods_2021.csv",
    "crimedata_csv_AllNeighbourhoods_2022.csv",
    "crimedata_csv_AllNeighbourhoods_2023.csv",
    "crimedata_csv_AllNeighbourhoods_2024.csv",
    "crimedata_csv_AllNeighbourhoods_2025.csv",
    "crimedata_csv_AllNeighbourhoods_2026.csv"
]
dfs = []
for f in vancouver_files:
    file_path = os.path.join(DATA_DIR, f)
    if os.path.exists(file_path):
        dfs.append(pd.read_csv(file_path))
    else:
        print(f"Warning: File not found: {f}")

if not dfs:
    raise ValueError("Vancouver crime data does not exist. Please check the directory structure.")

van_df = pd.concat(dfs, ignore_index=True)
van_df = van_df[van_df['X'] > 0].copy() 
# Vancouver coordinates are already in UTM Zone 10N (EPSG:32610)
van_gdf = gpd.GeoDataFrame(
    van_df, 
    geometry=gpd.points_from_xy(van_df.X, van_df.Y), 
    crs="EPSG:32610"
)
van_gdf['City'] = 'Vancouver'
van_gdf.rename(columns={'TYPE': 'Original_Type'}, inplace=True)
# 2. Load Burnaby Data

bby_path = os.path.join(DATA_DIR, "burnaby_crime_all.csv")
if os.path.exists(bby_path):
    bby_df = pd.read_csv(bby_path)
    bby_df = bby_df.dropna(subset=['geometry']).copy()
    bby_df['geometry'] = bby_df['geometry'].apply(wkt.loads)
    # Convert Burnaby from EPSG:4326 (Lat/Long) to EPSG:32610 (UTM Zone 10N)
    bby_gdf = gpd.GeoDataFrame(bby_df, geometry='geometry', crs="EPSG:4326").to_crs("EPSG:32610")
    
    # errors='coerce' added to safely parse dates without dropping the dataframe
    bby_gdf['YEAR'] = pd.to_datetime(bby_gdf['ReportedDate'], unit='ms', errors='coerce').dt.year
    bby_gdf['MONTH'] = pd.to_datetime(bby_gdf['ReportedDate'], unit='ms', errors='coerce').dt.month
    bby_gdf['City'] = 'Burnaby'
    bby_gdf.rename(columns={'File_Type': 'Original_Type'}, inplace=True)
else:
    print(f"Warning: Burnaby data not found at ({bby_path}). Initializing empty GeoDataFrame.")
    bby_gdf = gpd.GeoDataFrame(columns=['City', 'YEAR', 'MONTH', 'Original_Type', 'geometry'], geometry='geometry', crs="EPSG:32610")

# 3. Load Coquitlam Data

coq_path = os.path.join(DATA_DIR, "coquitlam_crime_all.csv")
if os.path.exists(coq_path):
    coq_df = pd.read_csv(coq_path)
    coq_df = coq_df.dropna(subset=['geometry']).copy()
    coq_df['geometry'] = coq_df['geometry'].apply(wkt.loads)
    # Convert Coquitlam from EPSG:4326 (Lat/Long) to EPSG:32610 (UTM Zone 10N)
    coq_gdf = gpd.GeoDataFrame(coq_df, geometry='geometry', crs="EPSG:4326").to_crs("EPSG:32610")
    
    coq_gdf['YEAR'] = pd.to_datetime(coq_df['Reported_Date'], unit='ms', errors='coerce').dt.year
    coq_gdf['MONTH'] = pd.to_datetime(coq_df['Reported_Date'], unit='ms', errors='coerce').dt.month
    coq_gdf['City'] = 'Coquitlam'
    coq_gdf.rename(columns={'File_Type': 'Original_Type'}, inplace=True)
else:
    print(f"Warning: Coquitlam data not found at ({coq_path}). Initializing empty GeoDataFrame.")
    coq_gdf = gpd.GeoDataFrame(columns=['City', 'YEAR', 'MONTH', 'Original_Type', 'geometry'], geometry='geometry', crs="EPSG:32610")


# 4. Load Richmond Data

rmd_path = os.path.join(DATA_DIR, "richmond_crime_all.csv")
if os.path.exists(rmd_path):
    rmd_df = pd.read_csv(rmd_path)
    rmd_df = rmd_df.dropna(subset=['geometry']).copy()
    rmd_df['geometry'] = rmd_df['geometry'].apply(wkt.loads)
    # Convert Richmond from EPSG:4326 (Lat/Long) to EPSG:32610 (UTM Zone 10N)
    rmd_gdf = gpd.GeoDataFrame(rmd_df, geometry='geometry', crs="EPSG:4326").to_crs("EPSG:32610")
    
    rmd_gdf['City'] = 'Richmond'
    rmd_gdf.rename(columns={'Crime_Category': 'Original_Type'}, inplace=True)
else:
    print(f"Warning: Richmond data not found at ({rmd_path}). Initializing empty GeoDataFrame.")
    rmd_gdf = gpd.GeoDataFrame(columns=['City', 'YEAR', 'MONTH', 'Original_Type', 'geometry'], geometry='geometry', crs="EPSG:32610")


# 5. Load Surrey Data

surrey_path = os.path.join(DATA_DIR, "SurreyCrime.csv")
if os.path.exists(surrey_path):
    sur_df = pd.read_csv(surrey_path)
    
    # Surrey dataset does NOT have coordinates. We assign an empty geometry (None)
    # so it concatenates properly without crashing GeoPandas.
    sur_df['geometry'] = None
    sur_gdf = gpd.GeoDataFrame(sur_df, geometry='geometry', crs="EPSG:32610")
    
    # Map the unique Surrey crime column
    if 'INCIDENT_TYPE' in sur_gdf.columns:
        sur_gdf.rename(columns={'INCIDENT_TYPE': 'Original_Type'}, inplace=True)

    # Surrey already separates MONTH and YEAR in its raw data, bypassing timestamp parsing
    sur_gdf['City'] = 'Surrey'
else:
    print(f"Warning: Surrey data not found at ({surrey_path}). Initializing empty GeoDataFrame.")
    sur_gdf = gpd.GeoDataFrame(columns=['City', 'YEAR', 'MONTH', 'Original_Type', 'geometry'], geometry='geometry', crs="EPSG:32610")

 
# 6. Combine 

cols_to_keep = ['City', 'YEAR', 'MONTH', 'Original_Type', 'geometry']

# Filter only valid, non-empty GeoDataFrames that successfully parsed all required columns
all_gdfs = [van_gdf, bby_gdf, coq_gdf, rmd_gdf, sur_gdf]
valid_gdfs = [gdf[cols_to_keep] for gdf in all_gdfs if not gdf.empty and set(cols_to_keep).issubset(gdf.columns)]

if valid_gdfs:
    combined_gdf = pd.concat(valid_gdfs, ignore_index=True)
else:
    raise ValueError("No valid crime data could be loaded from any city.")

# Define standardized mapping dictionary for diverse city crime categories
type_mapping = {
    'Break and Enter Residential/Other': 'Residential B&E',
    'BREAK & ENTER-RESIDENCE': 'Residential B&E',
    'Break & Enter - Residence': 'Residential B&E',
    'Residential Break & Enter': 'Residential B&E',
    'Break and Enter Commercial': 'Commercial B&E',
    'BREAK & ENTER-BUSINESS': 'Commercial B&E',
    'Break & Enter - Business': 'Commercial B&E',
    'Commercial Break & Enter': 'Commercial B&E',
    'Theft from Vehicle': 'Theft From Auto',
    'THEFT FROM AUTO': 'Theft From Auto',
    'Theft from Auto': 'Theft From Auto',
    'Theft from Motor Vehicle': 'Theft From Auto',  # Added for Surrey
    'Theft of Vehicle': 'Theft Of Auto',
    'THEFT OF AUTO': 'Theft Of Auto',
    'Theft of Auto': 'Theft Of Auto',
    'Theft of Motor Vehicle': 'Theft Of Auto',      # Added for Surrey
    'Theft of Bicycle': 'Bicycle Theft',
    'Bicycle Theft': 'Bicycle Theft',
    'Other Theft': 'Other Theft',
    'BREAK & ENTER-OTHER': 'Other Theft',
    'Mail Theft': 'Other Theft',
    'Shoplifting': 'Other Theft'                    # Added for Surrey
}

combined_gdf['Crime_Category'] = combined_gdf['Original_Type'].map(type_mapping)
combined_gdf = combined_gdf.dropna(subset=['Crime_Category'])

#output
print("Final GeoDataFrame Head")
print(combined_gdf.head())

print("\n Standardized Crime Category Counts")
print(combined_gdf['Crime_Category'].value_counts())

print("\n Record Counts by City")
print(combined_gdf['City'].value_counts())


output_dir = os.path.join("Data", "Processed")
os.makedirs(output_dir, exist_ok=True)
output_file = os.path.join(output_dir, "harmonized_crime_data.geojson")
combined_gdf.to_file(output_file, driver="GeoJSON")
print(f"\n Harmonized crime data saved to: {output_file}")