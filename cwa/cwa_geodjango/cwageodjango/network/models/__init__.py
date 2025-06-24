from neomodel import db, install_labels, remove_all_labels
from .pipe_end import PipeEnd
from .point_asset import PointAsset
from .pipe_main import PipeMain
from .in_dma import InDma
from .in_utility import InUtility
from .network_node import NetworkNode
from .pipe_node import PipeNode
from .pipe_junction import PipeJunction
from .has_asset import HasAsset
from .dma import DMA
from .utility import Utility


def initialise_node_labels():
    """Setup constraints based on network models"""

    # Can't find count function in nodel model so using cypher query
    # Note: do not use __len__ as it's very slow for large number of nodes
    node_count = db.cypher_query("match (n) return count (n);")[0][0][0]

    if node_count == 0:
        remove_all_labels()
        install_labels(NetworkNode)
        install_labels(DMA)
        install_labels(Utility)
        install_labels(PipeMain)
        install_labels(PipeNode)
