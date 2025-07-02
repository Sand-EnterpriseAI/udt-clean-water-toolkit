# NOTE: This script is an example of how to perform a spatial join in a Databricks environment.
# It relies on Databricks-specific features (like `spark` and `dbutils`) and will not run as a standalone script.
# For a standalone example that works with local data, please see `spatial_join_points.ipynb`.

point_layers = [
    "wNetworkMeter",
    "wChamber",
    "wNetworkOptValve",
    "wOperationalSite",
    "wPressureContValve",
    "wPressureFitting",
    "wHydrant",
]

# Point layers which require a spatial join with tolerance, tolerance in meters
# Needs to be small to limit incorrect matches, but large enough to match assets
tolerances = {"wOperationalSite": 1, "wChamber": 0.5}

# COMMAND ----------

# MAGIC %md # Imports

# COMMAND ----------

import numpy as np
import pandas as pd
import geopandas as gpd
import fiona

# import pyspark.sql.functions as F
import matplotlib.pyplot as plt

# from shapely import wkt
# from shapely.geometry import Point, LineString
# from shapely.ops import nearest_points
# import mlflow

# from data_factory.databricks.Metastore import Metastore
# from data_factory.AnalyticalTwin import twin

# COMMAND ----------


def save_ehms(table, dataframe, mode="overwrite", debug=False):
    try:
        schema_name, table_name = (table).split(".")
        if debug:
            table_name += "_ref"
        properties = {}
        metastore = Metastore()
        metastore.save_table(
            dbutils, schema_name, table_name, dataframe, properties, mode=mode
        )

    except Exception as e:
        print(e.args)


def read_table_pandas(table_name, debug=False):
    if debug:
        table_name += "_ref"
    return spark.read.table(table_name).toPandas()


# COMMAND ----------

# TODO: Replace with path to your own data. A sample is included in the /data directory.
shape_file = "../../data/sample_data.gdb.zip"
gdf_mains = gpd.read_file(shape_file, layer="wTrunkMain")
gdf_mains = gdf_mains[["GISID", "geometry"]]
gdf_mains.set_index("GISID", inplace=True)
gdf_mains.dropna(subset=["geometry"], inplace=True)

# COMMAND ----------

print(gdf_mains.shape)

# COMMAND ----------

# MAGIC %md # Geospatial join of point layers onto lines

# COMMAND ----------


def antijoin_points(left_on, right_on):
    tmp = pd.merge(
        left=left_on,
        right=right_on.set_index("Point"),
        how="left",
        left_index=True,
        right_on="Point",
        indicator=True,
    )
    return tmp[tmp["_merge"] == "left_only"].drop(columns="_merge")


def parse_point(record: str):
    # Conversion of string to Point object
    pieces = record.split()
    x = float(pieces[1].lstrip("("))
    y = float(pieces[2].rstrip(")"))
    point = Point(x, y)
    return point


def join_points_on_lines(
    points: gpd.GeoDataFrame, lines: gpd.GeoDataFrame, tol: float = None
) -> gpd.GeoDataFrame:
    # Spatial join of points to lines

    p = points[["geometry"]]
    l = lines[["geometry"]]

    if tol:
        # Create circles with radius tol around points
        p["geometry"] = gpd.GeoSeries(p["geometry"]).buffer(tol)
    # Spatial join of points (circles if tol) to lines
    df = gpd.sjoin(p, l, how="inner")
    df.reset_index(inplace=True)
    df.rename(
        columns={
            "index": "Point",
            "index_left": "Point",
            "GISID": "Point",
            "index_right": "Line",
        },
        inplace=True,
    )
    df = df[["Point", "Line"]]

    if tol:
        # Removal of points which match to multiple lines when using tolerance
        # we should experiment with not doing this and see the result
        df["count"] = df.groupby("Point")["Point"].transform("count")
        df = df[df["count"] == 1].drop(columns="count")

    return df


def join_points_with_tolerance(
    layer: str, points: gpd.GeoDataFrame, lines: gpd.GeoDataFrame, tol: float
) -> gpd.GeoDataFrame:
    df = join_points_on_lines(points, lines, tol)

    # Update gis table
    layer_df = read_table_pandas("dpsn_twin.gis_" + layer.lower())
    tmp = df.merge(layer_df, left_on="Point", right_on="GISID")
    tmp = tmp.merge(gdf_mains, left_on="Line", right_on="GISID")

    new_points = []
    for point, line in zip(tmp["geometry_x"], tmp["geometry_y"]):
        p = parse_point(point)
        new_points.append(nearest_points(line, p)[0])

    tmp["geometry"] = new_points
    tmp["SHAPEX"] = [i.x for i in new_points]
    tmp["SHAPEY"] = [i.y for i in new_points]
    tmp = tmp.drop(columns=["geometry_x", "geometry_y", "Point", "Line"])

    # Creating separate tol mapping
    layer_df = layer_df[~layer_df["GISID"].isin(list(tmp["GISID"]))]
    layer_df = layer_df.append(tmp)
    layer_df["geometry"] = layer_df["geometry"].astype(str)

    pdf = spark.createDataFrame(layer_df)
    save_ehms("dpsn_twin.gis_" + layer.lower() + "_tol", pdf)
    print(layer + " table updated")

    return df


# COMMAND ----------

# Read each layer and do the spatial join
# Record each match in the map point line table
# Operational sites get an additional spatial join with tolerance step

write_mode = "overwrite"
for layer in point_layers:
    print(layer)
    gdf = gpd.read_file(shape_file, layer=layer)
    gdf["layer"] = layer
    gdf.set_index("GISID", inplace=True)
    gdf.dropna(subset=["geometry"], inplace=True)
    print("...read in {:d} records".format(gdf.shape[0]))

    # wkt loads was giving me an issue trying to load the geometry column from databricks table
    # so a current workaround is to still read the gdb, but join on index, this
    # allows us to still contain the filtering to the 001 notebook
    import pdb

    pdb.set_trace()
    pdf = read_table_pandas("dpsn_twin.gis_" + layer.lower())
    gdf = gdf[gdf.index.isin(list(pdf["GISID"]))]

    map_point_line = join_points_on_lines(gdf, gdf_mains, None)

    if tolerances.get(layer):
        print("before tol ", map_point_line.shape)

        gdf = gdf[~gdf.index.isin(list(map_point_line["Point"]))]

        print("Finding points within tolerance of lines")
        gdf_tol = join_points_with_tolerance(
            layer, gdf, gdf_mains, tol=tolerances.get(layer)
        )

        print("gdf_tol", gdf_tol.shape)
        gdf_tol["Point"] = gdf_tol["Point"].astype(int)
        gdf_tol["Line"] = gdf_tol["Line"].astype(int)
        map_point_line = map_point_line.append(gdf_tol)

    print("found {} intersections".format(map_point_line.shape[0]))
    map_point_line["layer"] = layer

    if save:
        pdf = spark.createDataFrame(
            map_point_line, schema="Point long, Line long, layer string"
        )
        save_ehms(map_point_line_table, pdf, mode=write_mode)
        write_mode = "append"
