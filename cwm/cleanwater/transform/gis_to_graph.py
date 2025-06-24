import json
import bisect
from typing import Annotated
from annotated_types import Gt
from multiprocessing import Pool
from django.contrib.gis.geos import GEOSGeometry
from django.db.models.query import QuerySet
from shapely.ops import substring
from shapely import LineString, Point, line_locate_point
from ..core.utils import normalised_point_position_on_line
from ..core.constants import (
    PIPE_END__NAME,
    PIPE_JUNCTION__NAME,
    POINT_ASSET__NAME,
    GEOS_LINESTRING_TYPES,
    GEOS_POINT_TYPES,
    NETWORK_NODE__LABEL,
    PIPE_NODE__LABEL,
    PIPE_JUNCTION__LABEL,
    PIPE_END__LABEL,
    POINT_ASSET__LABEL,
)


def flatten_concatenation(matrix):
    """
    Flattens a 2D list (matrix) into a 1D list.

    Args:
        matrix (list of list): The 2D list to be flattened.

    Returns:
        list: A flat list containing all elements of the input matrix.
    """
    flat_list = []
    for row in matrix:
        flat_list += row
    return flat_list


class GisToGraph:
    """
    A class to convert GIS (Geographic Information System) data into a graph-based representation.

    The class processes spatial data such as pipes and point assets, and represents them
    as nodes and edges in a graph. This conversion facilitates the analysis of network structures
    and their properties, particularly in the context of utilities and infrastructure management.

    Attributes:
        srid (int): Spatial Reference System Identifier (SRID) used for geometry operations.
        sqids: Object responsible for generating unique IDs for nodes.
        point_asset_names (list): Names of point assets to include in the graph.
        processor_count (int): Number of processors to use in parallel operations.
        chunk_size (int or None): Size of data chunks for parallel processing.
        neoj4_point (bool): Whether to use Neo4j point geometry for nodes.
        all_pipe_edges_by_pipe (list): List of edges for each pipe.
        all_pipe_nodes_by_pipe (list): List of nodes for each pipe.
        all_asset_nodes_by_pipe (list): List of asset nodes for each pipe.
        all_pipe_node_to_asset_node_edges (list): List of edges connecting pipe nodes to asset nodes.
        dma_data (list): List of DMA (District Metered Area) data associated with nodes.
        utility_data (list): List of utility data associated with nodes.
        network_node_labels (list): List of unique network node labels.
        network_edge_labels (list): List of unique pipe edge labels.
    """

    def __init__(
        self,
        srid: int,
        sqids,
        point_asset_names: list = [],
        processor_count: int = 2,
        chunk_size: None | Annotated[int, Gt(0)] = None,
        neoj4_point: bool = False,
    ):
        self.srid = srid
        self.sqids = sqids
        self.point_asset_names = point_asset_names
        self.processor_count = processor_count
        self.chunk_size = chunk_size
        self.neoj4_point = neoj4_point

        self.all_pipe_edges_by_pipe: list = []
        self.all_pipe_nodes_by_pipe: list = []
        self.all_asset_nodes_by_pipe: list = []
        self.all_pipe_node_to_asset_node_edges: list = []
        self.dma_data: list = []
        self.utility_data: list = []
        self.network_node_labels: list = [
            NETWORK_NODE__LABEL,
            PIPE_NODE__LABEL,
            PIPE_JUNCTION__LABEL,
            PIPE_END__LABEL,
            POINT_ASSET__LABEL,
        ]  # List of network node labels with no duplicates
        self.network_edge_labels: list = (
            []
        )  # List of pipe edge labels with no duplicates

    def reset_pipe_asset_data(self):
        """
        Resets the internal data structures related to pipe and asset data.
        Clears all previously stored pipe edges, nodes, and associated data.
        """
        self.all_pipe_edges_by_pipe = []
        self.all_pipe_nodes_by_pipe = []
        self.all_asset_nodes_by_pipe = []
        self.all_pipe_node_to_asset_node_edges = []
        self.dma_data = []
        self.utility_data = []

    def calc_pipe_point_relative_positions(self, pipes: list) -> None:
        """
        Calculate and store relative positions of pipe points in the network.

        This function processes a list of pipe queries (`pipes`) to calculate
        the relative positions of various network components associated with each pipe.
        It updates several instance attributes with the results of these calculations.

        Parameters:
        pipes (list): A list of pipe query sets, where each entry contains data
                         necessary to compute the relative positions.

        Returns:
        None: This method does not return a value but updates the following instance attributes:
            - all_pipe_nodes_by_pipe: List of pipe nodes associated with each pipe.
            - all_pipe_edges_by_pipe: List of pipe edges associated with each pipe.
            - all_asset_nodes_by_pipe: List of asset nodes associated with each pipe.
            - all_pipe_node_to_asset_node_edges: List of edges connecting pipe nodes to asset nodes.
            - dma_data: Data related to district metered areas (DMA) for each pipe.
            - utility_data: Utility-related data for each pipe.
            - network_node_labels (extended): List of unique network node labels based on asset nodes.
        """
        (
            self.all_pipe_nodes_by_pipe,
            self.all_pipe_edges_by_pipe,
            self.all_asset_nodes_by_pipe,
            self.all_pipe_node_to_asset_node_edges,
            self.dma_data,
            self.utility_data,
            all_asset_node_labels,
        ) = list(zip(*map(self.map_relative_positions_calc, pipes)))

        self.network_node_labels.extend(
            list(set(flatten_concatenation(all_asset_node_labels)))
        )

    def calc_pipe_point_relative_positions_parallel(self, pipes_qs: list) -> None:
        with Pool(processes=self.processor_count) as p:
            (
                self.all_pipe_nodes_by_pipe,
                self.all_pipe_edges_by_pipe,
                self.all_asset_nodes_by_pipe,
                self.all_pipe_node_to_asset_node_edges,
                self.dma_data,
                self.utility_data,
                all_asset_node_labels,
            ) = zip(
                *p.imap_unordered(
                    self.map_relative_positions_calc,
                    pipes_qs,
                    self.chunk_size,
                )
            )

        self.network_node_labels.extend(
            list(set(flatten_concatenation(all_asset_node_labels)))
        )

    def map_relative_positions_calc(self, pipe_qs_object):
        """
        Calculate and map the relative positions of pipeline segments, junctions, and point assets.

        This function processes a queryset object representing pipeline segments and associated
        geospatial data. It calculates the relative positions of intersecting pipes (junctions)
        and point assets along the pipeline, and orders these elements based on their geospatial
        relationships. The results are returned as structured data representing nodes, edges,
        and asset connections, which can be used for further analysis or visualization.

        Parameters:
        -----------
        pipe_qs_object : queryset
            A Django QuerySet object containing pipeline segment data. This queryset includes
            geospatial information necessary for calculating the positions of junctions and point assets.

        Returns:
        --------
        tuple
            A tuple containing the following elements:

            - pipe_nodes_by_pipe : dict
                A dictionary mapping each pipe to its corresponding nodes.

            - pipe_edges_by_pipe : dict
                A dictionary mapping each pipe to its corresponding edges.

            - asset_nodes_by_pipe : dict
                A dictionary mapping each pipe to its associated asset nodes.

            - pipe_node_to_asset_node_edges : dict
                A dictionary representing edges between pipe nodes and asset nodes.

            - dma_data : dict
                Data related to District Metered Areas (DMAs) derived from the pipeline data.

            - utility_data : dict
                Data related to utility services derived from the pipeline data.

            - all_asset_node_labels : list
                A list of labels for all asset nodes identified in the pipeline data.

        Notes:
        ------
        This function is part of a larger pipeline management and geospatial analysis framework.
        It combines data from various sources to provide a comprehensive mapping of pipeline
        segments and assets. The order of nodes and the connections between them
        are based on their actual physical positions within the geospatial dataset.
        """

        # Convert the base pipe data from a queryset object to a dictionary
        base_pipe: dict = self._get_base_pipe_data(pipe_qs_object)

        # Convert all the data from intersecting pipes into
        # a list of dictionaries
        pipe_junctions: list = self._combine_all_pipe_junctions(pipe_qs_object)

        # Convert all the data from point assets into a list of dictionaries
        point_assets: list = self._combine_all_point_assets(pipe_qs_object)

        # Get the intersection points of all intersecting pipes (pipe junctions)
        junctions_with_positions = self._get_connections_points_on_pipe(
            base_pipe,
            pipe_junctions,
        )

        # Get the intersection points of all point assets
        point_assets_with_positions = self._get_connections_points_on_pipe(
            base_pipe,
            point_assets,
        )

        # Set node properties and order them relative to the start point
        # of the line. The junction and asset nodes returned matches the
        # actual physical order that occurs geo-spatially
        nodes_ordered = self._set_node_properties(
            base_pipe, junctions_with_positions, point_assets_with_positions
        )

        (
            pipe_nodes_by_pipe,
            pipe_edges_by_pipe,
            asset_nodes_by_pipe,
            pipe_node_to_asset_node_edges,
            dma_data,
            utility_data,
            all_asset_node_labels,
        ) = self._set_nodes_and_edges(base_pipe, nodes_ordered)

        return (
            pipe_nodes_by_pipe,
            pipe_edges_by_pipe,
            asset_nodes_by_pipe,
            pipe_node_to_asset_node_edges,
            dma_data,
            utility_data,
            all_asset_node_labels,
        )

    def create_dma_data(self, node_data: dict) -> list:
        """
        Create a list of dictionaries representing District Metered Area (DMA) data.

        This function processes node data to generate a structured list of DMA entries.
        Each entry in the list contains a DMA code, DMA name, and a reference to a node key.
        The function is useful for organizing and storing DMA information related to specific
        nodes within a pipeline or utility network.

        Parameters:
        -----------
        node_data : dict
            A dictionary containing node information. Expected keys are:
            - "dma_codes": A list of DMA codes associated with the node.
            - "dma_names": A list of DMA names corresponding to the DMA codes.
            - "node_key": A unique identifier for the node to which the DMA data is linked.

        Returns:
        --------
        list
            A list of dictionaries, where each dictionary represents a DMA with the following keys:
            - "code": The DMA code.
            - "name": The DMA name.
            - "to_node_key": The unique node key linking the DMA to the node.

        Notes:
        ------
        The `node_data` dictionary must have the same length for the "dma_codes" and "dma_names" lists,
        as each DMA code is paired with a corresponding DMA name.
        """
        dma_data = []
        for dma_code, dma_name in zip(node_data["dma_codes"], node_data["dma_names"]):
            dma_data.append(
                {
                    "code": dma_code,
                    "name": dma_name,
                    "to_node_key": node_data["node_key"],
                }
            )

        return dma_data

    def create_utility_data(self, node_data: dict) -> list:
        """
        Create a list of dictionaries representing utility data for a specific node.

        This function generates a structured list containing utility information
        associated with a specific node within a pipeline or utility network. Each entry
        in the list includes the utility name and a reference to the node key.

        Parameters:
        -----------
        node_data : dict
            A dictionary containing node information. Expected keys are:
            - "utility": The name of the utility associated with the node.
            - "node_key": A unique identifier for the node to which the utility data is linked.

        Returns:
        --------
        list
            A list containing a single dictionary with the following keys:
            - "name": The utility name.
            - "to_node_key": The unique node key linking the utility to the node.

        Notes:
        ------
        This function assumes that each node is associated with a single utility.
        The returned list contains only one dictionary, representing the utility data for the node.
        """

        return [
            {
                "name": node_data["utility"],
                "to_node_key": node_data["node_key"],
            }
        ]

    def _set_pipe_properties(self, node: dict, pipe_node_data: dict) -> dict:
        """
        Set properties for a pipeline node, including encoding the node key and assigning pipe tags.

        This function assigns specific properties to a pipeline node, such as determining
        the pipe node type (junction or end) and encoding a unique node key based on the
        node's intersection geometry. It also assigns pipe tags to the node data.

        Parameters:
        -----------
        node : dict
            A dictionary representing the pipeline node with the following expected keys:
            - "intersection_point_geometry": The geometric data of the node's intersection point.
            - "pipe_tags": A list of tags associated with the pipe.

        pipe_node_data : dict
            A dictionary containing existing data for the pipeline node. Expected key:
            - "node_labels": A list of labels describing the node's type (e.g., "PipeJunction").

        Returns:
        --------
        dict
            The updated `pipe_node_data` dictionary with the following additional keys:
            - "node_key": A unique identifier for the node, encoded based on its intersection point geometry.
            - "pipe_tags": The tags associated with the pipe, directly copied from the `node` input.

        Notes:
        ------
        The node key is encoded using the node's intersection geometry and a type index,
        where the type index differentiates between pipe junctions and other pipe types.
        """

        if "PipeJunction" in pipe_node_data["node_labels"]:
            pipe_type_encode_index = 0
        else:
            pipe_type_encode_index = 1

        pipe_node_data["node_key"] = self._encode_node_key(
            node["intersection_point_geometry"], extra_params=[pipe_type_encode_index]
        )
        pipe_node_data["pipe_tags"] = node["pipe_tags"]

        return pipe_node_data

    def _merge_pipe_junction_node(self, node: dict) -> dict:
        """
        Merge data for a pipe junction node and set its properties.

        This function creates a dictionary for a pipe junction node, assigns relevant
        labels to it, and then passes this data to the `_set_pipe_properties` method
        to encode the node key and set additional properties.

        Parameters:
        -----------
        node : dict
            A dictionary representing the pipeline node, typically containing geometric
            data and other relevant information needed for processing.

        Returns:
        --------
        dict
            The pipeline node data after being processed by `_set_pipe_properties`,
            including an encoded node key, node labels, and other properties.

        Notes:
        ------
        This function specifically handles nodes identified as pipe junctions,
        assigning them the appropriate labels before setting further properties.
        """
        pipe_node_data = {}

        pipe_node_data["node_labels"] = [PIPE_NODE__LABEL, PIPE_JUNCTION__LABEL]

        return self._set_pipe_properties(node, pipe_node_data)

    def _merge_pipe_end_node(self, node):
        pipe_node_data = {}
        pipe_node_data["node_labels"] = [PIPE_NODE__LABEL, PIPE_END__LABEL]

        return self._set_pipe_properties(node, pipe_node_data)

    def _handle_pipe_asset_node_labels(self, node):
        pipe_node_data = {}

        node_encode_index = self.point_asset_names.index(node["asset_name"])
        pipe_node_data["node_key"] = self._encode_node_key(
            node["intersection_point_geometry"], extra_params=[node_encode_index]
        )

        pipe_node_data["node_labels"] = [PIPE_NODE__LABEL, PIPE_JUNCTION__LABEL]

        return pipe_node_data

    def _create_asset_node(self, node: dict) -> dict:
        """
        Create and configure a node for a point asset within the network.

        This function initializes a dictionary for a point asset node, assigns appropriate labels,
        encodes a unique node key based on the asset's intersection geometry and name, and includes
        additional asset-specific properties such as tags, subtype, and acoustic logger information.

        Parameters:
        -----------
        node : dict
            A dictionary containing information about the point asset. Expected keys include:
            - "asset_label": The label representing the type of asset.
            - "asset_name": The name of the asset, used for encoding the node key.
            - "intersection_point_geometry": The geometric data of the asset's intersection point.
            - "tag": A tag associated with the asset.
            - "subtype" (optional): A subtype of the asset, if applicable.
            - "acoustic_logger" (optional): Acoustic logger information related to the asset, if applicable.

        Returns:
        --------
        dict
            A dictionary representing the configured asset node with the following keys:
            - "node_labels": A list of labels assigned to the asset node.
            - "node_key": A unique identifier for the asset node, encoded based on its intersection point geometry and asset name.
            - "tag": The tag associated with the asset.
            - "subtype": The subtype of the asset, if provided.
            - "acoustic_logger": Acoustic logger information, if provided.

        Notes:
        ------
        The node key is encoded using the asset's intersection geometry and a specific index
        derived from the asset's name. Additional properties such as subtype and acoustic
        logger are included if they are present in the input data.
        """
        asset_node_data = {}

        asset_node_data["node_labels"] = [
            NETWORK_NODE__LABEL,
            POINT_ASSET__LABEL,
            node["asset_label"],
        ]

        node_encode_index = self.point_asset_names.index(node["asset_name"])

        asset_node_data["node_key"] = self._encode_node_key(
            node["intersection_point_geometry"], extra_params=[node_encode_index]
        )

        asset_node_data["tag"] = node["tag"]

        subtype = node.get("subtype")
        if subtype:
            asset_node_data["subtype"] = subtype

        acoustic_logger = node.get("acoustic_logger")
        if acoustic_logger:
            asset_node_data["acoustic_logger"] = acoustic_logger

        return asset_node_data

    def _merge_point_asset_node(self, node: dict) -> tuple:
        """
        Merge data for a point asset node and handle associated pipe node labels.

        This function combines the data for a point asset node by first creating the asset node
        using `_create_asset_node` and then, if applicable, handling additional labels for the
        corresponding pipe node. It returns both the processed pipe node data and the asset node data.

        Parameters:
        -----------
        node : dict
            A dictionary containing information about the point asset and its relationship to the
            pipeline. Expected keys include:
            - "is_non_termini_asset_node" (optional): A boolean indicating if the asset node
              is a non-termini asset, requiring special handling of pipe node labels.

        Returns:
        --------
        tuple
            A tuple containing:
            - pipe_node_data : dict
                A dictionary with processed data for the pipe node, potentially including labels
                and other properties if `is_non_termini_asset_node` is True. Returns an empty dictionary
                if no special handling is required.
            - asset_node_data : dict
                A dictionary representing the configured asset node, as generated by `_create_asset_node`.

        Notes:
        ------
        This function is used to handle point assets that may be associated with non-termini nodes
        in a pipeline network. It ensures that both the asset node and any related pipe node data
        are appropriately merged and returned for further processing.
        """

        asset_node_data = self._create_asset_node(node)

        pipe_node_data = {}
        if node.get("is_non_termini_asset_node"):
            pipe_node_data = self._handle_pipe_asset_node_labels(node)

        return pipe_node_data, asset_node_data

    @staticmethod
    def _set_network_node_default_props(nodes) -> dict:

        return {
            "utility": nodes[0]["utility_name"],
            "coords_27700": [
                float(nodes[0]["intersection_point_geometry"].x),
                float(nodes[0]["intersection_point_geometry"].y),
            ],
            "dma_codes": nodes[0]["dma_codes"],
            "dma_names": nodes[0]["dma_names"],
            "dmas": nodes[0]["dmas"],
        }

    @staticmethod
    def _consolidate_nodes_on_position(nodes_ordered: list) -> list:
        """
        Consolidate nodes that are positioned at the same distance from the start of the pipe.

        This static method combines nodes that share the same rounded distance from the
        start of the pipe into groups. The nodes are expected to be ordered by their distance
        from the start of the pipe, and the method returns a list of lists, where each sublist
        contains nodes that occupy the same position along the pipe.

        Parameters:
        -----------
        nodes_ordered : list
            A list of dictionaries, where each dictionary represents a node along the pipeline.
            Each node dictionary must contain a key "distance_from_pipe_start_cm" that specifies
            the node's distance from the start of the pipe in centimeters.

        Returns:
        --------
        list
            A list of lists, where each sublist contains nodes that are located at the same
            distance from the start of the pipe. The nodes within each sublist are consolidated
            based on their rounded distance.

        Notes:
        ------
        The distance from the start of the pipe is rounded to the nearest whole number to determine
        if nodes should be consolidated. This method is useful for scenarios where multiple nodes
        are closely aligned along a pipeline and need to be treated as a single unit for further
        processing or analysis.
        """
        consolidated_nodes = [[nodes_ordered[0]]]

        prev_distance = round(nodes_ordered[0]["distance_from_pipe_start_cm"])
        for node in nodes_ordered[1:]:
            current_distance = round(node["distance_from_pipe_start_cm"])

            if current_distance == prev_distance:
                consolidated_nodes[-1].append(node)
            else:
                consolidated_nodes.append([node])

            prev_distance = current_distance

        return consolidated_nodes

    def _reconfigure_nodes(self, node: dict) -> tuple:
        """
        Reconfigure and merge node data based on the node type.

        This function processes a node dictionary by determining its type and
        applying the appropriate merge operation to reconfigure the node data.
        Depending on the node type, it may handle pipe junctions, pipe ends,
        or point assets. If the node type is not recognized, an exception is raised.

        Parameters:
        -----------
        node : dict
            A dictionary containing information about the node. Expected keys include:
            - "node_type": A string indicating the type of the node, which must be one of
              the following predefined types: PIPE_JUNCTION__NAME, PIPE_END__NAME, or POINT_ASSET__NAME.
            - Additional keys specific to the node type, which are required for the appropriate
              merge operation.

        Returns:
        --------
        tuple
            A tuple containing:
            - pipe_node_data : dict
                A dictionary representing the configured pipe node data after merging.
            - asset_node_data : dict
                A dictionary representing the configured asset node data after merging, if applicable.
                This will be empty if the node type is not a point asset.

        Raises:
        -------
        Exception
            If the node type is not recognized or is invalid, an exception is raised with a message
            indicating the invalid node type.

        Notes:
        ------
        This function delegates the actual merging process to helper methods such as
        `_merge_pipe_junction_node`, `_merge_pipe_end_node`, and `_merge_point_asset_node`
        based on the node type. It is a central part of the pipeline and asset management
        process, ensuring that nodes are appropriately configured before further analysis
        or processing.
        """

        asset_node_data = {}
        if node["node_type"] == PIPE_JUNCTION__NAME:
            pipe_node_data = self._merge_pipe_junction_node(node)
        elif node["node_type"] == PIPE_END__NAME:
            pipe_node_data = self._merge_pipe_end_node(node)
        elif node["node_type"] == POINT_ASSET__NAME:
            pipe_node_data, asset_node_data = self._merge_point_asset_node(node)
        else:
            raise Exception(f"Invalid node_type ({node['node_type']}) detected.")

        return pipe_node_data, asset_node_data

    @staticmethod
    def _merge_all_pipe_node_props(default_props: dict, pipe_node_data: dict) -> dict:
        """
        Merge default properties with specific pipe node data and ensure network node labeling.

        This static method combines a set of default properties with the specific data for a pipe node.
        After merging, it ensures that the "NETWORK_NODE__LABEL" is included in the node's labels.
        If the "node_labels" key does not exist, it initializes it with the "NETWORK_NODE__LABEL".

        Parameters:
        -----------
        default_props : dict
            A dictionary containing default properties that should be applied to the pipe node.

        pipe_node_data : dict
            A dictionary containing specific data for the pipe node, which may include
            existing labels and other node-specific properties.

        Returns:
        --------
        dict
            A dictionary containing the merged properties from `default_props` and `pipe_node_data`.
            The resulting dictionary will include a "node_labels" key, ensuring that the "NETWORK_NODE__LABEL"
            is present.

        Notes:
        ------
        This method uses the `|` operator to merge the dictionaries, a feature available in Python 3.9 and later.
        It is designed to handle cases where node labels might be missing, ensuring consistency in labeling
        across the pipeline nodes.
        """

        all_pipe_node_data = default_props | pipe_node_data

        try:
            all_pipe_node_data["node_labels"].append(NETWORK_NODE__LABEL)
        except KeyError:
            all_pipe_node_data["node_labels"] = [NETWORK_NODE__LABEL]

        return all_pipe_node_data

    @staticmethod
    def _merge_all_asset_node_props(default_props: dict, asset_node_data: dict) -> dict:
        """
        Merge default properties with specific asset node data and ensure network node labeling.

        This static method combines a set of default properties with specific data for an asset node,
        if the asset node data is provided. After merging, it ensures that the "NETWORK_NODE__LABEL"
        is included in the node's labels. If no asset node data is provided, an empty dictionary is returned.

        Parameters:
        -----------
        default_props : dict
            A dictionary containing default properties that should be applied to the asset node.

        asset_node_data : dict, optional
            A dictionary containing specific data for the asset node, which may include
            existing labels and other node-specific properties. This parameter may be empty.

        Returns:
        --------
        dict
            A dictionary containing the merged properties from `default_props` and `asset_node_data`.
            The resulting dictionary will include a "node_labels" key with the "NETWORK_NODE__LABEL" appended.
            If `asset_node_data` is empty, an empty dictionary is returned.

        Notes:
        ------
        This method uses the `|` operator to merge the dictionaries, a feature available in Python 3.9 and later.
        It ensures that asset nodes are properly labeled as network nodes when asset data is provided.
        """

        all_asset_node_data = {}
        if asset_node_data:
            all_asset_node_data = default_props | asset_node_data
            all_asset_node_data["node_labels"].append(NETWORK_NODE__LABEL)

        return all_asset_node_data

    def _create_pipe_asset_nodes(self, cnodes: list) -> tuple:
        """
        Create and configure nodes for pipes and associated assets, including utility and DMA data.

        This function processes a list of node dictionaries (cnodes) to create and configure both
        pipe nodes and asset nodes within a network. It handles the special case where an asset node
        occurs at a non-termini of a pipe, marking it as such and creating a pipe-junction if necessary.
        The function then merges default properties with the specific node data, generating utility
        and DMA data along the way.

        Parameters:
        -----------
        cnodes : list
            A list of dictionaries, where each dictionary represents a node in the network.
            Each node should include details such as node type, asset label, and other relevant
            attributes necessary for configuring the nodes.

        Returns:
        --------
        tuple
            A tuple containing:
            - all_pipe_node_data : dict
                A dictionary containing the merged and configured properties for the pipe nodes.

            - all_asset_node_data : dict
                A dictionary containing the merged and configured properties for the asset nodes.

            - all_dma_data : list
                A list of dictionaries representing the DMA (District Metered Area) data associated
                with the nodes.

            - all_utility_data : list
                A list of dictionaries representing the utility data associated with the nodes.

            - all_asset_node_labels : list
                A list of labels for all asset nodes identified and processed.

        Notes:
        ------
        - The function first applies default properties to each node and then checks if a single
          asset node exists at a non-termini of a pipe, marking it for special handling.
        - It reconfigures nodes based on their type, merging appropriate properties and generating
          utility and DMA data.
        - The resulting data structures are comprehensive, capturing both pipe and asset node
          information for further processing or analysis within the network.
        """

        default_props = self._set_network_node_default_props(cnodes)

        ### check if an asset node occurs at the
        ### non-termini of a pipe. We have do this
        ### to create a pipe-junction at this point.
        if (len(cnodes) == 1) and (cnodes[0]["node_type"] == POINT_ASSET__NAME):
            cnodes[0]["is_non_termini_asset_node"] = True

        all_pipe_node_data = {}
        all_asset_node_data = {}
        all_asset_node_labels = []
        all_dma_data = []
        all_utility_data = []
        for node in cnodes:

            pipe_node_data, asset_node_data = self._reconfigure_nodes(node)

            if pipe_node_data:
                all_pipe_node_data = self._merge_all_pipe_node_props(
                    default_props, pipe_node_data
                )
                utility_data = self.create_utility_data(all_pipe_node_data)
                dma_data = self.create_dma_data(all_pipe_node_data)
                all_utility_data.extend(utility_data)
                all_dma_data.extend(dma_data)

            if asset_node_data:
                all_asset_node_data = self._merge_all_asset_node_props(
                    default_props, asset_node_data
                )

                all_asset_node_labels.append(node["asset_label"])
                utility_data = self.create_utility_data(all_asset_node_data)
                dma_data = self.create_dma_data(all_asset_node_data)
                all_utility_data.extend(utility_data)
                all_dma_data.extend(dma_data)

        return (
            all_pipe_node_data,
            all_asset_node_data,
            all_dma_data,
            all_utility_data,
            all_asset_node_labels,
        )

    @staticmethod
    def _create_pipe_node_to_asset_node_edge(
        pipe_node: dict, asset_nodes_for_pipe_node: list
    ):
        """
        Create edges that connect a pipe node to associated asset nodes.

        This static method generates a list of edges representing connections between a given
        pipe node and its associated asset nodes. Each edge is represented as a dictionary containing
        the keys for the connected nodes and a unique edge key that identifies the connection.

        Parameters:
        -----------
        pipe_node : dict
            A dictionary representing the pipe node. Expected to contain a "node_key" that uniquely
            identifies the pipe node within the network.

        asset_nodes_for_pipe_node : list
            A list of dictionaries, where each dictionary represents an asset node associated with
            the pipe node. Each asset node is expected to have a "node_key" that uniquely identifies
            it within the network.

        Returns:
        --------
        list
            A list of dictionaries, where each dictionary represents an edge connecting the pipe node
            to an asset node. Each edge dictionary contains the following keys:
            - "from_node_key": The node key of the pipe node.
            - "to_node_key": The node key of the associated asset node.
            - "edge_key": A unique key representing the connection, formatted as "from_node_key-to_node_key".

        Notes:
        ------
        This method is useful for constructing a graph-like data structure where pipe nodes are connected
        to their corresponding asset nodes. The edge key ensures that each connection can be uniquely
        identified and referenced within the network.
        """
        edges = []

        from_node_key = pipe_node["node_key"]
        for asset_node in asset_nodes_for_pipe_node:
            to_node_key = asset_node["node_key"]
            edges.append(
                {
                    "from_node_key": from_node_key,
                    "to_node_key": to_node_key,
                    "edge_key": f"{from_node_key}-{to_node_key}",
                }
            )
        return edges

    def _set_network_node_and_edge_data(self, consolidated_nodes: list) -> tuple:
        """
        Set and configure network nodes and edges based on consolidated node positions.

        This function processes consolidated nodes to generate and organize network nodes
        (both pipe and asset nodes), as well as the edges that connect pipe nodes to associated
        asset nodes. Additionally, it compiles related data such as DMA information, utility data,
        and asset node labels.

        Parameters:
        -----------
        consolidated_nodes : list
            A list of consolidated nodes, where each item in the list is a group of nodes that
            share the same position along the pipeline. Each group is processed to configure
            pipe and asset nodes, and to establish the connections (edges) between them.

        Returns:
        --------
        tuple
            A tuple containing the following elements:
            - pipe_nodes : list
                A list of dictionaries, each representing a configured pipe node.

            - asset_nodes : list
                A list of lists, where each inner list contains dictionaries representing asset
                nodes associated with the corresponding pipe node.

            - pipe_asset_edges : list
                A list of dictionaries, where each dictionary represents an edge connecting a pipe node
                to an asset node, including keys for both nodes and an edge identifier.

            - all_dma_data : list
                A list of dictionaries representing DMA (District Metered Area) data associated
                with the nodes.

            - all_utility_data : list
                A list of dictionaries representing utility data associated with the nodes.

            - all_asset_node_labels : list
                A list of labels for all asset nodes identified and processed.

        Notes:
        ------
        - The function iterates through each group of consolidated nodes, creating pipe and asset
          nodes and establishing connections between them using helper functions like
          `_create_pipe_asset_nodes` and `_create_pipe_node_to_asset_node_edge`.
        - It ensures that all relevant data, including DMA and utility data, is aggregated and
          returned for further analysis or processing within the network framework.


            consolidated_nodes: list of nodes on a pipe ordered based on
            position from the start of the line. Each element is a list
            contains all pipe_junctions/assets or pipe_ends/assets at the
            same coordinates and this sublist has no order.

            cnodes: The pipe_junctions/assets or pipe_ends/assets at the
            same coordinates. There should only be one pipe_junction or pipe_end node.
            There can be any number of asset nodes. Has no particular order.

        """

        pipe_nodes: list = []
        asset_nodes: list = []
        pipe_asset_edges: list = []
        all_dma_data: list = []
        all_utility_data: list = []
        all_asset_node_labels: list = []

        for cnodes in consolidated_nodes:
            asset_nodes.append([])

            (
                pipe_node_data,
                asset_node_data,
                dma_data,
                utility_data,
                asset_node_labels,
            ) = self._create_pipe_asset_nodes(cnodes)

            if pipe_node_data:
                pipe_nodes.append(pipe_node_data)

            if asset_node_data:
                asset_nodes[-1].append(asset_node_data)

            ### create edges between junction/end node and the asset nodes
            ### that are at the same position
            pipe_asset_edges.extend(
                self._create_pipe_node_to_asset_node_edge(
                    pipe_nodes[-1], asset_nodes[-1]
                )
            )

            all_dma_data.extend(dma_data)
            all_utility_data.extend(utility_data)
            all_asset_node_labels.extend(asset_node_labels)

        return (
            pipe_nodes,
            asset_nodes,
            pipe_asset_edges,
            all_dma_data,
            all_utility_data,
            all_asset_node_labels,
        )

    def _get_edges_by_pipe(self, base_pipe: dict, nodes_by_pipe: list) -> list:
        """
        Generate edges for a pipeline segment based on the nodes along the pipe.

        This function creates a list of edges representing connections between sequential nodes
        along a pipeline. Each edge is defined by its start and end nodes, as well as various attributes
        related to the pipeline segment, including its geometry, material, diameter, and other properties.
        The function also calculates the length of each edge segment and stores it in Well-Known Text (WKT) format.

        Parameters:
        -----------
        base_pipe : dict
            A dictionary containing information about the pipeline segment, including its geometry
            and various attributes such as material, diameter, and asset labels.

        nodes_by_pipe : list
            A list of dictionaries, where each dictionary represents a node along the pipeline.
            The nodes should be ordered sequentially along the pipe to ensure correct edge creation.

        Returns:
        --------
        list
            A list of dictionaries, where each dictionary represents an edge connecting two nodes
            along the pipeline. Each edge dictionary contains the following keys:
            - "from_node_key": The unique key of the starting node.
            - "to_node_key": The unique key of the ending node.
            - "edge_key": A unique identifier for the edge, formatted as "from_node_key-to_node_key".
            - "tag": The tag associated with the base pipe.
            - "pipe_type": The type of the pipe.
            - "material": The material of the pipe.
            - "diameter": The diameter of the pipe.
            - "asset_name": The name of the pipe asset.
            - "asset_label": The label of the pipe asset.
            - "dma_codes": The DMA codes associated with the pipe.
            - "dma_names": The DMA names associated with the pipe.
            - "dmas": The DMAs associated with the pipe.
            - "segment_length": The length of the pipe segment between the two nodes.
            - "segment_wkt": The WKT (Well-Known Text) representation of the pipe segment's geometry.

        Notes:
        ------
        - The function uses the `line_locate_point` method to determine the location of each node
          along the pipeline's geometry, ensuring accurate edge creation.
        - If the asset label of the base pipe is not already in the `network_edge_labels`, it is added
          to this list for tracking purposes.
        - The edges are created in the order of the nodes, connecting each node to the next sequential node
          along the pipeline.
        """

        edges_by_pipe = []

        from_node = nodes_by_pipe[0]
        for to_node in nodes_by_pipe[1:]:

            from_node_pnt = Point(from_node["coords_27700"])
            to_node_pnt = Point(to_node["coords_27700"])
            line_geom = LineString(base_pipe["geometry"].coords)

            from_location = line_locate_point(line_geom, from_node_pnt)
            to_location = line_locate_point(line_geom, to_node_pnt)

            line_segment = substring(
                line_geom, from_location, to_location, normalized=True
            )

            if base_pipe["asset_label"] not in self.network_edge_labels:
                self.network_edge_labels.append(base_pipe["asset_label"])

            edges_by_pipe.append(
                {
                    "from_node_key": from_node["node_key"],
                    "to_node_key": to_node["node_key"],
                    "edge_key": f"{from_node['node_key']}-{to_node['node_key']}",
                    "tag": base_pipe["tag"],
                    "pipe_type": base_pipe["pipe_type"],
                    "material": base_pipe["material"],
                    "diameter": base_pipe["diameter"],
                    "asset_name": base_pipe["asset_name"],
                    "asset_label": base_pipe["asset_label"],
                    "dma_codes": base_pipe["dma_codes"],
                    "dma_names": base_pipe["dma_names"],
                    "dmas": base_pipe["dmas"],
                    "segment_length": round(line_segment.length, 5),
                    "segment_wkt": line_segment.wkt,
                }
            )
            from_node = to_node

        return edges_by_pipe

    def _set_nodes_and_edges(self, base_pipe, nodes_ordered):
        """
        Configure and create nodes and edges for a pipeline segment based on ordered nodes.

        This function processes a list of ordered nodes along a pipeline to create and consolidate
        network nodes, establish connections (edges) between these nodes, and generate additional
        data such as DMA (District Metered Area) information, utility data, and asset labels. The
        function returns a comprehensive set of data structures representing the nodes, edges, and
        associated properties for further analysis or processing.

        Parameters:
        -----------
        base_pipe : dict
            A dictionary containing information about the pipeline segment, including its geometry
            and various attributes such as material, diameter, and asset labels.

        nodes_ordered : list
            A list of dictionaries representing nodes along the pipeline. The nodes should be ordered
            sequentially based on their positions along the pipeline.

        Returns:
        --------
        tuple
            A tuple containing the following elements:
            - nodes_by_pipe : list
                A list of dictionaries representing the consolidated and configured nodes along the pipeline.

            - edges_by_pipe : list
                A list of dictionaries representing the edges connecting sequential nodes along the pipeline,
                including information about the pipeline segment and its properties.

            - asset_nodes_by_pipe : list
                A list of lists, where each inner list contains dictionaries representing asset nodes associated
                with the corresponding pipe node.

            - pipe_node_to_asset_node_edges : list
                A list of dictionaries representing the edges connecting pipe nodes to associated asset nodes.

            - dma_data : list
                A list of dictionaries representing DMA (District Metered Area) data associated with the nodes.

            - utility_data : list
                A list of dictionaries representing utility data associated with the nodes.

            - all_asset_node_labels : list
                A list of labels for all asset nodes identified and processed.

        Notes:
        ------
        - The function begins by consolidating nodes that are positioned at the same location along
          the pipeline using `_consolidate_nodes_on_position`.
        - It then configures the nodes and edges through `_set_network_node_and_edge_data`, which
          handles the creation of both pipe and asset nodes as well as their connections.
        - Finally, it creates edges between junction and end nodes for the pipeline segment using
          `_get_edges_by_pipe`, ensuring that all relevant data is aggregated and returned for further
          processing within the network framework.
        """

        consolidated_nodes = self._consolidate_nodes_on_position(nodes_ordered)

        (
            nodes_by_pipe,
            asset_nodes_by_pipe,
            pipe_node_to_asset_node_edges,
            dma_data,
            utility_data,
            all_asset_node_labels,
        ) = self._set_network_node_and_edge_data(consolidated_nodes)

        # create edges between junction and end nodes for the pipe
        edges_by_pipe = self._get_edges_by_pipe(base_pipe, nodes_by_pipe)

        return (
            nodes_by_pipe,
            edges_by_pipe,
            asset_nodes_by_pipe,
            pipe_node_to_asset_node_edges,
            dma_data,
            utility_data,
            all_asset_node_labels,
        )

    def _get_base_pipe_data(self, qs_object) -> dict:
        """
        Extract and organize the base data for a pipeline segment from a queryset object.

        This function retrieves various attributes related to a pipeline segment from a Django queryset object
        and organizes them into a dictionary. The resulting dictionary, `base_pipe`, contains key information
        about the pipe, including its geometry, material, diameter, and associated District Metered Areas (DMAs)
        and utilities. It also handles the collection of intersection data at the start and end points of the pipe.

        Parameters:
        -----------
        qs_object : Django queryset object
            A queryset object representing a single pipeline segment. This object should contain attributes
            such as primary key, tag, pipe type, asset name, geometry, and intersection data.

        Returns:
        --------
        dict
            A dictionary containing the extracted data for the pipeline segment, with the following keys:
            - "id": The primary key of the pipeline segment.
            - "tag": The tag associated with the pipeline segment.
            - "pipe_type": The type of the pipe.
            - "asset_name": The name of the pipe asset.
            - "asset_label": The label of the pipe asset.
            - "pipe_length": The length of the pipe.
            - "wkt": The Well-Known Text (WKT) representation of the pipe's geometry.
            - "material": The material of the pipe.
            - "diameter": The diameter of the pipe.
            - "dma_ids": The IDs of the associated District Metered Areas (DMAs).
            - "dma_codes": The codes of the associated DMAs.
            - "dma_names": The names of the associated DMAs.
            - "dmas": A JSON representation of the DMA data, built from the DMA codes and names.
            - "utilities": The names of utilities associated with the pipeline.
            - "geometry": The geometric data of the pipeline segment.
            - "start_point_geom": The geometry of the pipeline's start point.
            - "end_point_geom": The geometry of the pipeline's end point.
            - "line_start_intersection_tags": A list of tags from the intersections at the start of the pipe.
            - "line_start_intersection_ids": A list of IDs from the intersections at the start of the pipe.
            - "line_end_intersection_tags": A list of tags from the intersections at the end of the pipe.
            - "line_end_intersection_ids": A list of IDs from the intersections at the end of the pipe.

        Notes:
        ------
        - The function uses the `build_dma_data_as_json` method to compile the DMA data into a JSON structure.
        - It handles intersection data separately for the start and end points of the pipe, collecting both tags and IDs.
        """

        base_pipe: dict = {}

        base_pipe["id"] = qs_object.pk
        base_pipe["tag"] = qs_object.tag
        base_pipe["pipe_type"] = qs_object.pipe_type
        base_pipe["asset_name"] = qs_object.AssetMeta.asset_name
        base_pipe["asset_label"] = qs_object.AssetMeta.asset_name
        base_pipe["pipe_length"] = qs_object.geometry.length
        base_pipe["wkt"] = qs_object.geometry.wkt
        base_pipe["material"] = qs_object.material
        base_pipe["diameter"] = qs_object.diameter
        
        dmas = qs_object.dmas.all()
        base_pipe["dma_ids"] = [dma.id for dma in dmas]
        base_pipe["dma_codes"] = [dma.code for dma in dmas]
        base_pipe["dma_names"] = [dma.name for dma in dmas]
        base_pipe["dmas"] = self.build_dma_data_as_json(
            base_pipe["dma_codes"], base_pipe["dma_names"]
        )

        base_pipe["utilities"] = [dma.utility.name for dma in dmas]
        base_pipe["geometry"] = qs_object.geometry
        base_pipe["start_point_geom"] = Point(qs_object.geometry.coords[0])
        base_pipe["end_point_geom"] = Point(qs_object.geometry.coords[-1])

        base_pipe["line_start_intersection_tags"] = []
        base_pipe["line_start_intersection_ids"] = []
        base_pipe["line_end_intersection_tags"] = []
        base_pipe["line_end_intersection_ids"] = []

        return base_pipe

    def _combine_all_pipe_junctions(self, pipe_qs_object) -> list:
        # This method is problematic as it assumes a pre-fetched attribute.
        # For now, we will return an empty list as junctions are handled by intersections.
        return []

    def _combine_all_point_assets(self, pipe_qs_object) -> list:
        from cwageodjango.assets.models import Hydrant, NetworkOptValve

        assets = []
        
        # A more robust implementation would use a model registry
        # to avoid hardcoding model names here.
        asset_models = {
            "hydrant": Hydrant,
            "network_opt_valve": NetworkOptValve,
        }

        for asset_name in self.point_asset_names:
            if asset_name in asset_models:
                model = asset_models[asset_name]
                # Find assets that intersect with the pipe's geometry
                intersecting_assets = model.objects.filter(
                    geometry__intersects=pipe_qs_object.geometry
                )
                assets.extend(intersecting_assets)

        return assets

    @staticmethod
    def _get_intersecting_geometry(
        base_pipe_geom: GEOSGeometry, wkt: str, srid: int
    ) -> GEOSGeometry:
        """
        Calculate the intersection geometry between a base pipeline segment and another geometric object.

        This static method determines the intersection between the geometry of a base pipeline segment
        and another geometric object, which could be either a line (another pipeline) or a point asset.
        The method returns the intersecting geometry, which may be a point, multipoint, or the original
        point asset geometry.

        Parameters:
        -----------
        base_pipe_geom : GEOSGeometry
            The geometric representation of the base pipeline segment. This should be a GEOSGeometry object.

        wkt : str
            The Well-Known Text (WKT) representation of the geometry of the intersecting pipe or asset.

        srid : int
            The Spatial Reference System Identifier (SRID) for the coordinate system used in the geometries.

        Returns:
        --------
        GEOSGeometry
            A GEOSGeometry object representing the intersection of the base pipeline segment with the
            intersecting geometry. This could be a single point, multipoint, or the original point geometry
            if the intersecting object is a point asset.

        Raises:
        -------
        Exception
            If the geometry type of the intersecting object is not recognized as a line or point, an exception
            is raised indicating the valid GEOS geometry types.

        Notes:
        ------
        - The function first checks whether the intersecting geometry is a line (e.g., another pipeline).
          If so, it calculates the intersection between the two lines, which may result in a single point
          or a multipoint geometry.
        - If the intersecting geometry is a point (e.g., a point asset), it directly returns this point geometry.
        - The function ensures that only valid GEOS geometry types are processed, raising an exception if
          an unrecognized type is encountered.
        """

        # Geom of the intersecting pipe or asset
        pipe_or_asset_geom = GEOSGeometry(wkt, srid)

        # if pipe_or_asset_geom is a line then get the intersection point of the two lines
        if pipe_or_asset_geom.geom_typeid in GEOS_LINESTRING_TYPES:
            # __intersection__ may return a single or multipoint object
            return base_pipe_geom.intersection(pipe_or_asset_geom)

        # otherwise if it is a point asset then get the point asset intersection
        elif pipe_or_asset_geom.geom_typeid in GEOS_POINT_TYPES:
            return pipe_or_asset_geom

        else:
            raise Exception(
                f"Invalid GEOS line string type. Allowed types are {(',').join(str(x) for x in GEOS_LINESTRING_TYPES+GEOS_POINT_TYPES)}"
            )

    def _map_get_normalised_positions(
        self, base_pipe_geom: GEOSGeometry, junction_or_asset: dict
    ) -> list:
        """
        Calculate and map the normalized positions of junctions or assets along a pipeline segment.

        This function computes the intersection between a pipeline segment's geometry and a junction
        or asset's geometry, and then determines the normalized positions and distances of these
        intersections relative to the start of the pipeline. The result is a list of dictionaries,
        each containing the calculated intersection points, distances, and normalized positions.

        Parameters:
        -----------
        base_pipe_geom : GEOSGeometry
            The geometric representation of the base pipeline segment. This should be a GEOSGeometry object.

        junction_or_asset : dict
            A dictionary containing information about the junction or asset, including its WKT geometry
            and other relevant attributes.

        Returns:
        --------
        list
            A list of dictionaries, each representing an intersection between the pipeline segment and
            the junction or asset. Each dictionary contains the following keys:
            - "intersection_point_geometry": The GEOSGeometry object representing the intersection point.
            - "distance_from_pipe_start_cm": The distance from the start of the pipeline to the intersection
              point, measured in centimeters.
            - "normalised_position": The normalized position of the intersection point along the pipeline.
            - Other keys from the `junction_or_asset` dictionary.

        Raises:
        -------
        Exception
            If the intersection geometry is neither a point nor a multipoint, an exception is raised indicating
            the allowed geometry types.

        Notes:
        ------
        - The function first determines the intersection geometry using the `_get_intersecting_geometry` method.
        - It handles both single points and multipoints:
            - For single points, it calculates the normalized position and distance, then returns a list with
              a single dictionary.
            - For multipoints, it iterates through each point, calculating and returning a list of dictionaries
              representing each intersection.
        - If the intersection geometry is invalid (i.e., not a point or multipoint), the function raises an
          exception to indicate the error.
        - The function can optionally transform the intersection geometry to SRID 4326 if `neoj4_point` is set.
        """

        intersection_geom = self._get_intersecting_geometry(
            base_pipe_geom, junction_or_asset["wkt"], self.srid
        )

        if self.neoj4_point:
            intersection_geom_4326 = intersection_geom.transform(4326, clone=True)

        if intersection_geom.geom_type == "Point":
            intersection_params = normalised_point_position_on_line(
                base_pipe_geom, intersection_geom.coords
            )
            data = [
                {
                    **junction_or_asset,
                    "intersection_point_geometry": intersection_geom,
                    # distance returned is based on srid and should be in meters.
                    # Convert to cm and round.
                    "distance_from_pipe_start_cm": round(intersection_params[0] * 100),
                    "normalised_position": intersection_params[1],
                }
            ]

        elif intersection_geom.geom_type == "MultiPoint":
            data = []
            for coords in intersection_geom.coords:
                intersection_params = normalised_point_position_on_line(
                    base_pipe_geom,
                    coords,
                )
                data.append(
                    {
                        **junction_or_asset,
                        "intersection_point_geometry": GEOSGeometry(
                            f"POINT ({coords[0]} {coords[1]})", self.srid
                        ),
                        # distance returned is based on srid and should be in meters.
                        # Convert to cm and round.
                        "distance_from_pipe_start_cm": round(
                            intersection_params[0] * 100
                        ),
                        "normalised_position": intersection_params[1],
                    }
                )

        else:
            raise Exception(
                "Invalid geometry types for intersection. Allowed types are point and multipoint"
            )

        return data

    def _get_connections_points_on_pipe(
        self, base_pipe: dict, intersected_objects: list
    ) -> list:
        """
        Calculate the intersection points of objects along a pipeline and map their positions.

        This function identifies the intersection points between a base pipeline segment and a list
        of intersected objects (such as junctions or assets). It computes the normalized positions and
        distances of these intersection points relative to the start of the pipeline and returns a list
        of these intersections.

        Parameters:
        -----------
        base_pipe : dict
            A dictionary containing information about the base pipeline segment, including its geometry
            under the key "geometry".

        intersected_objects : list
            A list of dictionaries, where each dictionary represents an object (e.g., a junction or asset)
            that intersects with the pipeline. Each object should include its geometry and other relevant
            attributes.

        Returns:
        --------
        list
            A list of dictionaries, where each dictionary represents an intersection point between the pipeline
            and an intersected object. Each dictionary contains the following keys:
            - "intersection_point_geometry": The GEOSGeometry object representing the intersection point.
            - "distance_from_pipe_start_cm": The distance from the start of the pipeline to the intersection
              point, measured in centimeters.
            - "normalised_position": The normalized position of the intersection point along the pipeline.
            - Other keys from the intersected object dictionary.

        Notes:
        ------
        - The function iterates over each object in the `intersected_objects` list, using the `_map_get_normalised_positions`
          method to calculate the intersection details for each object.
        """

        object_intersections = []

        # Not inefficient to use for loop with append here as the number
        # of intersecting junctions_and_assets for any given base pipe is not large
        for ja in intersected_objects:
            intersection = self._map_get_normalised_positions(base_pipe["geometry"], ja)
            object_intersections += intersection

        return object_intersections

    @staticmethod
    def _get_non_termini_intersecting_pipes(base_pipe, junctions_with_positions):
        termini_intersecting_pipe_tags = (
            base_pipe["line_start_intersection_tags"]
            + base_pipe["line_end_intersection_tags"]
        )

        non_termini_intersecting_pipes = [
            pipe
            for pipe in junctions_with_positions
            if pipe["tag"] not in termini_intersecting_pipe_tags
        ]

        # non_termini_intersecting_pipes.append(
        #     {
        #         "id": 1,
        #         "tag": 88888888,
        #         "distance_from_pipe_start_cm": 73,
        #         "intersection_point_geometry": base_pipe["start_point_geom"],
        #     }
        # )
        # non_termini_intersecting_pipes.append(
        #     {
        #         "id": 2,
        #         "tag": 333333,
        #         "distance_from_pipe_start_cm": 50,
        #         "intersection_point_geometry": base_pipe["start_point_geom"],
        #     }
        # )
        # non_termini_intersecting_pipes.append(
        #     {
        #         "id": 3,
        #         "tag": 999999,
        #         "distance_from_pipe_start_cm": 50,
        #         "intersection_point_geometry": base_pipe["start_point_geom"],
        #     }
        # )
        # non_termini_intersecting_pipes.append(
        #     {
        #         "id": 4,
        #         "tag": 77777,
        #         "distance_from_pipe_start_cm": 73,
        #         "intersection_point_geometry": base_pipe["start_point_geom"],
        #     }
        # )
        # non_termini_intersecting_pipes.append(
        #     {
        #         "id": 5,
        #         "tag": 111111,
        #         "distance_from_pipe_start_cm": 73,
        #         "intersection_point_geometry": base_pipe["start_point_geom"],
        #     }
        # )
        # non_termini_intersecting_pipes.append(
        #     {
        #         "id": 6,
        #         "tag": 222222,
        #         "distance_from_pipe_start_cm": 35,
        #         "intersection_point_geometry": base_pipe["start_point_geom"],
        #     }
        # )

        return non_termini_intersecting_pipes

    def _set_terminal_nodes(self, base_pipe):
        start_node_distance_cm = 0
        # round to int to make distance comparisons more robust
        end_node_distance_cm = round(base_pipe["pipe_length"] * 100)

        line_start_intersection_tags = base_pipe["line_start_intersection_tags"]
        line_end_intersection_tags = base_pipe["line_end_intersection_tags"]

        start_node_tags = sorted([base_pipe["tag"], *line_start_intersection_tags])
        end_node_tags = sorted([base_pipe["tag"], *line_end_intersection_tags])

        if not line_start_intersection_tags:
            start_node_type = PIPE_END__NAME
        else:
            start_node_type = PIPE_JUNCTION__NAME

        if not line_end_intersection_tags:
            end_node_type = PIPE_END__NAME
        else:
            end_node_type = PIPE_JUNCTION__NAME

        nodes_ordered = [
            {
                "pipe_tags": start_node_tags,
                "node_type": start_node_type,
                "distance_from_pipe_start_cm": start_node_distance_cm,
                "dma_codes": base_pipe["dma_codes"],
                "dma_names": base_pipe["dma_names"],
                "dmas": base_pipe["dma_codes"],
                "intersection_point_geometry": base_pipe["start_point_geom"],
                "utility_name": self._get_utility(base_pipe),
                **base_pipe,
            },
            {
                "pipe_tags": end_node_tags,
                "node_type": end_node_type,
                "distance_from_pipe_start_cm": end_node_distance_cm,
                "dma_codes": base_pipe["dma_codes"],
                "dma_names": base_pipe["dma_names"],
                "dmas": base_pipe["dma_codes"],
                "intersection_point_geometry": base_pipe["end_point_geom"],
                "utility_name": self._get_utility(base_pipe),
                **base_pipe,
            },
        ]

        return nodes_ordered

    def _set_non_terminal_nodes(
        self, base_pipe, nodes_ordered, non_termini_intersecting_pipes
    ):
        distances = [x["distance_from_pipe_start_cm"] for x in nodes_ordered]

        position_index = 0
        for pipe in non_termini_intersecting_pipes:
            pipe_tag = pipe["tag"]
            # distance_from_start_cm must be an
            # int for sqid compatible hashing
            distance_from_pipe_start_cm = pipe["distance_from_pipe_start_cm"]

            tags = sorted([pipe_tag, base_pipe["tag"]])
            if distance_from_pipe_start_cm not in distances:

                position_index = bisect.bisect_right(
                    nodes_ordered,
                    distance_from_pipe_start_cm,
                    key=lambda x: x["distance_from_pipe_start_cm"],
                )

                nodes_ordered.insert(
                    position_index,
                    {
                        "pipe_tags": tags,
                        "node_type": PIPE_JUNCTION__NAME,
                        "utility_name": self._get_utility(base_pipe),
                        "distance_from_pipe_start_cm": distance_from_pipe_start_cm,
                        "dma_codes": base_pipe["dma_codes"],
                        "dma_names": base_pipe["dma_names"],
                        "dmas": base_pipe["dmas"],
                        "intersection_point_geometry": pipe[
                            "intersection_point_geometry"
                        ],
                        **base_pipe,
                    },
                )

                distances.append(distance_from_pipe_start_cm)
            else:
                nodes_ordered[position_index]["pipe_tags"].append(pipe_tag)
                nodes_ordered[position_index]["pipe_tags"] = sorted(
                    nodes_ordered[position_index]["pipe_tags"]
                )

        return nodes_ordered

    def _set_point_asset_properties(
        self, base_pipe, nodes_ordered, point_assets_with_positions
    ):

        for asset in point_assets_with_positions:

            # TODO: node_key may not be unique between assets. FIX by defining an asset_code
            bisect.insort(
                nodes_ordered,
                {
                    "distance_from_pipe_start_cm": asset["distance_from_pipe_start_cm"],
                    "node_type": POINT_ASSET__NAME,
                    "dma_codes": base_pipe["dma_codes"],
                    "dma_names": base_pipe["dma_names"],
                    "dmas": base_pipe["dmas"],
                    "utility_name": self._get_utility(base_pipe),
                    **asset,
                },
                key=lambda x: x["distance_from_pipe_start_cm"],
            )

        return nodes_ordered

    def _set_node_properties(
        self, base_pipe, junctions_with_positions, point_assets_with_positions
    ):
        non_termini_intersecting_pipes = self._get_non_termini_intersecting_pipes(
            base_pipe, junctions_with_positions
        )

        nodes_ordered = self._set_terminal_nodes(base_pipe)

        nodes_ordered = self._set_non_terminal_nodes(
            base_pipe, nodes_ordered, non_termini_intersecting_pipes
        )

        nodes_ordered = self._set_point_asset_properties(
            base_pipe, nodes_ordered, point_assets_with_positions
        )

        # self._calc_pipe_length_between_nodes(nodes_ordered)

        return nodes_ordered

    def get_srid(self):
        """Get the currently used global srid"""
        return self.srid

    @staticmethod
    def get_pipe_count(qs) -> QuerySet:
        """Get the number of pipes in the provided queryset.
        Will make a call to the db. Strictly speaking will
        return the count of any queryset.

        Params:
              qs (Queryset). A queryset (preferably a union of all the pipe data)

        Returns:
              int: The queryset count:
        """

        return qs.count()

    @staticmethod
    def _get_utility(qs_object):
        utilities = list(set(qs_object["utilities"]))

        if len(utilities) > 1:
            raise Exception(
                f"{qs_object} is located in multiple utilities. It should only be within one"
            )
        return utilities[0]

    @staticmethod
    def build_dma_data_as_json(dma_codes, dma_names):
        dma_data = [
            {"code": dma_code, "name": dma_name}
            for dma_code, dma_name in zip(dma_codes, dma_names)
        ]

        return json.dumps(dma_data)

    def _encode_node_key(self, point, extra_params=[]):
        """
        Round and cast Point geometry coordinates to str to remove '.'
        then return back to int to make make coords sqid compatible.

        Note these are not coordinates but int representations of the
        coordinates to ensure a unique node_key.
        """

        coord1_repr = int(str(round(point.x, 3)).replace(".", ""))
        coord2_repr = int(str(round(point.y, 3)).replace(".", ""))
        return self.sqids.encode([coord1_repr, coord2_repr, *extra_params])
