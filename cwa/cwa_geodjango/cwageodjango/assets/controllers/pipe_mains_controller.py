from django.db.models import Value, JSONField, OuterRef
from django.db.models.functions import JSONObject
from django.contrib.postgres.aggregates import ArrayAgg
from django.contrib.postgres.expressions import ArraySubquery
from django.db.models.query import QuerySet
from django.contrib.gis.measure import D
from django.contrib.gis.db.models.functions import (
    AsGeoJSON,
    Cast,
    Length,
    AsWKT
)
from cleanwater.data_managers import GeoDjangoDataManager
from cwageodjango.assets.models import *
from cwageodjango.core.db.models.functions import LineStartPoint, LineEndPoint


class PipeMainsController(GeoDjangoDataManager):
    """Convert pipe_mains data to a Queryset or GeoJSON."""

    WITHIN_DISTANCE = 0.1
    default_properties = [
        "id",
        "tag",
    ]  # should not include the geometry column as per convention
    model = PipeMain

    def generate_dwithin_subquery(
        self,
        qs,
        json_fields,
        geometry_field="geometry",
        extra_json_fields={},
    ):
        """
        Generates a subquery where the inner query is filtered if its geometery object
        is within the geometry of the outer query.

        Params:
              qs (Queryset, required)
              json_fields (dict, required) - A dictionary of model fields to return
              geometry_field (str, optional, default="geometry") - The field name of the outer geometry object

        Returns:
              subquery (Queryset)

        """

        pm_inner_subquery = self._generate_dwithin_inner_subquery(
            self.model.objects.all(), "tag", geometry_field=geometry_field
        )

        subquery = (
            qs.filter(
                geometry__dwithin=(OuterRef(geometry_field), D(m=self.WITHIN_DISTANCE))
            )
            .values(
                json=JSONObject(
                    **json_fields,
                    **extra_json_fields,
                    pm_touches_ids=pm_inner_subquery,
                    asset_name=Value(qs.model.AssetMeta.asset_name),
                    asset_label=Value(qs.model.__name__)
                )
            )
            .order_by("pk")
        )

        return subquery

    def _generate_dwithin_inner_subquery(self, qs, field, geometry_field="geometry"):
        inner_subquery = (
            qs.filter(
                geometry__dwithin=(OuterRef(geometry_field), D(m=self.WITHIN_DISTANCE))
            )
            .values_list(field, flat=True)
            .order_by("pk")
        )

        return ArraySubquery(inner_subquery)

    @staticmethod
    def generate_touches_subquery(qs, json_fields, geometry_field="geometry"):
        """
        Generates a subquery where the inner query is filtered if its geometery object
        touches the geometry of the outer query.

        Params:
               qs (Queryset, required)
               json_fields (dict, required) - A dictionary of model fields to return
               geometry_field (str, optional, default="geometry") - The field name of the outer geometry object

        Returns:
              subquery (Queryset)

        """

        subquery = (
            qs.filter(geometry__touches=OuterRef(geometry_field))
            .values(
                json=JSONObject(
                    **json_fields,
                    asset_name=Value(qs.model.AssetMeta.asset_name),
                    asset_label=Value(qs.model.__name__)
                ),
            )
            .order_by("pk")
        )

        return subquery

    def generate_termini_subqueries(self, qs):

        subquery_line_start = (
            qs.exclude(pk=OuterRef("id"))
            .filter(geometry__touches=OuterRef("start_point_geom"))
            .values(json=JSONObject(tags=ArrayAgg("tag"), ids=ArrayAgg("id")))
            .order_by("pk")
        )

        subquery_line_end = (
            qs.exclude(pk=OuterRef("id"))
            .filter(geometry__touches=OuterRef("end_point_geom"))
            .values(json=JSONObject(tags=ArrayAgg("tag"), ids=ArrayAgg("id")))
            .order_by("pk")
        )

        return subquery_line_start, subquery_line_end

    @staticmethod
    def get_asset_json_fields(geometry_field="geometry"):
        """Overwrite the fields retrieved by the subqueries or
        the SQL functions used to retrieve them.

        Params:
              geometry_field (str, optional, defaut="geometry")

        Returns:
              json object for use in subquery
        """

        return {
            "id": "id",
            "tag": "tag",
            "geometry": geometry_field,
            "wkt": AsWKT(geometry_field),
            "dma_ids": ArrayAgg("dmas"),
            "dma_codes": ArrayAgg("dmas__code"),
            "dma_names": ArrayAgg("dmas__name"),
            "utilities": ArrayAgg("dmas__utility__name"),
        }

    @staticmethod
    def get_pipe_json_fields():
        """Overwrite the fields retrieved by the subqueries or
        the SQL functions used to retrieve them.

        Params:
              None

        Returns:
              json object for use in subquery
        """

        return {
            "id": "id",
            "tag": "tag",
            "pipe_type": "pipe_type",
            "geometry": "geometry",
            "wkt": AsWKT("geometry"),
            "material": "material",
            "diameter": "diameter",
            "start_point_geom": LineStartPoint("geometry"),
            "end_point_geom": LineEndPoint("geometry"),
            "dma_ids": ArrayAgg("dmas"),
            "dma_codes": ArrayAgg("dmas__code"),
            "dma_names": ArrayAgg("dmas__name"),
            "utilities": ArrayAgg("dmas__utility__name"),
        }

    def _generate_mains_subqueries(self):
        pm_qs = self.model.objects.all().order_by("pk")

        json_fields = self.get_pipe_json_fields()

        subquery_pm_junctions = self.generate_touches_subquery(pm_qs, json_fields)

        termini_subqueries = self.generate_termini_subqueries(pm_qs)

        subqueries = {
            "pipemain_junctions": ArraySubquery(subquery_pm_junctions),
            "line_start_intersections": ArraySubquery(termini_subqueries[0]),
            "line_end_intersections": ArraySubquery(termini_subqueries[1]),
        }

        return subqueries

    def _generate_asset_subqueries(self):
        json_fields = self.get_asset_json_fields()

        # This section is deliberately left verbose for clarity
        subquery3 = self.generate_dwithin_subquery(Logger.objects.all(), json_fields)

        subquery4 = self.generate_dwithin_subquery(
            Hydrant.objects.all(),
            json_fields,
            extra_json_fields={"acoustic_logger": "acoustic_logger"},
        )

        subquery5 = self.generate_dwithin_subquery(
            PressureFitting.objects.all(),
            json_fields,
            extra_json_fields={"subtype": "subtype"},
        )

        subquery6 = self.generate_dwithin_subquery(
            PressureControlValve.objects.all(),
            json_fields,
            extra_json_fields={"subtype": "subtype"},
        )

        subquery7 = self.generate_dwithin_subquery(
            NetworkMeter.objects.all(),
            json_fields,
            extra_json_fields={"subtype": "subtype"},
        )

        subquery8 = self.generate_dwithin_subquery(Chamber.objects.all(), json_fields)

        subquery9 = self.generate_dwithin_subquery(
            OperationalSite.objects.all(),
            json_fields,
            extra_json_fields={"subtype": "subtype"},
        )

        subquery10 = self.generate_dwithin_subquery(
            NetworkOptValve.objects.all(),
            json_fields,
            extra_json_fields={"acoustic_logger": "acoustic_logger"},
        )

        subquery11 = self.generate_dwithin_subquery(
            ConnectionMeter.objects.all(),
            json_fields,
        )

        subquery12 = self.generate_dwithin_subquery(
            ConsumptionMeter.objects.all(),
            json_fields,
        )

        subquery13 = self.generate_dwithin_subquery(
            IsolationValve.objects.all(),
            json_fields,
        )

        subquery14 = self.generate_dwithin_subquery(
            BulkMeter.objects.all(),
            json_fields,
        )

        subqueries = {
            "logger_data": ArraySubquery(subquery3),
            "hydrant_data": ArraySubquery(subquery4),
            "pressure_fitting_data": ArraySubquery(subquery5),
            "pressure_valve_data": ArraySubquery(subquery6),
            "network_meter_data": ArraySubquery(subquery7),
            "chamber_data": ArraySubquery(subquery8),
            "operational_site_data": ArraySubquery(subquery9),
            "network_opt_valve_data": ArraySubquery(subquery10),
            "connection_meter_data": ArraySubquery(subquery11),
            "consumption_meter_data": ArraySubquery(subquery12),
            "isolation_valve_data": ArraySubquery(subquery13),
            "bulk_meter_data": ArraySubquery(subquery14),
        }
        return subqueries

    @staticmethod
    def _filter_by_utility(qs, filters):
        utility_names = filters.get("utility_names")

        if not utility_names:
            return qs

        return qs.filter(dmas__utility__name__in=utility_names)

    @staticmethod
    def _filter_by_dma(qs, filters):
        dma_codes = filters.get("dma_codes")

        if not dma_codes:
            return qs

        return qs.filter(dmas__code__in=dma_codes)

    def get_pipe_point_relation_queryset(self, filters):
        mains_intersection_subqueries = self._generate_mains_subqueries()
        asset_subqueries = self._generate_asset_subqueries()

        # https://stackoverflow.com/questions/51102389/django-return-array-in-subquery
        qs = self.model.objects.prefetch_related("dmas", "dmas__utility")

        qs = self._filter_by_utility(qs, filters)
        qs = self._filter_by_dma(qs, filters)

        qs = qs.annotate(
            asset_name=Value(self.model.AssetMeta.asset_name),
            asset_label=Value(qs.model.__name__),
            pipe_length=Length("geometry"),
            wkt=AsWKT("geometry"),
            dma_ids=ArrayAgg("dmas"),
            dma_codes=ArrayAgg("dmas__code"),
            dma_names=ArrayAgg("dmas__name"),
            start_point_geom=LineStartPoint("geometry"),
            end_point_geom=LineEndPoint("geometry"),
            utility_names=ArrayAgg("dmas__utility__name"),
        )

        qs = qs.annotate(**mains_intersection_subqueries, **asset_subqueries).order_by(
            "pk"
        )

        return qs

    def get_mains_count(self, filters):

        qs = self.model.objects.prefetch_related("dmas", "dmas__utility")

        qs = self._filter_by_utility(qs, filters)
        qs = self._filter_by_dma(qs, filters)
        return qs.count()

    def get_mains_pks(self, filters):
        qs = self.model.objects.prefetch_related("dmas", "dmas__utility")

        qs = self._filter_by_utility(qs, filters)
        qs = self._filter_by_dma(qs, filters)
        return list(qs.values_list("pk", flat=True).order_by("pk"))

    # Refs on how the GeoJSON is constructed.
    # AsGeoJson query combined with json to build object
    # https://docs.djangoproject.com/en/5.0/ref/contrib/postgres/expressions/
    # https://postgis.net/docs/ST_AsGeoJSON.html
    # https://dakdeniz.medium.com/increase-django-geojson-serialization-performance-7cd8cb66e366
    def get_geometry_queryset(self, properties=None) -> QuerySet:
        properties = properties or self.default_properties
        properties = set(properties)
        json_properties = dict(zip(properties, properties))

        qs: QuerySet = (
            self.model.objects.values(*properties)
            .annotate(
                geojson=JSONObject(
                    properties=JSONObject(**json_properties),
                    type=Value("Feature"),
                    geometry=Cast(
                        AsGeoJSON("geometry", crs=True),
                        output_field=JSONField(),
                    ),
                ),
            )
            .values_list("geojson", flat=True)
        )
        return qs

    def mains_to_geojson(self, properties=None):
        """Serialization of db data to GeoJSON.

        Faster (with bigger datasets) serialization into geoson.

        Params:
                properties: list (optional). A list of model fields
        Returns:
                geoJSON: geoJSON object of DistributionMains
        """

        qs = self.get_geometry_queryset(properties)
        return self.queryset_to_geojson(qs)

    def mains_to_geojson2(self, properties=None):
        """Faster (with bigger datasets) serialization into geoson.

        Params:
                properties: list (optional). A list of model fields
        Returns:
                geoJSON: geoJSON object of Mains
        """

        qs = self.get_geometry_queryset(properties)
        return self.queryset_to_geojson(qs)

    def mains_to_geodataframe(self, properties=None):
        """Serialization of db data to GeoJSON.

        Faster (with bigger datasets) serialization into geoson.

        Params:
                properties: list (optional). A list of model fields
        Returns:
                geoJSON: geoJSON object of Mains
        """

        qs = self.get_geometry_queryset(properties)
        return self.queryset_to_geodataframe(qs)
