from django.core.management.base import BaseCommand
from django.contrib.gis.gdal import DataSource
from cwageodjango.assets.models import Meter
from cwageodjango.utilities.models import DMA


class Command(BaseCommand):
    help = "Write Thames Water meter layer data to sql"

    def add_arguments(self, parser):
        parser.add_argument("-f", "--file", type=str, help="Path to valid datasource")
        parser.add_argument("-x", "--index", type=int, help="Layer index")

    def handle(self, *args, **kwargs):
        ds_path = kwargs.get("file")
        layer_index = kwargs.get("index")

        ds = DataSource(ds_path)

        print(
            f"""There are {ds[layer_index].num_feat} features.
Large numbers of features will take a long time to save."""
        )

        meter_layer = ds[layer_index]

        new_meters = []
        for feature in meter_layer:
            tag = feature.get("tag")
            geom = feature.geom
            geom_4326 = feature.get("wkt_geom_4326")

            new_meter = Meter(tag=tag, geometry=geom.wkt, geometry_4326=geom_4326)
            new_meters.append(new_meter)

            if len(new_meters) == 100000:
                Meter.objects.bulk_create(new_meters)
                new_meters = []

        # save the last set of data as it will probably be less than 100000
        if new_meters:
            Meter.objects.bulk_create(new_meters)

        DMAThroughModel = Meter.dmas.through
        bulk_create_list = []
        for meter in Meter.objects.only("id", "geometry"):
            wkt = meter.geometry.wkt

            dma_ids = DMA.objects.filter(
                geometry__intersects=wkt, utility__name="severn_trent_water"
            ).values_list("pk", flat=True)

            if not dma_ids:
                dma_ids = [
                    DMA.objects.get(
                        code=r"undefined", utility__name="severn_trent_water"
                    ).pk
                ]

            bulk_create_list.extend(
                [
                    DMAThroughModel(meter_id=meter.pk, dma_id=dma_id)
                    for dma_id in dma_ids
                ]
            )

            if len(bulk_create_list) == 100000:
                DMAThroughModel.objects.bulk_create(bulk_create_list)
                bulk_create_list = []

        # save the last set of data as it will probably be less than 100000
        if bulk_create_list:
            DMAThroughModel.objects.bulk_create(bulk_create_list)
