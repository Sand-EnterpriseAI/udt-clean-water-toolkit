from django.contrib.gis.db import models
from cwageodjango.utilities.models import DMA
from cwageodjango.core.constants import DEFAULT_SRID
from cwageodjango.assets.constants import WATER_WORK__NAME


class WaterWork(models.Model):
    tag = models.CharField(
        max_length=50, null=False, blank=False, unique=True, db_index=True
    )
    geometry = models.PointField(
        spatial_index=True, null=False, blank=False, srid=DEFAULT_SRID
    )
    geometry_4326 = models.PointField(
        spatial_index=True, null=False, blank=False, srid=4326
    )
    dmas = models.ManyToManyField(DMA, related_name="dma_water_works")
    modified_at = models.DateTimeField(auto_now=True, null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add=True, null=False, blank=False)

    class Meta:
        ordering = ["pk"]

    class AssetMeta:
        asset_name = WATER_WORK__NAME
