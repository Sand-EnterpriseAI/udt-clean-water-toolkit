from neomodel import StringProperty
from .network_node import NetworkNode
from cwageodjango.core.constants import POINT_ASSET__NAME


class PointAsset(NetworkNode):
    __optional_labels__ = [
        "Chamber",
        "ConnectionMeter",
        "ConsumptionMeter",
        "FlowControl",
        "Hydrant",
        "Logger",
        "Meter",
        "NetworkMeter",
        "NetworkOptValve",
        "OperationalSite",
        "PressureControlValve",
        "PressureFitting",
        "WaterPump",
        "WaterTank",
        "WaterWork",
    ]

    tag = StringProperty(required=True, index=True)

    class AssetMeta:
        node_type = POINT_ASSET__NAME
