from neomodel import StructuredNode, Relationship, ArrayProperty, StringProperty
from neomodel.contrib.spatial_properties import PointProperty

from .in_dma import InDma
from .in_utility import InUtility


class NetworkNode(StructuredNode):
    __abstract__ = True

    coords_27700 = ArrayProperty(required=True)
    node_key = StringProperty(unique_index=True, required=True)
    location = PointProperty(crs="wgs-84", require=True)
    in_dma = Relationship("InDma", "IN_DMA", model=InDma)
    in_utility = Relationship("InUtility", "IN_UTILITY", model=InUtility)
