from django.core.management.base import BaseCommand
from django.contrib.gis.gdal import DataSource
from cwageodjango.assets.models import OperationalSite
from cwageodjango.utilities.models import DMA, Utility


class Command(BaseCommand):
    help = "Write Severn Trent Water operational site layer data to sql"

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

        operational_site_layer = ds[layer_index]

        new_operational_sites = []
        for feature in operational_site_layer:
            tag = feature.get("tag")
            geom = feature.geom
            geom_4326 = feature.get("wkt_geom_4326")
            subtype = feature.get("subtype")

            new_operational_site = OperationalSite(
                tag=tag, geometry=geom.wkt, geometry_4326=geom_4326, subtype=subtype
            )
            new_operational_sites.append(new_operational_site)

            if len(new_operational_sites) == 100000:
                OperationalSite.objects.bulk_create(new_operational_sites)
                new_operational_sites = []

        # save the last set of data as it will probably be less than 100000
        if new_operational_sites:
            OperationalSite.objects.bulk_create(new_operational_sites)

        # get the utility
        utility = Utility.objects.get(name="severn_trent_water")

        DMAThroughModel = OperationalSite.dmas.through
        bulk_create_list = []

        for operational_site in OperationalSite.objects.only("id", "geometry"):
            wkt = operational_site.geometry.wkt

            dma_ids = DMA.objects.filter(
                geometry__intersects=wkt, utility=utility
            ).values_list("pk", flat=True)

            if not dma_ids:
                dma_ids = [DMA.objects.get(name=r"undefined", utility=utility).pk]

            bulk_create_list.extend(
                [
                    DMAThroughModel(
                        operationalsite_id=operational_site.pk, dma_id=dma_id
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
