import json
from django.db.models.query import QuerySet


class GeoDjangoSerializer:
    """Custom serializers from GeoDjango."""

    srid = 27700  # TODO: set default srid in config

    def queryset_to_geojson(self, qs: QuerySet, srid: int = None) -> str:
        """GeoJSON serialization for properties and geometry
        fields directly queried from the db without modification.
        No iteration."""

        srid: int | None = srid or self.srid

        geo_data: dict = {
            "type": "FeatureCollection",
            "crs": {"type": "name", "properties": {"name": f"EPSG:{srid}"}},
            "features": list(qs),
        }
        return json.dumps(geo_data)

    def queryset_to_geojson2(self, qs: QuerySet, srid: int = None) -> str:
        """GeoJSON serialization for properties and geometry
        fields."""

        srid: int | None = srid or self.srid

        geo_data: dict = {
            "type": "FeatureCollection",
            "crs": {"type": "name", "properties": {"name": f"EPSG:{srid}"}},
            "features": [
                {"properties": i["properties"], "geometry": json.loads(i["geometry"])}
                for i in qs
            ],
        }
        return json.dumps(geo_data)
