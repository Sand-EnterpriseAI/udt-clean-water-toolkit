import os
import geopandas as gpd
from geopandas import GeoDataFrame
from cleanwater.exceptions import LayerLoadException
from cleanwater.serializers import GeoDjangoSerializer
from .base_data_manager import BaseDataManager
from django.db.models.query import QuerySet
from networkx import Graph


class GeoDjangoDataManager(BaseDataManager, GeoDjangoSerializer):
    """Helper functions to manipulate geospatial data"""

    srid = 27700  # TODO: set default srid in config

    def gdb_zip_to_gdf_layer(self, zip_path: str, layer_name: str):
        if not os.path.exists(zip_path):
            raise Exception("gdf file not found")
        try:
            return gpd.read_file(zip_path, layer=layer_name)
        except ValueError:
            raise LayerLoadException(
                f"Layer cannot be identified with provided name: {layer_name}"
            )

    def django_queryset_to_geodataframe(
        self, qs: QuerySet, srid: int = None
    ) -> GeoDataFrame:
        # TODO: this class should probably not be instantiated here

        srid: int | None = srid or self.srid
        data: str = self.queryset_to_geojson(qs, srid)

        return gpd.read_file(data)
