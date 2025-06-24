from neomodel import StructuredNode, StringProperty
from cwageodjango.core.constants import UTILITIES


class Utility(StructuredNode):
    name = StringProperty(required=True, unique_index=True, choices=UTILITIES)
