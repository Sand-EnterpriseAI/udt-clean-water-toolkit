from neomodel import db
from wntr.network import WaterNetworkModel


class InpToNeo4jController:
    """Convert a WaterNetworkModel into a Neo4j graph using Cypher queries."""

    def __init__(self, config):
        self.config = config

    def create_neo4j_graph(
        self, wn, node_weight=None, link_weight=None, modify_direction=False
    ):
        """
        Convert a WaterNetworkModel into a Neo4j graph using Cypher queries.

        Parameters
        ----------
        wn : WaterNetworkModel
            The water network model to convert.
        node_weight : dict or pandas Series, optional
            Node weights.
        link_weight : dict or pandas Series, optional
            Link weights.
        modify_direction : bool, optional
            If True, then if the link weight is negative, the link start and
            end node are switched and the abs(weight) is assigned to the link
            (this is useful when weighting graphs by flowrate). If False, link
            direction and weight are not changed.
        """

        # Add nodes
        for name, node in wn.nodes():
            node_attributes = {
                "node_key": name,
                "pos": str(node.coordinates),  # Convert coordinates to string
                "type": node.node_type,
            }
            if node_weight is not None and name in node_weight:
                node_attributes["weight"] = node_weight[name]

            query = f"""
            CREATE (n:NetworkNode {{
                node_key: '{node_attributes['node_key']}',
                pos: '{node_attributes['pos']}',
                type: '{node_attributes['type']}'
            """
            if "weight" in node_attributes:
                query += f", weight: {node_attributes['weight']}"
            query += "})"
            db.cypher_query(query)

        # Add links
        for name, link in wn.links():
            start_node_name = link.start_node_name
            end_node_name = link.end_node_name
            link_type = link.link_type
            link_weight_value = None

            if link_weight is not None and name in link_weight:
                link_weight_value = link_weight[name]

            if (
                modify_direction
                and link_weight_value is not None
                and link_weight_value < 0
            ):
                start_node_name, end_node_name = end_node_name, start_node_name
                link_weight_value = -link_weight_value

            relationship_properties = {"type": link_type}
            if link_weight_value is not None:
                relationship_properties["weight"] = link_weight_value

            query = f"""
            MATCH (start:NetworkNode {{node_key: '{start_node_name}'}})
            MATCH (end:NetworkNode {{node_key: '{end_node_name}'}})
            CREATE (start)-[:LINKED_TO {{
                type: '{relationship_properties['type']}'"""
            if "weight" in relationship_properties:
                query += f", weight: {relationship_properties['weight']}"
            query += "}]->(end)"
            db.cypher_query(query)

    def convert(self):
        wn = WaterNetworkModel(self.config.inpfile)
        self.create_neo4j_graph(wn)
