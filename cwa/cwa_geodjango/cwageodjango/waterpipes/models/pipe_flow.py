from django.contrib.gis.db import models
from cwageodjango.assets.models import PipeMain


class PipeFlow(models.Model):
    pipe_main = models.OneToOneField(
        PipeMain,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="pipe_main_flows",
    )
    flow_data = models.JSONField()
