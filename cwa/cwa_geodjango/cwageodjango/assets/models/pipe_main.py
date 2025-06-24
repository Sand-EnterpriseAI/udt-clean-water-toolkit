from django.contrib.gis.db import models
from cwageodjango.utilities.models import DMA
from cwageodjango.core.constants import DEFAULT_SRID, PIPE_MAIN__NAME


class PipeMain(models.Model):
    tag = models.CharField(null=False, blank=False, unique=True, db_index=True)
    geometry = models.LineStringField(
        spatial_index=True, null=False, blank=False, srid=DEFAULT_SRID
    )
    dmas = models.ManyToManyField(DMA, related_name="dma_pipe_mains")
    geometry_4326 = models.LineStringField(
        spatial_index=True, null=False, blank=False, srid=4326
    )
    material = models.CharField(max_length=255, null=False, blank=False, db_index=True)
    pipe_type = models.CharField(max_length=255, null=False, blank=False, db_index=True)
    modified_at = models.DateTimeField(auto_now=True, null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add=True, null=False, blank=False)
    diameter = models.FloatField(null=False, blank=False)

    class Meta:
        ordering = ["pk"]

    class AssetMeta:
        asset_name = PIPE_MAIN__NAME
