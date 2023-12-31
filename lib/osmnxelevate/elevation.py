"""
Module Name: OSMnxElevation
Description: Package to bind elevation to OSM road networks
@author: Siddharth Ramavajjala
"""

import os
import warnings
import osmnx as ox
import geopandas as gpd
import rioxarray as rxr
import matplotlib.pyplot as plt
from shapely.geometry import box
ox.settings.log_console=True
ox.settings.use_cache=True



class NetworkDataset:
    """NetworkDataset manages OSMNx module and appends elevation to edge network"""
    def __init__(self, place, raster_fpath, output_fpath):
        """NetworkDataset is initialized
        
        Parameters
        ----------
        place: str
            Input format: City, County/District, State/Province, Country
            Eg: Madison, Dane County, Wisconsin, USA
        raster_fpath: str
            Digital Elevation Models (DEMs) folder path to bind the elevation
        output_fpath: str
            Folder path to store output ESRI shapefile
        """
        self.place = place
        self.raster_fpath = raster_fpath
        self.output_fpath = output_fpath
        print(f"Current working directory changed to {output_fpath}")
        os.chdir(output_fpath)
        warnings.simplefilter(action="ignore", category=UserWarning)
        
    def _save_geopackage(self):
        """Function to extract geopackage from OSM to a folder"""
        try:
            if not isinstance(self.place, str):
                raise TypeError("Place input has to be comma seperated string")
            # Load the graph based on 'drive' network
            graph = ox.graph_from_place(self.place, network_type="drive")
            # Saves geopackage to output folder path
            gpkg_path = f"{self.place.split(',')[0]}.gpkg"
            fpath = os.path.join(self.output_fpath, gpkg_path)
            if os.path.exists(fpath):
                os.remove(fpath)
            ox.save_graph_geopackage(graph, filepath=fpath)
            return fpath
        except TypeError as e:
            print(f"{str(e)}")

    def _read_geopackage(self, fpath):
        """Function to read nodes and edges geopackage from local folder path
        
        Parameters
        ----------
        fpath: str
            Geopackage file path retrieved from OSMnx graph query of place string
        """
        gdf_dict = {}
        # Check if geopackage exists
        if os.path.exists(fpath) and fpath.endswith(".gpkg"):
            # Reads 'nodes' layer from geopackage 
            node_gdf = gpd.read_file(fpath, layer="nodes")
            # Reads 'edges' layer from geopackage
            edge_gdf = gpd.read_file(fpath, layer="edges")
            # Reprojects both GeoDataFrames to EPSG:3857 into a dictionary
            gdf_dict["nodes"] = node_gdf.to_crs(3857)
            gdf_dict["edges"] = edge_gdf.to_crs(3857)
        return gdf_dict

    def _extract_raster_bounds(self):
        """Function extracts raster bounds and returns a dictionary in EPSG: 3857"""
        bounds = {}
        # Opens raster files in the folder path
        for file in os.listdir(self.raster_fpath):
            if file.endswith(".tif"):
                # Raster file path as key for the bounds dictionary
                fpath = os.path.join(self.raster_fpath, file)
                raster = rxr.open_rasterio(fpath)
                # Reprojects raster to EPSG:3857
                reproj_raster = raster.rio.reproject(3857)
                bbox = reproj_raster.rio.bounds()
                # Shapely box object as value for bounds dictionary
                bbox = box(bbox[0], bbox[3], bbox[2], bbox[1])
                bounds[fpath] = bbox
        return bounds
    
    def _append_raster_fname(self, gdf_dict, bounds_dict):
        """Function appends raster file path if a point is within a raster bounds
        
        Parameters
        ----------
        gdf_dict: dict
            GeoDataFrame dictionary of nodes and edges of queried place
                keys: 'nodes', 'edges'
                values: nodes_gdf, edges_gdf
        bounds_dict: dict
            Bounding box dictionary of rasters file paths and raster bounds

        Returns
        ----------
        node_gdf: GeoDataFrame
            Creates a GeoDataFrame with column 'fname'
            'fname' stores raster file paths for points if within bounds
        """
        try:
            node_gdf = gdf_dict["nodes"]
            node_gdf["fname"] = None
            for file_name, polygon in bounds_dict.items():
                within_polygon = node_gdf["geometry"].within(polygon)
                node_gdf.loc[within_polygon, "fname"] = file_name
            if None in list(node_gdf["fname"].unique()):
                none_gdf = node_gdf[node_gdf["fname"].isnull()]
                osmid = list(none_gdf["osmid"])
                raise AttributeError(f"Cannot perform elevation bind. Raster bounds not found for {len(osmid)} points for coordinates range {none_gdf['x'].min(), none_gdf['y'].min(), none_gdf['x'].max(), none_gdf['y'].max()}")
            return node_gdf
        except AttributeError as e:
            print(f"{str(e)}")

    def _bind_elevation_to_nodes(self, gdf_dict, bounds_dict):
        """Function to bind elevation to nodes geodataframe

        Parameters
        ----------
        gdf_dict: dict
            GeoDataFrame dictionary of nodes and edges of queried place
                keys: 'nodes', 'edges'
                values: nodes_gdf, edges_gdf
        bounds_dict: dict
            Bounding box dictionary of rasters file paths and raster bounds

        Returns
        ----------
        node_gdf: GeoDataFrame
            Output GeoDataFrame consists of 'elev' column which extracts elevation
            from raster and appends it to corresponding node in meters (m)
        """
        node_gdf = self._append_raster_fname(gdf_dict, bounds_dict)
        node_gdf["elev"] = None
        unq_list = list(node_gdf["fname"].unique())
        raster_dict = {}
        for raster_file in unq_list:
            dst = rxr.open_rasterio(raster_file)
            reproj_dst = dst.rio.reproject(3857)
            raster_dict[raster_file] = reproj_dst
        for index, row in node_gdf.iterrows():
            lon, lat = row["geometry"].x, row["geometry"].y
            filename = row["fname"]
            raster = raster_dict[filename]
            elevation = raster.sel(x=lon, y=lat, method="nearest").values
            node_gdf.at[index, "elev"] = elevation[0]
        node_gdf = node_gdf.drop(labels="fname", axis=1)
        return node_gdf
    
    def bind_elevation_to_network(self):
        """Function to bind elevation to node and edge network"""
        print("Executing elevation binding process........")
        fpath = self._save_geopackage()
        gdf_dict = self._read_geopackage(fpath)
        bounds_dict = self._extract_raster_bounds()
        edge_gdf = gdf_dict["edges"]
        node_gdf = self._bind_elevation_to_nodes(gdf_dict, bounds_dict)
        merged_gdf = gpd.GeoDataFrame()
        # Perform a join operation on the 'osmid' column
        merged_gdf = edge_gdf.merge(node_gdf, left_on="from", right_on="osmid", how="left")
        # Assuming 'elev' is the elevation column in node_gdf
        merged_gdf["from_elev"] = merged_gdf["elev"]
        
        col_list = list(merged_gdf.columns.values)
        col = [item for item in col_list if item.endswith("_y")]
        col_elev = [item for item in col_list if item.startswith("elev")]

        merged_gdf = merged_gdf.drop(labels=col, axis=1)
        merged_gdf = merged_gdf.drop(labels=col_elev, axis=1)
    
        rename_dict = {}
        for col in col_list:
            if col.endswith("_x"):
                rename_col = col.split("_")[0]
                rename_dict[col] = rename_col

        merged_gdf = merged_gdf.rename(columns = rename_dict)
        # Perform a join operation on the 'osmid' column
        merged_gdf = merged_gdf.merge(node_gdf, left_on="to", right_on="osmid", how="left")
        # Assuming 'elev' is the elevation column in node_gdf
        merged_gdf["to_elev"] = merged_gdf["elev"]

        col_list = list(merged_gdf.columns.values)
        col = [item for item in col_list if item.endswith("_y")]
        col_elev = [item for item in col_list if item.startswith("elev")]

        merged_gdf = merged_gdf.drop(labels=col, axis=1)
        merged_gdf = merged_gdf.drop(labels=col_elev, axis=1)

        rename_dict = {}
        for col in col_list:
            if col.endswith("_x"):
                rename_col = col.split("_")[0]
                rename_dict[col] = rename_col

        merged_gdf = merged_gdf.rename(columns = rename_dict)
        geometry = merged_gdf["geometry"]
        df = merged_gdf.drop("geometry", axis=1)
        gdf = gpd.GeoDataFrame(df, crs="EPSG:3857", geometry=geometry)
        # To avoid conversion issues created due to inconsistent dtypes
        reclass_dict = {"from_elev": float, "to_elev":float}
        gdf = gdf.astype(reclass_dict)
        gdf = gdf.to_crs(4326)
        gdf.to_file("edge_network.gpkg", driver="GPKG", layer="edges")
        node_gdf = node_gdf.astype({"elev":float})
        node_gdf = node_gdf.to_crs(4326)
        node_gdf.to_file("node_network.gpkg", driver="GPKG", layer="nodes")
        print(f"Saved edge network to file path {os.path.join(os.getcwd(), 'edge_network.gpkg')}")
        print(f"Saved edge network to file path {os.path.join(os.getcwd(), 'node_network.gpkg')}")
    
    def visualize_edges_elevation(self, gpkg_fpath, col_name, title, fname="elevation", cmap="coolwarm"):
        """Function to visualize edges elevation using input geopackage file path and saves png to directory
        
        Parameters
        ----------
        gpkg_fpath: str
            Edges geopackage file path
        col_name: str
            Name of the column to be visualized: 'from_elev' or 'to_elev'
        title: str
            Title of the edge network plot
        fname: str, optional
            Save filename of the plot without .png extension
            default: 'elevation'
        cmap: str, optional
            ColorMap diverging scheme 
            default: 'coolwarm'
        """
        if not os.path.exists(f"{gpkg_fpath}"):
            raise FileNotFoundError(f"Input gpkg file path not found in {gpkg_fpath}")
        gdf = gpd.read_file(f"{gpkg_fpath}")
        if col_name not in list(gdf.columns.values):
            raise AttributeError(f"{col_name} is not available. Available columns are: {list(gdf.column.values)}")
        # Desired figsize (width, height) in inches
        fig, ax = plt.subplots(figsize=(10, 5))
        # Plot the geodataframe
        gdf.plot(ax=ax, linewidth=0.5, column=f"{col_name}", legend=True,
                    legend_kwds={"label": "Digital Elevation (m)", "orientation": "vertical"}, 
                    cmap=cmap)
        # Set plot parameters
        ax.set_title(title)
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        # Saves figure to the directory
        plt.savefig(f"{fname}.png", bbox_inches ="tight", dpi=600)
        print(f"Plot is saved as {fname}.png at {os.getcwd()}")
        # Show the plot
        plt.show()
