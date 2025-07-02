from django.contrib.gis.gdal import DataSource
from django.core.management.base import BaseCommand
from django.contrib.gis.geos import GEOSGeometry
from cwageodjango.utilities.models import DMA, Utility
from cwageodjango.core.constants import DEFAULT_SRID


class Command(BaseCommand):
    help = "Write Thames Water dma codes from geospatial layers of interest to sql"

    def add_arguments(self, parser):
        parser.add_argument("-f", "--file", type=str, help="Path to valid datasource")
        parser.add_argument("-x", "--index", type=str, help="Layer index")

    ### Attempt using bulk create
    def handle(self, *args, **kwargs):
        ds_path = kwargs.get("file")
        layer_index = kwargs.get("index")

        utility, _ = Utility.objects.get_or_create(name="thames_water")

        # Create a dummy dma as not all assets fall within a dma
        dma = DMA.objects.filter(utility=utility, code=r"undefined").first()

        if not dma:
            DMA.objects.create(
                utility=utility,
                name=r"undefined",
                code=r"undefined",
                geometry=GEOSGeometry("MULTIPOLYGON EMPTY", srid=DEFAULT_SRID),
            )

        ds = DataSource(ds_path)
        print(
            f"""There are {ds[layer_index].num_feat} features.
Large numbers of features will take a long time to save."""
        )

        dma_layer = ds[layer_index]

        new_dmas = []
        for feature in dma_layer:

            # TODO: Not sure why but have to do this instead of feature.geom directly
            # dma_geom = GEOSGeometry(feature.get("wkt"), srid=DEFAULT_SRID)

            new_dma = DMA(
                utility=utility,
                name=feature.get("DMANAME"),
                code=feature.get("DMAAREACODE"),
                geometry=feature.geom.wkt,
            )

            new_dmas.append(new_dma)
            if len(new_dmas) == 100000:
                DMA.objects.bulk_create(new_dmas)
                new_dmas = []

        # save the last set of data as it will probably be less than 100000
        if new_dmas:
            DMA.objects.bulk_create(new_dmas)
