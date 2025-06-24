from django.db.models import Value, JSONField, OuterRef
from django.db.models.functions import JSONObject
from django.contrib.postgres.aggregates import ArrayAgg
from django.contrib.postgres.expressions import ArraySubquery
from django.db.models.query import QuerySet
from django.contrib.gis.measure import D
from django.contrib.gis.db.models.functions import AsGeoJSON, Cast, Length, AsWKT
from cleanwater.data_managers import GeoDjangoDataManager
from cwageodjango.core.db.models.functions import LineStartPoint, LineEndPoint


class PipeAndAssets(GeoDjangoDataManager):
    """Convert pipe_mains data to a Queryset or GeoJSON."""

    WITHIN_DISTANCE = 0.1
    default_properties = [
        "id",
        "tag",
    ]  # should not include the geometry column as per convention

    def generate_dwithin_subquery(
        self,
        pipe_model,
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
            pipe_model.objects.all(), "tag", geometry_field=geometry_field
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

        ### we use dwithing with zero distance as opposed to touches as postgis
        ### handles touches in a different way leading to unexpected results
        subquery_line_start = (
            qs.exclude(pk=OuterRef("id"))
            .filter(geometry__dwithin=(OuterRef("start_point_geom"), D(m=0)))
            .values(json=JSONObject(tags=ArrayAgg("tag"), ids=ArrayAgg("id")))
            .order_by("pk")
        )

        subquery_line_end = (
            qs.exclude(pk=OuterRef("id"))
            .filter(geometry__dwithin=(OuterRef("end_point_geom"), D(m=0)))
            .values(json=JSONObject(tags=ArrayAgg("tag"), ids=ArrayAgg("id")))
            .order_by("pk")
        )

        return subquery_line_start, subquery_line_end

    @staticmethod
    def get_asset_json_fields(asset_model, geometry_field="geometry"):
        """Overwrite the fields retrieved by the subqueries or
        the SQL functions used to retrieve them.

        Params:
              geometry_field (str, optional, defaut="geometry")

        Returns:
              json object for use in subquery
        """

        model_fields = {}
        for f in asset_model._meta.get_fields(include_parents=False):
            model_fields[f.name] = f.name

        return {
            **model_fields,
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

    def _generate_mains_subqueries(self, pipe_model):
        pm_qs = pipe_model.objects.all().order_by("pk")

        json_fields = self.get_pipe_json_fields()

        subquery_pm_junctions = self.generate_touches_subquery(pm_qs, json_fields)

        termini_subqueries = self.generate_termini_subqueries(pm_qs)

        subqueries = {
            "pipemain_junctions": ArraySubquery(subquery_pm_junctions),
            "line_start_intersections": ArraySubquery(termini_subqueries[0]),
            "line_end_intersections": ArraySubquery(termini_subqueries[1]),
        }

        return subqueries

    def _generate_asset_subqueries(self, pipe_model, point_assets):

        subqueries = {}
        for annotation, asset_model in point_assets.items():
            json_fields = self.get_asset_json_fields(asset_model)

            subquery = self.generate_dwithin_subquery(
                pipe_model, asset_model.objects.all(), json_fields
            )

            subqueries[annotation] = ArraySubquery(subquery)

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

    def get_pipe_and_point_relations(self, pipe_model, point_assets, filters):
        mains_intersection_subqueries = self._generate_mains_subqueries(pipe_model)
        asset_subqueries = self._generate_asset_subqueries(pipe_model, point_assets)

        # https://stackoverflow.com/questions/51102389/django-return-array-in-subquery
        qs = pipe_model.objects.prefetch_related("dmas", "dmas__utility")

        qs = self._filter_by_utility(qs, filters)
        qs = self._filter_by_dma(qs, filters)

        qs = qs.annotate(
            asset_name=Value(pipe_model.AssetMeta.asset_name),
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

    def get_mains_count(self, pipe_model, filters):

        qs = pipe_model.objects.prefetch_related("dmas", "dmas__utility")

        qs = self._filter_by_utility(qs, filters)
        qs = self._filter_by_dma(qs, filters)
        return qs.count()

    def get_pipe_mains_pks(self, pipe_model, filters):
        qs = pipe_model.objects.prefetch_related("dmas", "dmas__utility")

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
