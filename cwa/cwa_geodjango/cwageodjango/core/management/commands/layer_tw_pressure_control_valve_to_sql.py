from django.core.management.base import BaseCommand
from django.contrib.gis.gdal import DataSource
from cwageodjango.assets.models import PressureControlValve
from cwageodjango.utilities.models import DMA, Utility


class Command(BaseCommand):
    help = "Write Thames Water pressure control valve layer data to sql"

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

        pressure_control_valve_layer = ds[layer_index]

        new_pressure_control_valves = []
        for feature in pressure_control_valve_layer:
            gid = feature.get("GISID")
            geom = feature.geom
            geom_4326 = feature.get("wkt_geom_4326")
            subtype = feature.get("SUBTYPECD")

            new_pressure_control_valve = PressureControlValve(
                tag=gid, geometry=geom.wkt, geometry_4326=geom_4326, subtype=subtype
            )
            new_pressure_control_valves.append(new_pressure_control_valve)

            if len(new_pressure_control_valves) == 100000:
                PressureControlValve.objects.bulk_create(new_pressure_control_valves)
                new_pressure_control_valves = []

        # save the last set of data as it will probably be less than 100000
        if new_pressure_control_valves:
            PressureControlValve.objects.bulk_create(new_pressure_control_valves)

        # get the utility
        utility = Utility.objects.get(name="thames_water")

        DMAThroughModel = PressureControlValve.dmas.through
        bulk_create_list = []

        for pressure_control_valve in PressureControlValve.objects.only(
            "id", "geometry"
        ):
            wkt = pressure_control_valve.geometry.wkt

            dma_ids = DMA.objects.filter(
                geometry__intersects=wkt, utility=utility
            ).values_list("pk", flat=True)

            if not dma_ids:
                dma_ids = [DMA.objects.get(name=r"undefined", utility=utility).pk]

            bulk_create_list.extend(
                [
                    DMAThroughModel(
                        pressurecontrolvalve_id=pressure_control_valve.pk, dma_id=dma_id
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
