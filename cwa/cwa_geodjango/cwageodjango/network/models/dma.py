from neomodel import StructuredNode, StringProperty


class DMA(StructuredNode):
    code = StringProperty(required=True, unique_index=True)
    name = StringProperty(required=True, index=True)
