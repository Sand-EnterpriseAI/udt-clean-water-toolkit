from .pipe_node import PipeNode
from cwageodjango.core.constants import PIPE_END__NAME


class PipeEnd(PipeNode):
    class AssetMeta:
        node_type = PIPE_END__NAME
