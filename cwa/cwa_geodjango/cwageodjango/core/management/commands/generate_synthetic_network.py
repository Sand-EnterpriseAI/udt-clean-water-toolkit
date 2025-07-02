import random
import json
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.contrib.gis.geos import LineString, Point, MultiPolygon, Polygon
from cwageodjango.assets.models import (
    PipeMain,
    Hydrant,
    NetworkOptValve,
)
from cwageodjango.utilities.models import DMA, Utility
from cwageodjango.waterpipes.models import PipeFlow

class Command(BaseCommand):
    help = "Generate a synthetic water network for demonstration purposes."

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting synthetic network generation...")

        # 1. Clean up any existing data
        self.stdout.write("Cleaning up old data...")
        PipeFlow.objects.all().delete()
        Hydrant.objects.all().delete()
        NetworkOptValve.objects.all().delete()
        PipeMain.objects.all().delete()
        DMA.objects.all().delete()
        Utility.objects.all().delete()

        # 2. Define a geographic area (a simple 1km x 1km grid)
        min_x, min_y = -0.1, 51.5
        max_x, max_y = -0.09, 51.6
        grid_size = 10  # 10x10 grid

        # 3. Create a utility and a DMA
        self.stdout.write("Creating Utility and DMA...")
        utility, _ = Utility.objects.get_or_create(name="synthetic_utility")
        
        # Create a polygon for the DMA's geometry
        dma_polygon = Polygon.from_bbox((min_x, min_y, max_x, max_y))
        dma_multipolygon = MultiPolygon(dma_polygon, srid=4326)

        dma, _ = DMA.objects.get_or_create(
            code="SYNTHETIC_DMA_01",
            defaults={
                "name": "Synthetic DMA 01",
                "utility": utility,
                "geometry": dma_multipolygon
            }
        )
        grid_size = 10  # 10x10 grid

        # 4. Generate a street grid and create PipeMain objects
        self.stdout.write("Generating pipe mains...")
        pipe_mains = []
        # Horizontal pipes
        for i in range(grid_size + 1):
            y = min_y + (i * (max_y - min_y) / grid_size)
            line = LineString((min_x, y), (max_x, y), srid=4326)
            pipe = PipeMain(
                tag=f"H_PIPE_{i}",
                geometry=line,
                geometry_4326=line,
                material=random.choice(['Iron', 'PVC', 'Copper']),
                diameter=random.choice([100, 150, 200, 250, 300]),
                pipe_type='Distribution Main'
            )
            pipe_mains.append(pipe)

        # Vertical pipes
        for i in range(grid_size + 1):
            x = min_x + (i * (max_x - min_x) / grid_size)
            line = LineString((x, min_y), (x, max_y), srid=4326)
            pipe = PipeMain(
                tag=f"V_PIPE_{i}",
                geometry=line,
                geometry_4326=line,
                material=random.choice(['Iron', 'PVC', 'Copper']),
                diameter=random.choice([100, 150, 200, 250, 300]),
                pipe_type='Distribution Main'
            )
            pipe_mains.append(pipe)
        
        PipeMain.objects.bulk_create(pipe_mains)
        
        # Add all pipes to the DMA
        all_pipes = PipeMain.objects.all()
        for pipe in all_pipes:
            pipe.dmas.add(dma)


        # 5. Generate assets along the pipes
        self.stdout.write("Generating hydrants and valves...")
        hydrants = []
        valves = []
        for pipe in all_pipes:
            # Add a hydrant somewhere along the pipe
            if random.random() > 0.5: # 50% chance of adding a hydrant
                point = pipe.geometry.interpolate(random.random())
                hydrant = Hydrant(
                    tag=f"HYD_{pipe.tag}",
                    geometry=point,
                    geometry_4326=point,
                    acoustic_logger=random.choice([True, False])
                )
                hydrants.append(hydrant)

            # Add a valve somewhere along the pipe
            if random.random() > 0.7: # 30% chance of adding a valve
                point = pipe.geometry.interpolate(random.random())
                valve = NetworkOptValve(
                    tag=f"VALVE_{pipe.tag}",
                    geometry=point,
                    geometry_4326=point,
                    acoustic_logger=random.choice([True, False])
                )
                valves.append(valve)

        Hydrant.objects.bulk_create(hydrants)
        NetworkOptValve.objects.bulk_create(valves)

        # 6. Generate flow data for the new pipes
        self.stdout.write("Generating synthetic flow data...")
        self.generate_flow_data(all_pipes)

        self.stdout.write(self.style.SUCCESS("Successfully generated synthetic network."))

    def generate_flow_data(self, pipes):
        pipe_flows = []
        for pipe in pipes:
            flow_data = self.generate_random_flow_data_dict()
            pipe_flow = PipeFlow(pipe_main=pipe, flow_data=json.dumps(flow_data))
            pipe_flows.append(pipe_flow)
        
        PipeFlow.objects.bulk_create(pipe_flows)

    def generate_random_flow_data_dict(self):
        start_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        flow_data = {}

        for i in range(0, 24 * 4):  # 24 hours * 4 (15-minute intervals per hour)
            time_slot = start_time + timedelta(minutes=i * 15)
            flow_value = round(random.uniform(0.0, 100.0), 2)  # range
            flow_data[time_slot.isoformat()] = flow_value

        return flow_data
