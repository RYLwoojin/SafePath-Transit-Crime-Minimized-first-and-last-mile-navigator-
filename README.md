# 🛡️ Navigating Safely: First and Last Mile Pedestrian Routing

**CMPT 353 Final Project - Simon Fraser University**

A multimodal, data-driven navigation algorithm designed to minimize pedestrian crime exposure during the "First and Last Mile" of public transit journeys. This project integrates Greater Vancouver municipal crime datasets, TransLink GTFS schedules, and OpenStreetMap road networks to dynamically compute the most balanced path between travel distance and safety.

## 👥 Contributors
* **woojin lim** - 301435### - wla177@sfu.ca

---

## 🛠️ Tech Stack & Core Libraries
* **Language:** Python 3.10+
* **Geospatial Processing:** `geopandas`, `shapely`, `geopy`
* **Network & Routing:** `networkx`, `osmnx`
* **Data Manipulation:** `pandas`
* **Visualization & UI:** `folium`, `matplotlib`, `streamlit`

---

## 📂 Repository Structure
\`\`\`text
├── Data/
│   ├── Crime Data/        # Place raw municipal crime CSVs here
│   ├── Transit Data/      # Extracted TransLink GTFS text files here
│   └── Processed/         # Generated harmonized GeoJSON will be saved here
├── Scripts/
│   ├──CrimeDataCollection 
│   │    └──Data Collecting python files # Extracted the underlying ArcGIS REST API endpoint and queried the raw data directly using Python  
│   └──Main 
│       ├── DataCleaning.py    # Integrates and harmonizes heterogeneous crime datasets
│       ├── GVGraph.py         # Visualizes raw GTFS transit graph
│       ├── tradeoff.py        # Generates multi-objective trade-off analysis chart
│       └── gen_route_map.py   # Generates high-res static maps for the report
├── SafeRouting.ipynb      # Main Jupyter Notebook detailing the algorithm process
├── requirements.txt       # Python dependencies
└── README.md
\`\`\`


## 🚀 How to Run the Project

### Step 1: Install Dependencies
Open your terminal and install the required Python packages:
```
pip install -r requirements.txt
```

### Step 2: Data Preprocessing
Run the data cleaning script to merge all municipal crime data into a single harmonized GeoJSON file (converted to UTM EPSG:26910):
```
python Scripts/DataCleaning.py
```

### Step 3: Run the Routing Algorithm & Visualization
Launch the main Jupyter Notebook to execute the multimodal routing algorithm, process the network, and render the interactive folium maps:
```
jupyter notebook SafeRouting.ipynb
```
(Inside the notebook, you can modify the Origin and Destination address queries to generate customized Shortest vs. Safest multimodal paths dynamically.)
---

## 📊 Key Features
1. **Heterogeneous Data Integration:** Harmonizes disparate crime schemas from 5 different municipalities into a unified spatial dataset.
2. **Min-Max Normalized Multi-Objective Routing:** Scales street length and crime density to a `[0, 1]` range to perfectly balance travel distance and crime exposure using Dijkstra's algorithm.
3. **Dynamic Bounding:** Crops OSMnx road networks within a 1.5km radius of the user's location to prevent memory overload and ensure fast computation.
4. **GTFS Integration:** Links pedestrian paths directly with exact GTFS bus/SkyTrain route geometries.
