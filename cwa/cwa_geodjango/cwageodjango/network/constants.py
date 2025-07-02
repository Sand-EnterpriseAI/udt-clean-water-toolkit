from collections import OrderedDict
from cwageodjango.assets.models import *

POINT_ASSET_MODELS = OrderedDict(
    [
        ("chamber", Chamber),
        ("connection_meter", ConnectionMeter),
        ("consumption_meter", ConsumptionMeter),
        ("flow_control", FlowControl),
        ("hydrant", Hydrant),
        ("logger", Logger),
        ("meter", Meter),
        ("network_meter", NetworkMeter),
        ("network_opt_valve", NetworkOptValve),
        ("operational_site", OperationalSite),
        ("pressure_control_valve", PressureControlValve),
        ("pressure_fitting", PressureFitting),
        ("water_pump", WaterPump),
        ("water_tank", WaterTank),
        ("water_work", WaterWork),
    ]
)

PIPE_MAIN_MODEL = PipeMain
