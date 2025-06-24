from django.contrib.gis.db import models
from .utility import Utility
from cwageodjango.core.constants import DEFAULT_SRID


class DMA(models.Model):
    code = models.CharField(max_length=50, null=False, blank=False, db_index=True)
    name = models.CharField(max_length=255, null=False, blank=False)
    utility = models.ForeignKey(
        Utility, on_delete=models.RESTRICT, related_name="utility_dmas"
    )
    network_repr = models.JSONField(null=True)
    geometry = models.MultiPolygonField(
        spatial_index=True, null=False, blank=False, srid=DEFAULT_SRID
    )
    modified_at = models.DateTimeField(auto_now=True, null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add=True, null=False, blank=False)

    class Meta:
        ordering = ["pk"]
        unique_together = (
            "utility",
            "code",
        )

    def __str__(self):
        return self.code
