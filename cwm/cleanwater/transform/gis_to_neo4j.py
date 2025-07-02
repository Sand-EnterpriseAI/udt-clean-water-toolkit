from multiprocessing.pool import ThreadPool
from typing import Annotated
from annotated_types import Gt
from neomodel import db
from collections import defaultdict
from . import GisToGraph


def flatten_concatenation(matrix):
    flat_list = []
    for row in matrix:
        flat_list += row
    return flat_list


class GisToNeo4j(GisToGraph):
    """Create a Neo4J graph of assets from a geospatial network of assets"""

    def __init__(
        self,
        srid,
        sqids,
        point_asset_names: list = [],
        processor_count: int = 2,
        chunk_size: Annotated[int, Gt(0)] = 1,
        neoj4_point: bool = False,
    ):
        self.srid = srid
        self.squids = sqids
        self.processor_count = processor_count

        self.all_pipe_nodes_by_pipe = []
        self.all_pipe_edges_by_pipe = []
        self.all_asset_nodes_by_pipe = []
        self.all_pipe_node_to_asset_node_edges = []
        self.dma_data = []
        self.utility_data = []
        self.network_node_labels = []

        super().__init__(
            srid,
            sqids,
            point_asset_names=point_asset_names,
            processor_count=processor_count,
            chunk_size=chunk_size,
            neoj4_point=neoj4_point,
        )

    def _get_unique_nodes_and_edges(self, all_nodes, all_edges):

        unique_node_keys = set()
        all_unique_nodes = []
        for node in all_nodes:
            node_key = node["node_key"]
            if node_key not in unique_node_keys:
                all_unique_nodes.append(node)
                unique_node_keys.add(node_key)

        unique_edge_keys = set()
        all_unique_edges = []
        for edge in all_edges:
            edge_key = edge["edge_key"]
            if edge_key not in unique_edge_keys:
                all_unique_edges.append(edge)
                unique_edge_keys.add(edge_key)

        return all_unique_nodes, all_unique_edges

    @staticmethod
    def set_default_node_properties():
        return """
        n.node_key = node.node_key,
        n.coords_27700 = node.coords_27700
        """

    def set_node_labels(self):
        subquery = ""
        for node_label in self.network_node_labels:
            subquery += f"""FOREACH (ignoreMe IN CASE
            WHEN '{node_label}' IN node.node_labels
            THEN [1] ELSE [] END |
            SET n:{node_label})\n"""

        return subquery

    def _batch_create_pipe_nodes(self):
        nodes = flatten_concatenation(self.all_pipe_nodes_by_pipe)

        query = f"""UNWIND $all_unique_nodes AS node
         MERGE (n:NetworkNode {{node_key: node.node_key}})
         ON CREATE
             SET n.createdAt = timestamp()
             {self.set_node_labels()}
         SET
         {self.set_default_node_properties()}
         RETURN n
         """

        db.cypher_query(query, {"all_unique_nodes": nodes})

    def _batch_create_pipe_node_relations(self):
        edges = flatten_concatenation(self.all_pipe_edges_by_pipe)

        grouped_edges = defaultdict(list)
        for edge in edges:
            grouped_edges[edge["asset_label"]].append(edge)

        for asset_label, edges in grouped_edges.items():
            query = f"""
            UNWIND $edges AS edge
            MATCH (n:NetworkNode {{node_key: edge.from_node_key}}),
                  (m:NetworkNode {{node_key: edge.to_node_key}})
            MERGE (n)-[r:{asset_label} {{
                tag: edge.tag,
                pipe_type: edge.pipe_type,
                material: edge.material,
                diameter: edge.diameter,
                segment_wkt: edge.segment_wkt,
                segment_length: edge.segment_length
                }}]-(m)
            ON CREATE
                SET r.createdAt = timestamp()
            RETURN r
            """
            db.cypher_query(query, {"edges": edges})

    def set_dynamic_asset_node_properties(self):
        subquery = """n.acoustic_logger = CASE WHEN node.acoustic_logger IS NOT NULL THEN node.acoustic_logger ELSE NULL END,
        n.subtype = CASE WHEN node.subtype IS NOT NULL THEN node.subtype ELSE NULL END"""

        return subquery

    def _batch_create_asset_nodes(self):
        nodes = flatten_concatenation(
            flatten_concatenation(self.all_asset_nodes_by_pipe)
        )

        query = f"""UNWIND $all_unique_nodes AS node
         MERGE (n:NetworkNode {{node_key: node.node_key}})
         ON CREATE
             SET n.createdAt = timestamp()
             {self.set_node_labels()}
         SET
        {self.set_default_node_properties()},
        {self.set_dynamic_asset_node_properties()},
         n.tag = node.tag
         RETURN n
         """

        db.cypher_query(query, {"all_unique_nodes": nodes})

    def _batch_create_pipe_node_to_asset_node_relations(self):
        edges = flatten_concatenation(self.all_pipe_node_to_asset_node_edges)

        query = f"""
            UNWIND $edges AS edge
            MATCH (n:NetworkNode {{node_key: edge.from_node_key}}),
                  (m:NetworkNode {{node_key: edge.to_node_key}})
            MERGE (n)-[r:HAS_ASSET {{
            edge_key: edge.edge_key
                }}]->(m)
            ON CREATE
                SET r.created_at = timestamp()
            RETURN r
            """

        db.cypher_query(query, {"edges": edges})

    def _batch_create_dma_nodes(self):
        """Batch creates DMA nodes."""
        query = f"""
        UNWIND $dma_nodes AS dma
        MERGE (d:DMA {{code: dma.code}})
        ON CREATE SET d.name = dma.name
        RETURN d
        """

        db.cypher_query(query, {"dma_nodes": flatten_concatenation(self.dma_data)})

    def _batch_create_dma_relationships(self):
        """Batch creates relationships between NetworkNodes and DMA nodes."""
        query = f"""
        UNWIND $dma_data AS dma
        MATCH (n:NetworkNode {{node_key: dma.to_node_key}}), (d:DMA {{code: dma.code}})
        MERGE (n)-[:IN_DMA]->(d)
        """

        db.cypher_query(query, {"dma_data": flatten_concatenation(self.dma_data)})

    def _batch_create_utility_nodes(self):
        """Batch creates Utility nodes."""
        query = f"""
        UNWIND $utility_data AS utility
        MERGE (u:Utility {{name: utility.name}})
        RETURN u
        """
        db.cypher_query(
            query, {"utility_data": flatten_concatenation(self.utility_data)}
        )

    def _batch_create_utility_relationships(self):
        """Batch creates relationships between NetworkNodes and Utility nodes."""
        query = f"""
        UNWIND $utility_data AS utility
        MATCH (n:NetworkNode {{node_key: utility.to_node_key}}), (u:Utility {{name: utility.name}})
        MERGE (n)-[:IN_UTILITY]->(u)
        """
        db.cypher_query(
            query, {"utility_data": flatten_concatenation(self.utility_data)}
        )

    def _map_pipe_connected_asset_relations(self):

        # self.all_asset_nodes_by_pipe = []
        # self.all_pipe_node_to_asset_node_edges = []
        self._batch_create_pipe_nodes()
        self._batch_create_pipe_node_relations()

        self._batch_create_asset_nodes()
        self._batch_create_pipe_node_to_asset_node_relations()

        # Batch create DMA nodes and relationship
        self._batch_create_dma_nodes()
        self._batch_create_dma_relationships()

        # Batch create utility nodes and relationship
        self._batch_create_utility_nodes()
        self._batch_create_utility_relationships()

    def _reset_pipe_asset_data(self):
        self.all_pipe_edges_by_pipe = []
        self.all_pipe_nodes_by_pipe = []
        self.all_asset_nodes_by_pipe = []
        self.all_pipe_node_to_asset_node_edges = []
        self.dma_data = []
        self.utility_data = []

    def create_neo4j_graph(self) -> None:

        # all_unique_nodes, all_unique_edges = self._get_unique_nodes_and_edges(
        #     self.all_pipe_nodes_by_pipe, self.all_pipe_edges_by_pipe
        # )

        self._map_pipe_connected_asset_relations()
        self.reset_pipe_asset_data()

    def _create_neo4j_graph_parallel(self) -> None:
        with ThreadPool(self.processor_count) as p:
            p.starmap(
                self._map_pipe_connected_asset_relations,
                zip(self.all_pipe_edges_by_pipe, self.all_pipe_nodes_by_pipe),
            )
        self.reset_pipe_asset_data()
