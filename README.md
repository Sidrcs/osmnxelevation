# OSMnxElevation
**OSMnxElevation** is a lightweight Python package that binds elevation from raster datasets to nodes and edges of OpenStreetMaps (OSM) to create input network datasets that support elevation-based network analysis like walkability and bikeability in ArcGIS Pro (ESRI 2020).

## Demo
[Basic Demo Notebook](https://github.com/Sidrcs/osmnxelevation/blob/6d6d89f75d5714dac425f413e1f0a4ae807df43f/lib/Demo.ipynb)

## How to Install and Use

### Installation
Step 1: Clone the repository
```
git clone https://github.com/Sidrcs/osmnxelevation.git
```
Step 2: Change the directory to lib folder
```
cd lib
```
Step 3: Install environment.yml to install dependencies using Conda
```
conda env create -f environment.yml
```
Step 4: Activate the Conda environment
```
conda activate oxelev
```
Step 5: Launch Jupyter Notebook from the terminal (Mac) or Anaconda prompt (Windows)
```
jupyter-notebook
```
### Usage
1. Import the `NetworkDataset` module from `osmnxelevation` library.<br>
2. Initialize the `NetworkDataset` instance with the required arguments:
    - `place`(str): City, County, State, Country [Eg: Madison, Dane, Wisconsin, US]
    - `raster_fpath`(str): Folder path containing Digital Elevation Models (DEMs) raster datasets. Try: [USGS TNM Downloader](https://apps.nationalmap.gov/downloader/)
    - `output_fpath`(str): Output folder path to store geopackage outputs after elevation binding
3. Launch elevation binding to network using method `bind_elevation_to_network()`
```
# import library
import osmnxelevate as oe

# Create an instance of NetworkDataset object
ndst = oe.NetworkDataset(place = "Midland, Midland County, TX, USA",
                        raster_fpath = "Elevation_OSM\Midland_DEM",
                        output_fpath = "Elevation_OSM")

# Binds elevation to nodes and edges
ndst.bind_elevation_to_network()
```
### Visualization
1. The NetworkDataset module has `visualize_edges_elevation(gpkg_fpath, col_name, title)` which visualizes **from_elev** or **to_elev** columns of the **edge_network.gpkg** created from the output of the `bind_elevation_to_network()` method:

```
gpkg_fpath = "edge_network.gpkg"
col_name = "from_elev"
title = "Elevation model of Midland City, TX"
ndst.visualize_edges_elevation(gpkg_fpath, col_name, title)
```
<img src="https://github.com/Sidrcs/osmnxelevation/blob/main/elevation.png?raw=true">

## Credits
Boeing, G. 2017. "[OSMnx: New Methods for Acquiring, Constructing, Analyzing, and Visualizing Complex Street Networks](https://geoffboeing.com/publications/osmnx-complex-street-networks/)." _Computers, Environment and Urban Systems_ 65, 126-139.

## LICENSE
OSMnxElevation is open source and licensed under the MIT license. [License](https://github.com/Sidrcs/osmnxelevation/blob/6d6d89f75d5714dac425f413e1f0a4ae807df43f/lib/LICENSE) requires that derivative works provide proper attribution.
