import random
import json
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from cwageodjango.assets.models import PipeMain
from cwageodjango.waterpipes.models import PipeFlow


class Command(BaseCommand):
    help = "Generate flow data for each pipe at 15 minute intervals for a day"

    def handle(self, *args, **kwargs):
        pipes = PipeMain.objects.all()[:1000]

        for pipe in pipes:
            flow_data = self.generate_random_flow_data()

            try:
                # Create a new PipeFlow object for each PipeMain instance
                pipe_flow = PipeFlow.objects.create(pipe_main=pipe, flow_data=flow_data)
                # self.stdout.write(
                #     self.style.SUCCESS(f"Flow data added to PipeMain {pipe.id}")
                # )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"Failed to create PipeFlow for PipeMain {pipe.id}: {e}"
                    )
                )

    def generate_random_flow_data(self):
        start_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        flow_data = {}

        for i in range(0, 24 * 4):  # 24 hours * 4 (15-minute intervals per hour)
            time_slot = start_time + timedelta(minutes=i * 15)
            flow_value = round(random.uniform(0.0, 100.0), 2)  # range
            flow_data[time_slot.isoformat()] = flow_value

        return json.dumps(flow_data)
