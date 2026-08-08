import os
import pandas as pd
import geopandas as gpd
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.collections as mcoll
import zipfile
import warnings

warnings.filterwarnings('ignore')

transit_dir = os.path.join("Data", "Transit Data")
os.makedirs(transit_dir, exist_ok=True)

zip_path = os.path.join("Data", "google_transit.zip")
if os.path.exists(zip_path):
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(transit_dir)
    print("✅ Extracted google_transit.zip")

try:
    stops_df = pd.read_csv(os.path.join(transit_dir, "stops.txt"))
    stop_times_df = pd.read_csv(os.path.join(transit_dir, "stop_times.txt"))
    print(f"✅ Loaded {len(stops_df)} stops and {len(stop_times_df)} stop times.")
except Exception as e:
    raise FileNotFoundError(f"Error loading GTFS files: {e}")

# Ensure IDs are strings to avoid mapping issues later
stops_df['stop_id'] = stops_df['stop_id'].astype(str)
stop_times_df['stop_id'] = stop_times_df['stop_id'].astype(str)

# Sort by trip_id and stop_sequence to find consecutive stops
stop_times_sorted = stop_times_df.sort_values(by=['trip_id', 'stop_sequence'])

# Shift stop_id to get the destination node for each edge
stop_times_sorted['next_stop_id'] = stop_times_sorted.groupby('trip_id')['stop_id'].shift(-1)
edges_df = stop_times_sorted.dropna(subset=['next_stop_id'])[['stop_id', 'next_stop_id']].drop_duplicates()

# Create NetworkX Graph
G = nx.from_pandas_edgelist(edges_df, 'stop_id', 'next_stop_id', create_using=nx.Graph())

# Create a position dictionary for the nodes {stop_id: (longitude, latitude)}
pos = {row['stop_id']: (row['stop_lon'], row['stop_lat']) for idx, row in stops_df.iterrows()}

# Filter graph to only include nodes with valid coordinates
valid_nodes = [node for node in G.nodes if node in pos]
G_valid = G.subgraph(valid_nodes)

print(f"Constructed Transit Graph: {G_valid.number_of_nodes()} Nodes, {G_valid.number_of_edges()} Edges")


lons = [pos[n][0] for n in valid_nodes]
lats = [pos[n][1] for n in valid_nodes]
min_lon, max_lon = min(lons), max(lons)
min_lat, max_lat = min(lats), max(lats)

fig, axes = plt.subplots(1, 2, figsize=(20, 10))

# Plot 1: Raw Transit Stops
axes[0].scatter(stops_df['stop_lon'], stops_df['stop_lat'], s=1, c='blue', alpha=0.5)
axes[0].set_title('Metro Vancouver Transit Stops (Raw Locations)', fontsize=16)
axes[0].set_xlabel('Longitude')
axes[0].set_ylabel('Latitude')
axes[0].set_xlim([min_lon - 0.05, max_lon + 0.05])
axes[0].set_ylim([min_lat - 0.05, max_lat + 0.05])
axes[0].grid(True, linestyle='--', alpha=0.6)

# Plot 2: Transit Network Graph (Nodes + Edges)
# Use LineCollection for highly optimized edge rendering
edge_lines = [(pos[u], pos[v]) for u, v in G_valid.edges()]
lc = mcoll.LineCollection(edge_lines, colors='red', linewidths=0.5, alpha=0.5)
axes[1].add_collection(lc)

axes[1].scatter(lons, lats, s=2, c='black', alpha=0.7)
axes[1].set_title('Metro Vancouver Transit Network Graph', fontsize=16)
axes[1].set_xlabel('Longitude')
axes[1].set_ylabel('Latitude')
axes[1].set_xlim([min_lon - 0.05, max_lon + 0.05])
axes[1].set_ylim([min_lat - 0.05, max_lat + 0.05])
axes[1].grid(True, linestyle='--', alpha=0.6)

plt.tight_layout()
plt.show()