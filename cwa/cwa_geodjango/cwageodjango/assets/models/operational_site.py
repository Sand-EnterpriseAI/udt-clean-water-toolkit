from django.contrib.gis.db import models
from cwageodjango.core.constants import DEFAULT_SRID, OPERATIONAL_SITE__NAME
from cwageodjango.utilities.models import DMA


class OperationalSite(models.Model):
    tag = models.CharField(
        max_length=50, null=False, blank=False, unique=True, db_index=True
    )
    geometry = models.PointField(
        spatial_index=True, null=False, blank=False, srid=DEFAULT_SRID
    )
    geometry_4326 = models.PointField(
        spatial_index=True, null=False, blank=False, srid=4326
    )
    subtype = models.CharField(null=False, blank=False)
    dmas = models.ManyToManyField(DMA, related_name="dma_operational_sites")
    modified_at = models.DateTimeField(auto_now=True, null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add=True, null=False, blank=False)

    class Meta:
        ordering = ["pk"]

    class AssetMeta:
        asset_name = OPERATIONAL_SITE__NAME
