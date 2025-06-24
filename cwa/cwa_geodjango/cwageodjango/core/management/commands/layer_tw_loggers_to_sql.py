from django.core.management.base import BaseCommand
from django.contrib.gis.gdal import DataSource
from django.contrib.gis.utils import LayerMapping
from cwageodjango.assets.models import Logger
from cwageodjango.utilities.models import DMA, Utility


class Command(BaseCommand):
    help = "Write Thames Water Logger layer data to sql"

    def add_arguments(self, parser):
        parser.add_argument("-f", "--file", type=str, help="Path to valid datasource")
        parser.add_argument("-x", "--index", type=str, help="Layer index")

    def handle(self, *args, **kwargs):
        ds_path = kwargs.get("file")
        layer_index = kwargs.get("index")

        ds = DataSource(ds_path)

        print(
            f"""There are {ds[layer_index].num_feat} features.
Large numbers of features will take a long time to save."""
        )

        logger_layer = ds[layer_index]

        new_loggers = []
        for feature in logger_layer:
            gid = feature.get("GISID")
            geom = feature.geom
            geom_4326 = feature.get("wkt_geom_4326")

            new_logger = Logger(tag=gid, geometry=geom.wkt, geometry_4326=geom_4326)
            new_loggers.append(new_logger)

            if len(new_loggers) == 100000:
                Logger.objects.bulk_create(new_loggers)
                new_loggers = []

        # save the last set of data as it will probably be less than 100000
        if new_loggers:
            Logger.objects.bulk_create(new_loggers)

        # get the utility
        utility = Utility.objects.get(name="thames_water")

        DMAThroughModel = Logger.dmas.through
        bulk_create_list = []
        for logger in Logger.objects.only("id", "geometry"):
            wkt = logger.geometry.wkt

            dma_ids = DMA.objects.filter(
                geometry__intersects=wkt, utility=utility
            ).values_list("pk", flat=True)

            if not dma_ids:
                dma_ids = [DMA.objects.get(code=r"undefined", utility=utility).pk]

            bulk_create_list.extend(
                [
                    DMAThroughModel(logger_id=logger.pk, dma_id=dma_id)
                    for dma_id in dma_ids
                ]
            )

            if len(bulk_create_list) == 100000:
                DMAThroughModel.objects.bulk_create(bulk_create_list)
                bulk_create_list = []

        # save the last set of data as it will probably be less than 100000
        if bulk_create_list:
            DMAThroughModel.objects.bulk_create(bulk_create_list)
