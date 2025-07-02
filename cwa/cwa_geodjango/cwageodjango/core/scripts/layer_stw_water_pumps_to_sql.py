from django.core.management.base import BaseCommand
from django.contrib.gis.gdal import DataSource
from cwageodjango.assets.models import WaterPump
from cwageodjango.utilities.models import DMA, Utility


class Command(BaseCommand):
    help = "Write Severn Trent Water Water Pump layer data to sql"

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

        water_pump_layer = ds[layer_index]

        new_water_pumps = []
        for feature in water_pump_layer:
            gid = feature.get("tag")
            geom = feature.geom
            geom_4326 = feature.get("wkt_geom_4326")

            new_water_pump = WaterPump(
                tag=gid, geometry=geom.wkt, geometry_4326=geom_4326
            )
            new_water_pumps.append(new_water_pump)

            if len(new_water_pumps) == 100000:
                WaterPump.objects.bulk_create(new_water_pumps)
                new_water_pumps = []

        # save the last set of data as it will probably be less than 100000
        if new_water_pumps:
            WaterPump.objects.bulk_create(new_water_pumps)

        # get the utility
        utility = Utility.objects.get(name="severn_trent_water")

        DMAThroughModel = WaterPump.dmas.through
        bulk_create_list = []
        for water_pump in WaterPump.objects.filter(dmas=None).only("id", "geometry"):
            wkt = water_pump.geometry.wkt

            dma_ids = DMA.objects.filter(
                geometry__intersects=wkt, utility=utility
            ).values_list("pk", flat=True)

            if not dma_ids:
                dma_ids = [DMA.objects.get(name=r"undefined", utility=utility).pk]

            bulk_create_list.extend(
                [
                    DMAThroughModel(waterpump_id=water_pump.pk, dma_id=dma_id)
                    for dma_id in dma_ids
                ]
            )

            if len(bulk_create_list) == 100000:
                DMAThroughModel.objects.bulk_create(bulk_create_list)
                bulk_create_list = []

        # save the last set of data as it will probably be less than 100000
        if bulk_create_list:
            DMAThroughModel.objects.bulk_create(bulk_create_list)
