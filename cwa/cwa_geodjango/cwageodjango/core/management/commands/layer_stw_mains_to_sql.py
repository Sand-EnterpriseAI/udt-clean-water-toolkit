from django.core.management.base import BaseCommand
from django.contrib.gis.gdal import DataSource
from cwageodjango.assets.models import PipeMain
from cwageodjango.utilities.models import DMA, Utility


class Command(BaseCommand):
    help = "Write Severn Trent Water mains layer data to sql"

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

        pipe_mains_layer = ds[layer_index]

        new_pipe_mains = []

        for feature in pipe_mains_layer:
            tag = feature.get("tag")
            geom = feature.geom
            geom_4326 = feature.get("wkt_geom_4326")
            material = feature.get("material") or "unknown"
            diameter = feature.get("DIAMETER_mm") or -1
            pipe_type = feature.get("type")

            new_pipe_main = PipeMain(
                tag=tag,
                geometry=geom.wkt,
                geometry_4326=geom_4326,
                material=material,
                diameter=diameter,
                pipe_type=pipe_type,
            )
            new_pipe_mains.append(new_pipe_main)

            if len(new_pipe_mains) == 100000:
                PipeMain.objects.bulk_create(new_pipe_mains)
                new_pipe_mains = []

        # save the last set of data as it will probably be less than 100000
        if new_pipe_mains:
            PipeMain.objects.bulk_create(new_pipe_mains)

        # get the utility
        utility = Utility.objects.get(name="severn_trent_water")

        DMAThroughModel = PipeMain.dmas.through
        bulk_create_list = []

        for pipe_main in PipeMain.objects.filter(dmas=None).only("id", "geometry"):

            wkt = pipe_main.geometry.wkt

            dma_ids = DMA.objects.filter(
                geometry__intersects=wkt, utility=utility
            ).values_list("pk", flat=True)

            if not dma_ids:
                dma_ids = [DMA.objects.get(name=r"undefined", utility=utility).pk]

            for dma_id in dma_ids:
                bulk_create_list.append(
                    DMAThroughModel(pipemain_id=pipe_main.pk, dma_id=dma_id)
                )

            if len(bulk_create_list) == 100000:
                DMAThroughModel.objects.bulk_create(bulk_create_list)
                bulk_create_list = []

        # save the last set of data as it will probably be less than 100000
        if bulk_create_list:
            DMAThroughModel.objects.bulk_create(bulk_create_list)
