import networkit as nk
from neomodel import db


class Neo4jToNk:
    """
    Converts a list of edges and nodes from Neo4J to NetworkIt
    """

    def __init__(self):
        self.G = nk.Graph(edgesIndexed=True)
        self.edgegid = self.G.attachEdgeAttribute("gid", str)

    def add_pipe(self, start_node_id, end_node_id):
        self.G.addEdge(start_node_id, end_node_id, addMissing=True)

    def get_node_attributes(self, node_type, attribute):
        node = getattr(attribute[1], node_type)

        node_id = node._id

        return node_id

    def set_edge_attributes(self, start_node_id, end_node_id, attribute):
        edge_gid = str(attribute[1]["gid"])
        self.edgegid[start_node_id, end_node_id] = edge_gid

    def create_nk_graph(self, graph):

        for attribute in graph:
            start_node_id = self.get_node_attributes("_start_node", attribute)
            end_node_id = self.get_node_attributes("_end_node", attribute)
            self.add_pipe(start_node_id, end_node_id)

    def query_graph(self, batch_size, utilities, dmas):
        """
        Generator function to query the graph database in batches.

        Parameters:
            batch_size (int): Size of each batch for querying the graph database.

        Yields:
            results: Result object containing batched query results.

        """
        offset = 0
        while True:
            results, m = db.cypher_query(
                f"MATCH (n:NetworkNode)-[:IN_UTILITY]-(u:Utility), (n)-[:IN_DMA]-(d:DMA) WHERE u.name IN {utilities} AND d.code IN {dmas} WITH n MATCH (n:NetworkNode)-[r:PipeMain]-(s:NetworkNode) RETURN n,r, s limit {batch_size}"
            )
            records = list(results)
            if not records:
                break

            yield results
            offset += batch_size

            if len(records) <= batch_size:
                break

    def convert(self, batch_size, filters):
        """
        Converts the Neo4j graph data to NetworKit format.
        Conversion is done in batches.
        """
        utilities = filters.get("utility_names")
        dmas = filters.get("dma_codes")

        for graph in self.query_graph(batch_size, utilities, dmas):
            self.create_nk_graph(graph)

    def nk_to_graphml(self, outputfile):
        """
        Export the network graph to a GraphML file.
        Writes the network graph to a specified GraphML file using the NetworkKit library.
        """
        nk.writeGraph(self.G, outputfile, nk.Format.GML)
