import os
import pandas as pd
import geopandas as gpd
import networkx as nx
import osmnx as ox
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from shapely.geometry import Point
from geopy.geocoders import Nominatim
import warnings

warnings.filterwarnings('ignore')
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, "..", ".."))

graph_path = os.path.join(project_root, "Data", "Processed", "burnaby_walk.graphml")
crime_path = os.path.join(project_root, "Data", "Processed", "harmonized_crime_data.geojson")
output_dir = os.path.join(project_root, "Output")
os.makedirs(output_dir, exist_ok=True)

G_proj = ox.load_graphml(graph_path)
crimes = gpd.read_file(crime_path)
if crimes.crs != 'EPSG:26910':
    crimes = crimes.to_crs('EPSG:26910')

geolocator = Nominatim(user_agent="cmpt353_route_mapper_white", timeout=10)

origin_query = "Metropolis at Metrotown, Burnaby, BC"
dest_query = "7710 Kentwood street, Burnaby, BC"


o_loc = geolocator.geocode(origin_query)
d_loc = geolocator.geocode(dest_query)

orig_geom = gpd.GeoSeries([Point(o_loc.longitude, o_loc.latitude)], crs='EPSG:4326').to_crs('EPSG:26910').iloc[0]
dest_geom = gpd.GeoSeries([Point(d_loc.longitude, d_loc.latitude)], crs='EPSG:4326').to_crs('EPSG:26910').iloc[0]


buffer_dist = 1500 
minx, maxx = min(orig_geom.x, dest_geom.x) - buffer_dist, max(orig_geom.x, dest_geom.x) + buffer_dist
miny, maxy = min(orig_geom.y, dest_geom.y) - buffer_dist, max(orig_geom.y, dest_geom.y) + buffer_dist

valid_nodes = [n for n, d in G_proj.nodes(data=True) if minx <= d['x'] <= maxx and miny <= d['y'] <= maxy]
G_local = G_proj.subgraph(valid_nodes).copy()

_, edges_local = ox.graph_to_gdfs(G_local)
crimes_local = crimes.cx[minx:maxx, miny:maxy]

edges_buffered = edges_local.copy()
edges_buffered['geometry'] = edges_buffered.geometry.buffer(50)
edges_buffered = edges_buffered.reset_index()

joined = gpd.sjoin(crimes_local, edges_buffered, how='inner', predicate='within')
crime_counts = joined.groupby(['u', 'v', 'key']).size().reset_index(name='crime_count')

edges_local = edges_local.reset_index().merge(crime_counts, on=['u', 'v', 'key'], how='left')
edges_local['crime_count'] = edges_local['crime_count'].fillna(0)
edges_local['crime_density'] = edges_local['crime_count'] / edges_local['length']
edges_local = edges_local.set_index(['u', 'v', 'key'])

min_len, max_len = edges_local['length'].min(), edges_local['length'].max()
min_crime, max_crime = edges_local['crime_density'].min(), edges_local['crime_density'].max()

def min_max_scale(val, min_v, max_v): 
    return 0.0 if max_v == min_v else (val - min_v) / (max_v - min_v)

for u, v, key, data in G_local.edges(keys=True, data=True):
    ds = edges_local.loc[(u, v, key), 'crime_density']
    density = ds.iloc[0] if isinstance(ds, pd.Series) else ds
    
    n_len = min_max_scale(data.get('length', 1.0), min_len, max_len)
    n_crime = min_max_scale(density, min_crime, max_crime)
    
    data['cost_shortest'] = n_len
    data['cost_safest'] = (0.3 * n_len) + (0.7 * n_crime)

orig_node = ox.nearest_nodes(G_local, orig_geom.x, orig_geom.y)
dest_node = ox.nearest_nodes(G_local, dest_geom.x, dest_geom.y)

route_shortest = nx.shortest_path(G_local, orig_node, dest_node, weight='cost_shortest')
route_safest = nx.shortest_path(G_local, orig_node, dest_node, weight='cost_safest')




fig, ax = ox.plot_graph_routes(
    G_local,
    routes=[route_shortest, route_safest],
    route_colors=['#E63946', '#2A9D8F'], 
    route_linewidths=[3, 5], 
    route_alpha=0.9,
    node_size=0, 
    edge_color="#CCCCCC", 
    edge_linewidth=0.5,
    bgcolor="white",     
    show=False,
    close=False,
    figsize=(12, 12)
)

# Plot Origin and Destination Markers
orig_x, orig_y = G_local.nodes[orig_node]['x'], G_local.nodes[orig_node]['y']
dest_x, dest_y = G_local.nodes[dest_node]['x'], G_local.nodes[dest_node]['y']

ax.scatter(orig_x, orig_y, c='#F4A261', s=150, zorder=5, edgecolors='black', marker='o') # Orange origin
ax.scatter(dest_x, dest_y, c='#9D4EDD', s=150, zorder=5, edgecolors='black', marker='*') # Purple dest

legend_elements = [
    Line2D([0], [0], color='#E63946', lw=3, label='Shortest Path (Dist Optimized)'),
    Line2D([0], [0], color='#2A9D8F', lw=5, label='Safest Path (Crime Avoided)'),
    Line2D([0], [0], marker='o', color='w', markerfacecolor='#F4A261', markeredgecolor='black', markersize=12, label='Origin'),
    Line2D([0], [0], marker='*', color='w', markerfacecolor='#9D4EDD', markeredgecolor='black', markersize=15, label='Destination')
]

ax.legend(handles=legend_elements, loc='upper left', fontsize=12, 
          frameon=True, facecolor='white', edgecolor='black', labelcolor='black')


ax.set_title("Routing Comparison: Shortest vs. Safest Path", color='black', fontsize=20, pad=20, fontweight='bold')


image_path = os.path.join(output_dir, "report_img4_route_comparison_white.png")
fig.savefig(image_path, dpi=300, bbox_inches='tight', facecolor='white')

print(f"saved: {image_path}")