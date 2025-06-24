from django.core.management.base import BaseCommand
from django.contrib.gis.gdal import DataSource
from cwageodjango.assets.models import WaterWork
from cwageodjango.utilities.models import DMA, Utility


class Command(BaseCommand):
    help = "Write Severn Trent Water Water Work layer data to sql"

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

        water_work_layer = ds[layer_index]

        new_water_works = []
        for feature in water_work_layer:
            tag = feature.get("id")
            geom = feature.geom
            geom_4326 = feature.get("wkt_geom_4326")

            if not geom_4326:
                continue

            new_water_work = WaterWork(
                tag=tag, geometry=geom.wkt, geometry_4326=geom_4326
            )
            new_water_works.append(new_water_work)

            if len(new_water_works) == 100000:
                WaterWork.objects.bulk_create(new_water_works)
                new_water_works = []

        # save the last set of data as it will probably be less than 100000
        if new_water_works:
            WaterWork.objects.bulk_create(new_water_works)

        # get the utility
        utility = Utility.objects.get(name="severn_trent_water")

        DMAThroughModel = WaterWork.dmas.through
        bulk_create_list = []
        for water_work in WaterWork.objects.filter(dmas=None).only("id", "geometry"):
            wkt = water_work.geometry.wkt

            dma_ids = DMA.objects.filter(
                geometry__intersects=wkt, utility=utility
            ).values_list("pk", flat=True)

            if not dma_ids:
                dma_ids = [DMA.objects.get(name=r"undefined", utility=utility).pk]

            bulk_create_list.extend(
                [
                    DMAThroughModel(waterwork_id=water_work.pk, dma_id=dma_id)
                    for dma_id in dma_ids
                ]
            )

            if len(bulk_create_list) == 100000:
                DMAThroughModel.objects.bulk_create(bulk_create_list)
                bulk_create_list = []

        # save the last set of data as it will probably be less than 100000
        if bulk_create_list:
            DMAThroughModel.objects.bulk_create(bulk_create_list)
