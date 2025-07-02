from neomodel import db
from cleanwater.transform import Neo4j2Wntr
import wntr
from ...core.constants import ROUGHNESS_FACTORS


class Convert2Wntr(Neo4j2Wntr):
    """
    Class for converting Neo4j graph data to Water Network Toolkit (WNTR) format.

    This class extends the Neo4j2Wntr class, adding functionality to convert graph
    data from a Neo4j database into a WNTR model format, which is useful for
    hydraulic modeling and water network analysis.

    Parameters:
        config: Configuration object containing settings for the conversion.
        dma (optional): District Metered Area (DMA) code to filter data by a specific area.
        utility (optional): Utility name to filter data by a specific utility.

    Attributes:
        config: Stores the configuration object passed during initialization.
        links_loaded: Set of links (pipes) that have been loaded from the database.
        nodes_loaded: Set of nodes (junctions, reservoirs, etc.) that have been loaded from the database.
        asset_dict: Dictionary mapping node IDs to asset labels (e.g., reservoir, pipe).
    """

    def __init__(self, config, dma=None, utility=None):
        """
        Initialize the Convert2Wntr class.

        Parameters:
            config: Configuration object containing settings for the conversion.
            dma: (optional) District Metered Area (DMA) code for filtering.
            utility: (optional) Utility name for filtering.
        """
        super().__init__(config)
        self.dma = dma
        self.utility = utility
        self.roughness_values = ROUGHNESS_FACTORS  # Dictionary of roughness factors for different materials.
        self.links_loaded = set()  # Set to keep track of loaded links (pipes).
        self.nodes_loaded = set()  # Set to keep track of loaded nodes (junctions, reservoirs, etc.).
        self.asset_dict = {}  # Dictionary to store asset information by node ID.

    def query_neo4j(self, dma=None, utility=None, query_limit=None):
        """
        Query the Neo4j graph database in batches and populate the nodes_loaded set.

        This method retrieves nodes and links from the Neo4j database based on the
        provided DMA and utility parameters and stores them in
        self.nodes_loaded and self.links_loaded. The query is performed in batches
        to handle large datasets efficiently.

        Parameters:
            dma (str): District Metered Area (DMA) code for filtering (optional).
            utility (str): Utility name for filtering (optional).
            query_limit (int): Maximum number of nodes to load (optional).
        """
        offset = 0  # Initialize the offset for batch querying.
        total_nodes_loaded = 0  # Initialize the counter for total nodes loaded.
        query_limit = query_limit or float('inf')  # Set query limit to infinite if not provided.

        conditions = []  # List to hold query conditions.
        if dma:
            print(f"Filtering by DMA: {dma}")  # Print the DMA code if provided.
            conditions.append(f"d.code = '{dma}'")  # Add DMA filtering condition.
        if utility:
            print(f"Filtering by Utility: {utility}")  # Print the utility name if provided.
            conditions.append(f"u.name = '{utility}'")  # Add utility name filtering condition.

        where_clause = " AND ".join(conditions) if conditions else "1=1"  # Combine conditions or default to true.

        # Base query for fetching nodes in batches.
        node_query_base = """
            MATCH (n)-[r:PipeMain]-(m)
            MATCH (n)-[:IN_DMA]->(d)
            MATCH (n)-[:IN_UTILITY]->(u)
            WHERE {conditions}
            RETURN n,m
            SKIP {offset}
            LIMIT {batch_size}
        """

        # Base query for fetching edges (pipes) in batches.
        edge_query_base = """
            MATCH (n)-[r:PipeMain]->(m)
            MATCH (n)-[:IN_DMA]->(d)
            MATCH (m)-[:IN_DMA]->(d)
            MATCH (n)-[:IN_UTILITY]->(u)
            MATCH (m)-[:IN_UTILITY]->(u)
            WHERE {conditions}
            RETURN r
            SKIP {offset}
            LIMIT {batch_size}
        """

        # Loop to query nodes and edges in batches until the optional query limit is reached.
        while total_nodes_loaded < query_limit:
            try:
                # Format the node query with current offset and batch size.
                node_query = node_query_base.format(
                    conditions=where_clause,
                    offset=offset,
                    batch_size=self.config.batch_size
                )

                # Format the edge query with current offset and batch size.
                edge_query = edge_query_base.format(
                    conditions=where_clause,
                    offset=offset,
                    batch_size=self.config.batch_size
                )

                # Execute the node query and flatten the results.
                node_results_raw, _ = db.cypher_query(node_query)
                node_results = self.flatten_list(node_results_raw)

                # Execute the edge query and flatten the results.
                edge_results_raw, _ = db.cypher_query(edge_query)
                edge_results = self.flatten_list(edge_results_raw)

                offset += self.config.batch_size  # Update offset for the next batch.
            except Exception as e:
                print(f"Error querying the database: {e}")  # Handle any query errors.
                break

            # Process the query results if any nodes were returned.
            if node_results_raw:
                unique_nodes = {node["node_key"] for node in node_results}  # Get unique nodes from results.
                unique_edges = {edge._id for edge in edge_results}  # Get unique edges from results.

                # Filter out already loaded nodes.
                new_nodes = {record for record in node_results
                             if record['node_key'] not in {node['node_key'] for node in self.nodes_loaded}}
                print(f"Nodes queried: {len(unique_nodes)}, Nodes added: {len(new_nodes)}")  # Debug print.

                # Filter out already loaded edges.
                new_edges = {record for record in edge_results
                             if record.id not in {link.id for link in self.links_loaded}}
                print(f"Edges queried: {len(unique_edges)}, Edges added: {len(new_edges)}")  # Debug print.

                self.nodes_loaded.update(new_nodes)  # Add new nodes to the set of loaded nodes.
                self.links_loaded.update(new_edges)  # Add new edges to the set of loaded links.
                total_nodes_loaded += len(new_nodes)  # Update the count of total loaded nodes.

            else:
                print("Query returned no records")  # Print message if no records were returned.
                break

    def generate_asset_dict(self, node_ids):
        """
        Query Neo4j for assets connected to NetworkNodes and build the asset dictionary.

        This method retrieves asset information for specific nodes and stores the
        data in the asset_dict attribute, mapping node IDs to their corresponding
        asset labels.

        Parameters:
            node_ids (list): List of node IDs to filter nodes.

        Returns:
            results: Result object containing node IDs and their asset labels.
        """
        utilities = (self.config.utility_names or [])  # List of utility names to filter by.

        # Base query to fetch asset information for nodes.
        base_query = """
            MATCH (n)-[:PipeMain]-(m)
            MATCH (n)-[:IN_UTILITY]->(u)
            MATCH (n)-[:IN_DMA]->(d)
            MATCH (n)-[:HAS_ASSET]->(a)
            WHERE {conditions}
            RETURN id(n) AS node_id, 
                   CASE
                       WHEN a.subtype CONTAINS 'reservoir' THEN 'reservoir'
                       ELSE labels(a)
                   END AS asset_labels
        """
        conditions = [f"id(n) IN [{', '.join(map(str, node_ids))}]"]  # Condition to filter by node IDs.

        if utilities:
            utility_names_str = ", ".join(f"'{utility_name}'" for utility_name in utilities)
            conditions.append(f"u.name IN [{utility_names_str}]")  # Add utility name filtering condition.

        if self.dma:
            conditions.append(f"d.code = '{self.dma}'")  # Add DMA code filtering condition.

        where_clause = " AND ".join(conditions)  # Combine conditions for the WHERE clause.
        query = base_query.format(conditions=where_clause)  # Format the query with conditions.

        try:
            print("Querying assets")  # Debug print.
            results, _ = db.cypher_query(query)  # Execute the query.
        except Exception as e:
            print(f"Error querying assets: {e}")  # Handle any query errors.
            results = []

        # Process the results and populate the asset_dict.
        for attributes in results:
            node_id = str(attributes[0])  # Extract node ID.
            node_labels = attributes[1]  # Extract asset labels.
            self.asset_dict[node_id] = node_labels  # Map node ID to asset labels in the dictionary.

    def convert(self):
        """
        Convert the Neo4j graph data to WNTR format.

        This method orchestrates the entire conversion process, starting with querying
        the Neo4j database, generating the asset dictionary, and finally building the
        WNTR model graph.
        """
        print("Querying Neo4j")  # Debug print.
        self.query_neo4j(dma=self.dma, utility=self.utility)  # Query the Neo4j database for nodes and links.

        print("Assembling asset dictionary")  # Debug print.
        node_ids = [node._id for node in self.nodes_loaded]  # Extract node IDs from loaded nodes.
        self.generate_asset_dict(node_ids)  # Generate the asset dictionary.

        print("Building Water Network")  # Debug print.
        self.create_graph()  # Create the WNTR graph using the loaded nodes and links.

        print("Checking graph completeness")
        self.check_graph_completeness()

    def create_graph(self):
        """
        Create a WNTR graph from the loaded nodes and links.

        This method constructs the water network model by adding nodes and pipes
        (links) to the WNTR graph based on the data loaded from Neo4j.
        """
        for node in self.nodes_loaded:
            node_id_str = str(node._id)  # Convert node ID to string.
            coordinates = self.convert_coords(node['coords_27700'])  # Convert coordinates to WNTR format.
            node_type = self.asset_dict.get(node_id_str)  # Get node type from the asset dictionary.
            self.add_node(node_id_str, coordinates, node_type)  # Add the node to the WNTR model.

        for link in self.links_loaded:
            link_id = str(link.id)  # Convert link ID to string.
            start_node_id = str(link._start_node._id)  # Get the start node ID of the link.
            end_node_id = str(link._end_node._id)  # Get the end node ID of the link.

            if start_node_id not in self.wn.node_name_list:
                print(f"Missing start node! {start_node_id} for link {link_id}")  # Debug print for missing nodes.

            if end_node_id not in self.wn.node_name_list:
                print(f"Missing end node! {end_node_id} for link {link_id}")  # Debug print for missing nodes.

            diameter = link["diameter"]  # Get the pipe diameter.
            length = link["segment_length"]  # Get the pipe length.
            roughness = self.roughness_values.get(link['material'], 120)  # Get pipe roughness, default to 120.
            self.add_pipe(link_id, start_node_id, end_node_id, diameter, length,
                          roughness)  # Add the pipe to the model.

    def wntr_to_inp(self):
        """
        Export the WNTR model to an INP (EPANET input file) format.

        This method exports the constructed WNTR model into an EPANET-compatible
        INP file format, which can be used for hydraulic simulations in EPANET.
        """
        if self.dma:
            filename = f"{self.dma}_WNTR.INP"
        elif self.utility:
            filename = f"{self.utility}_WNTR.INP"
        else:
            raise ValueError("DMA or utility name must be provided for exporting to INP.")
        print(f"Exporting WNTR model to {filename}")  # Debug print.
        wntr.network.write_inpfile(self.wn, filename)  # Export the WNTR model to an INP file.

    def wntr_to_json(self):
        """
        Export the WNTR model to a JSON format.

        This method exports the WNTR model into a JSON file, which can be useful
        for sharing data or further processing in other tools or environments.

        Parameters:
            filename (str): Name of the JSON file to export.
        """
        if self.dma:
            filename = f"{self.dma}_WNTR.json"
        elif self.utility:
            filename = f"{self.utility}_WNTR.json"
        else:
            raise ValueError("DMA or utility name must be provided for exporting to JSON.")
        print(f"Exporting WNTR model to {filename}")  # Debug print.
        wntr.network.write_json(self.wn, filename)  # Export the WNTR model to a JSON file.

