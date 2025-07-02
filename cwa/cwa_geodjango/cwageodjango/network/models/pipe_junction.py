from .pipe_node import PipeNode
from cwageodjango.core.constants import PIPE_JUNCTION__NAME


class PipeJunction(PipeNode):

    class AssetMeta:
        node_type = PIPE_JUNCTION__NAME
