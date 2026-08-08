import os
import pandas as pd
import geopandas as gpd
import networkx as nx
import osmnx as ox
import matplotlib.pyplot as plt
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

geolocator = Nominatim(user_agent="cmpt353_tradeoff_analysis", timeout=10)

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

orig_node = ox.nearest_nodes(G_local, orig_geom.x, orig_geom.y)
dest_node = ox.nearest_nodes(G_local, dest_geom.x, dest_geom.y)


results = []
betas = [round(x * 0.1,1) for x in range(11)] # 0.0, 0.1, ... 1.0

for beta in betas:
    # Update weights based on current beta
    for u, v, key, data in G_local.edges(keys=True, data=True):
        ds = edges_local.loc[(u, v, key), 'crime_density']
        density = ds.iloc[0] if isinstance(ds, pd.Series) else ds
        
        n_len = min_max_scale(data.get('length', 1.0), min_len, max_len)
        n_crime = min_max_scale(density, min_crime, max_crime)
        
        # Cost = (1 - beta) * Length + beta * Crime
        data['dynamic_cost'] = ((1.0 - beta) * n_len) + (beta * n_crime)
        data['actual_length'] = data.get('length', 0)
        data['actual_crimes'] = edges_local.loc[(u, v, key), 'crime_count']
        if isinstance(data['actual_crimes'], pd.Series):
            data['actual_crimes'] = data['actual_crimes'].iloc[0]

    # Find shortest path using the dynamic cost
    try:
        path = nx.shortest_path(G_local, orig_node, dest_node, weight='dynamic_cost')
        
        # Calculate actual total distance and total crimes encountered on this path
        total_dist = sum(G_local[u][v][0]['actual_length'] for u, v in zip(path[:-1], path[1:]))
        total_crime = sum(G_local[u][v][0]['actual_crimes'] for u, v in zip(path[:-1], path[1:]))
        
        results.append({
            'beta': beta,
            'distance_m': total_dist,
            'crime_exposure': total_crime
        })
    except nx.NetworkXNoPath:
        print(f"No path found for beta={beta}")

results_df = pd.DataFrame(results)
shortest_stats = results_df[results_df['beta'] == 0.0].iloc[0]
safest_stats = results_df[results_df['beta'] == 0.7].iloc[0] # Using 0.7 as Safest based on your code

dist_increase = ((safest_stats['distance_m'] - shortest_stats['distance_m']) / shortest_stats['distance_m']) * 100
crime_decrease = ((shortest_stats['crime_exposure'] - safest_stats['crime_exposure']) / shortest_stats['crime_exposure']) * 100

print("\n" + "="*50)
print("REPORT METRICS FOR SECTION 4.1")
print("="*50)
print(f"Shortest Path (Beta=0.0): Distance = {shortest_stats['distance_m']:.1f} m, Crime Encounters = {shortest_stats['crime_exposure']:.0f}")
print(f"Safest Path   (Beta=0.7): Distance = {safest_stats['distance_m']:.1f} m, Crime Encounters = {safest_stats['crime_exposure']:.0f}")
print("-" * 50)
print(f"Distance Penalty: +{dist_increase:.2f}%")
print(f"Crime Reduction:  -{crime_decrease:.2f}%")
print("="*50 + "\n")

import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import LinearRegression


# 1. Prepare Data
X = results_df[['beta']].values
y_dist = results_df['distance_m'].values.reshape(-1, 1)
y_crime = results_df['crime_exposure'].values.reshape(-1, 1)

# 2. Normalize to 0~1 scale for fair Cost-Benefit comparison
scaler_dist = MinMaxScaler()
scaler_crime = MinMaxScaler()

y_dist_norm = scaler_dist.fit_transform(y_dist).flatten()
y_crime_norm = scaler_crime.fit_transform(y_crime).flatten()

# 3. Fit Polynomial Regression (Degree 4 to capture the sharp knee and spike)
poly = PolynomialFeatures(degree=4)
X_poly = poly.fit_transform(X)

reg_dist = LinearRegression().fit(X_poly, y_dist_norm)
reg_crime = LinearRegression().fit(X_poly, y_crime_norm)

# 4. Generate continuous beta values (0.00 to 1.00)
beta_smooth = np.linspace(0, 1, 100).reshape(-1, 1)
beta_smooth_poly = poly.transform(beta_smooth)

# Predict continuous curves
pred_dist_norm = reg_dist.predict(beta_smooth_poly)
pred_crime_norm = reg_crime.predict(beta_smooth_poly)

# 5. Calculate Utility (Net Benefit)
# Benefit = (1 - Normalized Crime Risk) : How much crime was reduced relative to max
# Cost = Normalized Distance : How much distance was added relative to max
# Net Utility = Benefit - Cost
benefit = 1.0 - pred_crime_norm
cost = pred_dist_norm
utility = benefit - cost

# Find the Beta that maximizes Net Utility
optimal_idx = np.argmax(utility)
optimal_beta = beta_smooth[optimal_idx][0]

print(f"Regression Complete! Mathematically Optimal Beta: {optimal_beta:.2f}")

fig3, ax = plt.subplots(figsize=(10, 6), facecolor='white')

# Plot Continuous Predicted Curves
ax.plot(beta_smooth, benefit * 100, color='#2A9D8F', linewidth=3, label='Regression: Safety Benefit (%)')
ax.plot(beta_smooth, cost * 100, color='#E63946', linewidth=3, label='Regression: Distance Cost (%)')
ax.plot(beta_smooth, utility * 100, color='#F4A261', linestyle='--', linewidth=3, label='Net Utility (Benefit - Cost)')

# Mark the Optimal Beta Point
ax.axvline(x=optimal_beta, color='black', linestyle=':', linewidth=2, label=f'Optimal $\\beta$ = {optimal_beta:.2f}')
ax.scatter([optimal_beta], [utility[optimal_idx] * 100], color='black', s=100, zorder=5)

# Formatting
ax.set_title("Optimal $\\beta$ Selection via Polynomial Regression", fontsize=16, fontweight='bold', color='black')
ax.set_xlabel(r"Safety Weight ($\beta$)", fontsize=12)
ax.set_ylabel("Normalized Metric (%)", fontsize=12)
ax.set_ylim([-50, 110])
ax.grid(True, linestyle='--', alpha=0.5)
ax.legend(loc='lower center', ncol=2, frameon=True, fontsize=10)

reg_chart_path = os.path.join(output_dir, "report_img5_regression_optimal_beta.png")
fig3.savefig(reg_chart_path, dpi=300, bbox_inches='tight', facecolor='white')
print(f"✅ Image 5 (Regression Chart) saved: {reg_chart_path}")

print("5. Generating Trade-off Chart Image (White Theme)...")
fig, ax1 = plt.subplots(figsize=(10, 6), facecolor='white')
ax1.set_facecolor('white')

color1 = '#d62728' 
ax1.set_xlabel(r'Safety Weight ($\beta$)', color='black', fontsize=12)
ax1.set_ylabel('Total Walking Distance (m)', color=color1, fontsize=12)
line1, = ax1.plot(results_df['beta'], results_df['distance_m'], color=color1, marker='o', linewidth=2, label='Distance (m)')
ax1.tick_params(axis='y', labelcolor=color1)
ax1.tick_params(axis='x', colors='black')


ax1.grid(True, linestyle='--', color='gray', alpha=0.3)

ax2 = ax1.twinx()  
color2 = '#1f77b4' 
ax2.set_ylabel('Total Crime Encounters', color=color2, fontsize=12)
line2, = ax2.plot(results_df['beta'], results_df['crime_exposure'], color=color2, marker='s', linewidth=2, label='Crime Exposure')
ax2.tick_params(axis='y', labelcolor=color2)


ax1.axvline(x=0.7, color='green', linestyle=':', linewidth=2, label='Chosen Safest Config ($\beta=0.7$)')

fig.suptitle('Trade-off Analysis: Walking Distance vs. Crime Exposure', color='black', fontsize=16)


lines = [line1, line2, plt.Line2D([0], [0], color='green', linestyle=':', linewidth=2)]
labels = [l.get_label() for l in lines[:2]] + ['Chosen Safest Config ($\\beta=0.7$)']
ax1.legend(lines, labels, loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=3, frameon=False, labelcolor='black')

chart_path = os.path.join(output_dir, "report_img3_tradeoff_chart_white.png")
fig.savefig(chart_path, dpi=300, bbox_inches='tight', facecolor='white')
print(f"✅ Image 3 (Trade-off Chart) saved: {chart_path}")