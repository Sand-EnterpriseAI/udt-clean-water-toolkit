import pytest
import joblib
from sqids import Sqids
from django.contrib.gis.geos import GEOSGeometry

# from shapely import wkt
import pandas as pd
import geopandas as gpd
from .data.gis_to_graph_data import (
    PIPE_JUNCTIONS,
    POINT_ASSETS,
    JUNCTIONS_WITH_POSITIONS,
)
from cleanwater.transform.gis_to_graph import GisToGraph


BASE_PIPE_DATA_FILE_PATH = "./data/base_pipe_data.csv"

sqids = Sqids(alphabet="86QDHYuRxW3OfckshvCUtngEKamBbrPGNiM9LwjFypVq1Ze0TSIl4Jz5X2dA7o")

SRID = 27700


@pytest.mark.skip(reason="This function received the test input data.")
def get_pipe_data():

    gdf = gpd.read_file(BASE_PIPE_DATA_FILE_PATH)
    gdf.crs = "epsg:27700"
    base_pipe = gdf.to_dict("records")[0]

    base_pipe["geometry"] = GEOSGeometry(base_pipe["wkt"], SRID)

    return base_pipe


# content of test_class.py
class TestGisToGraph:

    def test_get_junction_connections_on_pipe(self):
        base_pipe = get_pipe_data()

        gis_to_graph = GisToGraph(SRID, sqids)
        junctions_with_positions = gis_to_graph._get_connections_points_on_pipe(
            base_pipe, PIPE_JUNCTIONS
        )

        del junctions_with_positions[0]["intersection_point_geometry"]
        del junctions_with_positions[1]["intersection_point_geometry"]
        assert junctions_with_positions == JUNCTIONS_WITH_POSITIONS

    # This function needs to be modified to so that it's done in the same way as the one above
    # def test_get_assets_connections_on_pipe(self):
    #     expected_point_assets_with_positions_hash = "0a7fdad5f5ecfb3571f9755d57e965bd"

    #     base_pipes = get_pipe_data()

    #     gis_to_graph = GisToGraph(SRID, sqids)

    #     point_assets_with_positions = gis_to_graph._get_connections_points_on_pipe(
    #         base_pipe, point_assets
    #     )

    #     assert (
    #         joblib.hash(point_assets_with_positions)
    #         == expected_point_assets_with_positions_hash
    #     )
