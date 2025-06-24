from geopandas import GeoDataFrame
from django.db.models.query import QuerySet
from networkx import Graph
from ..data_managers.network_data_manager import NetworkDataManager

# from ..config.settings import DEFAULT_SRID


class NetworkController(NetworkDataManager):
    """Create a graph network of assets from a geospatial
    network of assets"""

    def __init__(self, srid=None):
        self.srid = srid  # or DEFAULT_SRID

    def create_pipes_network(
        self, datasource: QuerySet | GeoDataFrame, srid: int = None
    ) -> Graph:
        """
        Convert a pipe gis object to a networkx graph

        Params:
            - datasource (required): geodjango queryset, geojson,
        geopandas dataframe"""
        srid: int | None = srid or self.srid
        if isinstance(datasource, QuerySet):
            gdf: GeoDataFrame = self.django_queryset_to_geodataframe(
                datasource, srid=None
            )
            return self.gdf_lines_to_nx_graph(gdf)
        elif isinstance(datasource, GeoDataFrame):
            return self.gdf_lines_to_nx_graph(datasource)
