import networkit as nk
from typing import Annotated
from annotated_types import Gt
from .gis_to_graph import GisToGraph


class GisToNk(GisToGraph):
    """
    Calculate network graph from geospatial asset data.
    """

    def __init__(
        self,
        srid,
        sqids,
        point_asset_names: list = [],
        processor_count: int = 2,
        chunk_size: Annotated[int, Gt(0)] = 1,
        neoj4_point: bool = False,
        outputfile=None,
    ):
        self.srid = srid
        self.squids = sqids
        self.processor_count = processor_count

        self.G: Graph = nk.Graph(edgesIndexed=True)
        self.edgelabel = self.G.attachEdgeAttribute("label", str)
        self.edgegid = self.G.attachEdgeAttribute("gid", str)
        self.nodelabel = self.G.attachNodeAttribute("label", str)

        self.all_pipe_nodes_by_pipe = []
        self.all_pipe_edges_by_pipe = []

        self.node_index = {}

        self.outputfile = outputfile

        super().__init__(
            srid,
            sqids,
            point_asset_names=point_asset_names,
            processor_count=processor_count,
            chunk_size=chunk_size,
            neoj4_point=neoj4_point,
        )

    def add_pipe(self, start_node_id, end_node_id):
        """
        Add a pipe to the network graph.

        Args:
            start_node_id: ID of the starting node of the pipe.
            end_node_id: ID of the ending node of the pipe.

        """
        self.G.addEdge(start_node_id, end_node_id, addMissing=True)

    def create_nk_graph(self) -> None:
        n = 0
        node_index = {}

        for i, pipe in enumerate(self.all_pipe_edges_by_pipe):
            from_node_key = pipe[0]["from_node_key"]
            to_node_key = pipe[0]["to_node_key"]
            edge_gid = pipe[0]["tag"]

            # Check if from_node_key exists in node_index, if not, assign a new index
            if from_node_key not in self.node_index:
                self.node_index[from_node_key] = len(self.node_index) + 1
            from_node_id = self.node_index[from_node_key]

            # Check if to_node_key exists in node_index, if not, assign a new index
            if to_node_key not in self.node_index:
                self.node_index[to_node_key] = len(self.node_index) + 1
            to_node_id = self.node_index[to_node_key]

            # Add the pipe to the Networkit graph
            self.add_pipe(from_node_id, to_node_id)

            # Add edge attributes
            self.edgelabel[from_node_id, to_node_id] = pipe[0]["asset_label"]
            self.edgegid[from_node_id, to_node_id] = str(edge_gid)

            for n in self.all_pipe_nodes_by_pipe[i]:
                if n.get("node_key") == from_node_key:
                    self.nodelabel[from_node_id] = n.get("node_labels")[-1]
                elif n.get("node_key") == to_node_key:
                    self.nodelabel[to_node_id] = n.get("node_labels")[-1]
            # Add node labels
            # Assuming asset_label is the label for both from_node and to_node
            asset_label = pipe[0]["asset_label"]
            self.nodelabel[from_node_id] = asset_label
            self.nodelabel[to_node_id] = asset_label

    def nk_to_graphml(self, outputfile):
        """
        Export the network graph to a GraphML file.
        Writes the network graph to a specified GraphML file using the NetworkKit library.
        """
        nk.writeGraph(self.G, outputfile, nk.Format.GML)
