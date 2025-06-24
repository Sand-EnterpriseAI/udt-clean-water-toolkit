from neomodel import Relationship
from .network_node import NetworkNode
from .pipe_main import PipeMain
from .has_asset import HasAsset


class PipeNode(NetworkNode):
    pipe_main = Relationship("PipeMain", "PIPE_MAIN", model=PipeMain)
    has_asset = Relationship("HasAsset", "HAS_ASSET", model=HasAsset)
