from django.core.management.base import BaseCommand
from django.contrib.gis.gdal import DataSource
from cwageodjango.assets.models import NetworkOptValve
from cwageodjango.utilities.models import DMA, Utility


class Command(BaseCommand):
    help = "Write Thames Water network opt valve data to sql"

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
        network_opt_valve_layer = ds[layer_index]

        new_network_opt_valves = []
        for feature in network_opt_valve_layer:
            gid = feature.get("GISID")
            geom = feature.geom
            geom_4326 = feature.get("wkt_geom_4326")
            logger = 0

            new_network_opt_valve = NetworkOptValve(
                tag=gid,
                geometry=geom.wkt,
                geometry_4326=geom_4326,
                acoustic_logger=logger,
            )
            new_network_opt_valves.append(new_network_opt_valve)

            if len(new_network_opt_valves) == 100000:
                NetworkOptValve.objects.bulk_create(new_network_opt_valves)
                new_network_opt_valves = []

        # save the last set of data as it will probably be less than 100000
        if new_network_opt_valves:
            NetworkOptValve.objects.bulk_create(new_network_opt_valves)

        # get the utility
        utility = Utility.objects.get(name="thames_water")

        DMAThroughModel = NetworkOptValve.dmas.through
        bulk_create_list = []
        for network_opt_valve in NetworkOptValve.objects.only("id", "geometry"):
            wkt = network_opt_valve.geometry.wkt

            dma_ids = DMA.objects.filter(
                geometry__intersects=wkt, utility=utility
            ).values_list("pk", flat=True)

            if not dma_ids:
                dma_ids = [DMA.objects.get(code=r"undefined", utility=utility).pk]
            bulk_create_list.extend(
                [
                    DMAThroughModel(
                        networkoptvalve_id=network_opt_valve.pk, dma_id=dma_id
                    )
                    for dma_id in dma_ids
                ]
            )
            if len(bulk_create_list) == 100000:
                DMAThroughModel.objects.bulk_create(bulk_create_list)
                bulk_create_list = []

        # save the last set of data as it will probably be less than 100000
        if bulk_create_list:
            DMAThroughModel.objects.bulk_create(bulk_create_list)
