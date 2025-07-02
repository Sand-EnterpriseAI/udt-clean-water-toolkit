from django.core.management.base import BaseCommand
from django.contrib.gis.gdal import DataSource
from cwageodjango.assets.models import Chamber
from cwageodjango.utilities.models import DMA


class Command(BaseCommand):
    help = "Write Thames Water chamber layer data to sql"

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

        chamber_layer = ds[layer_index]

        new_chambers = []
        for feature in chamber_layer:
            gid = feature.get("GISID")
            geom = feature.geom
            geom_4326 = feature.get("wkt_geom_4326")

            new_chamber = Chamber(tag=gid, geometry=geom.wkt, geometry_4326=geom_4326)
            new_chambers.append(new_chamber)

            if len(new_chambers) == 100000:
                Chamber.objects.bulk_create(new_chambers)
                new_chambers = []

        # save the last set of data as it will probably be less than 100000
        if new_chambers:
            Chamber.objects.bulk_create(new_chambers)

        DMAThroughModel = Chamber.dmas.through
        bulk_create_list = []
        for chamber in Chamber.objects.only("id", "geometry"):
            wkt = chamber.geometry.wkt

            dma_ids = DMA.objects.filter(
                geometry__intersects=wkt, utility__name="thames_water"
            ).values_list("pk", flat=True)

            if not dma_ids:
                dma_ids = [
                    DMA.objects.get(code=r"undefined", utility__name="thames_water").pk
                ]

            bulk_create_list.extend(
                [
                    DMAThroughModel(chamber_id=chamber.pk, dma_id=dma_id)
                    for dma_id in dma_ids
                ]
            )

            if len(bulk_create_list) == 100000:
                DMAThroughModel.objects.bulk_create(bulk_create_list)
                bulk_create_list = []

        # save the last set of data as it will probably be less than 100000
        if bulk_create_list:
            DMAThroughModel.objects.bulk_create(bulk_create_list)
