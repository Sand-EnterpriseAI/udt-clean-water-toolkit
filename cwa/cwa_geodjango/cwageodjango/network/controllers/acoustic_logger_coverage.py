from cwageodjango.network.models import *
from neomodel import db
import csv
import pandas as pd


class AcousticLoggerCoverage:
    def __init__(self, config):
        self.config = config
        self.detection_dist = {
            "Steel": 150,
            "Ductile Iron": 150,
            "Unknown": 150,
            "Cast Iron": 150,
            "Medium Density Polyethylene": 70,
            "High Performance Polyethylene": 70,
            "Polyolefin": 70,
            "Glass Reinforced Plastic": 70,
            "Unplasticized Polyvinyl Chloride": 70,
            "Concrete": 150,
            "Stainless Steel": 150,
            "Asbestos Cement": 70,
            "Concrete Steel": 150,
            "Other": 150,
            "Mild Steel Epoxy Coated": 70,
            "Low Density Polyethylene": 70,
            "Bituminous": 70,
            "Polyvinyl Chloride": 70,
            "Brick": 70,
            "Fiberglass": 70,
            "Copper": 150,
            "Galvanized Iron": 150,
            "Aluminium": 150,
            "Plastic": 70,
            "Glass": 70,
            "High Density Polyethylene": 70,
            "Polyethylene": 70,
            "Polyethylene Aluminium Composite": 150,
            "Polyurethane": 70,
            "Lead": 150,
            "Vinyl Chloride": 70,
            "Polypropylene": 70,
            "Steel High Pressure Polyethylene": 150,
            "Marble": 70,
            "None": 150,
        }

    def initialise_csv(self):
        with open(self.config.outputfile, mode="w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(
                [
                    "utility",
                    "dma",
                    "logger_node_key",
                    "logger_gid",
                    "logger_coords",
                    "pipe_id",
                    "pipe_tag",
                    "pipe_material",
                    "pipe_length",
                    "coverage_length",
                    "pipe_wkt",
                    "start_node_key",
                    "start_node_coords",
                    "end_node_key",
                    "end_node_coords",
                ]
            )

    def get_next_edges(self, node_key, processed_edges):
        processed_nodes_condition = ""
        if processed_edges:
            processed_nodes_condition = "AND NOT m.node_key IN " + str(
                list(processed_edges)
            )

        cypher_query = f"""MATCH (n:NetworkNode {{node_key : '{node_key}'}})-[r:PipeMain]-(m:NetworkNode) WHERE NOT id(r) IN {list(processed_edges)} {processed_nodes_condition} RETURN n,r,m;"""

        results, _ = db.cypher_query(cypher_query)
        return results

    def update_edge_attributes(
        self,
        start_node_key,
        end_node_key,
        logger_key,
        logger_gid,
        logger_coords,
        coverage_len,
    ):
        query = f"""
                    MATCH (n:NetworkNode {{node_key: '{start_node_key}'}})-[:IN_UTILITY]->(u:Utility), 
                        (n:NetworkNode {{node_key: '{start_node_key}'}})-[:IN_DMA]->(d:DMA), 
                        (n:NetworkNode {{node_key: '{start_node_key}'}})-[r:PipeMain]-(m:NetworkNode {{node_key: '{end_node_key}'}})
                    WITH r, 
                        CASE WHEN r.coveredbyLogger IS NOT NULL THEN r.coveredbyLogger + '|' + '{logger_key}' ELSE '{logger_key}' END AS newCoveredByLogger,
                        CASE WHEN r.coverageLen IS NOT NULL THEN r.coverageLen + '|' + '{coverage_len}' ELSE '{coverage_len}' END AS newCoverageLen,
                        n.node_key AS startNodeKey,
                        n.coords_27700 AS startNodeCoords,
                        m.node_key AS endNodeKey,
                        m.coords_27700 AS endNodeCoords,
                        r.tag as pipe_tag,
                        r.material AS PipeMaterial,
                        r.segment_length AS PipeLength,
                        r.segment_wkt AS PipeWkt,
                        u.name AS utility,
                        d.code AS dma
                    SET r.coveredbyLogger = newCoveredByLogger,
                        r.coverageLen = newCoverageLen
                    RETURN utility, dma, id(r) AS pipe_id, pipe_tag,
                        '{coverage_len}' AS coverage_length, 
                        startNodeKey, startNodeCoords, 
                        endNodeKey, endNodeCoords, 
                        PipeMaterial, PipeLength, PipeWkt
                    """
        results, _ = db.cypher_query(query)

        with open(self.config.outputfile, mode="a", newline="") as file:
            writer = csv.writer(file)
            for result in results:
                utility = result[0]
                dma = result[1]
                pipe_id = result[2]
                pipe_tag = result[3]
                coverage_length = result[4]
                start_node_key = result[5]
                start_node_coords = result[6]
                end_node_key = result[7]
                end_node_coords = result[8]
                pipe_material = result[9]
                pipe_length = result[10]
                pipe_wkt = result[11]
                writer.writerow(
                    [
                        utility,
                        dma,
                        logger_key,
                        logger_gid,
                        logger_coords,
                        pipe_id,
                        pipe_tag,
                        pipe_material,
                        pipe_length,
                        coverage_length,
                        pipe_wkt,
                        start_node_key,
                        start_node_coords,
                        end_node_key,
                        end_node_coords,
                    ]
                )

    def check_for_pipe_end(self, node_key):
        query = f"MATCH (n {{node_key : '{node_key}'}}) RETURN 'PipeEnd' IN labels(n) AS is_pipe_end"
        results, _ = db.cypher_query(query)
        is_pipe_end_str = results[0][0]
        return is_pipe_end_str

    def convert_remaining_distance(
        self, remaining_distance, current_material, next_material
    ):
        current_material_distance = self.detection_dist.get(current_material)
        next_material_distance = self.detection_dist.get(next_material)
        converted_distance = (
            remaining_distance / current_material_distance
        ) * next_material_distance
        return converted_distance

    def process_connected_edges(
        self,
        node_key,
        remaining_distance,
        processed_edges,
        processed_nodes,
        pipe_material,
        logger_key,
        logger_gid,
        logger_coords,
        is_initial,
    ):
        if self.check_for_pipe_end(node_key=node_key):
            return

        while remaining_distance > 0:
            processed_nodes.add(node_key)
            next_edges = self.get_next_edges(node_key, processed_edges)

            per_edge_distance = remaining_distance

            for edge in next_edges:
                if "edge_distance" not in locals() or edge_distance == 0:
                    edge_distance = per_edge_distance

                edge_distance = self.convert_remaining_distance(
                    edge_distance, pipe_material, edge[1].get("material")
                )
                start_node_key = edge[1]._start_node.get("node_key")
                end_node_key = edge[1]._end_node.get("node_key")
                pipe_id = edge[1]._id
                pipe_material = edge[1].get("material")
                pipe_length = edge[1].get("segment_length")

                # print(
                #     f"Running for {pipe_id}, {edge_distance} on the edge left, {remaining_distance} in total"
                # )

                if pipe_length > edge_distance:
                    covered_distance = edge_distance
                    remaining_distance -= edge_distance
                    self.update_edge_attributes(
                        start_node_key,
                        end_node_key,
                        logger_key,
                        logger_gid,
                        logger_coords,
                        covered_distance,
                    )

                    processed_edges.add(pipe_id)
                    edge_distance = 0
                    node_key = (
                        end_node_key
                        if start_node_key in processed_nodes
                        else start_node_key
                    )

                    if self.check_for_pipe_end(node_key=node_key):

                        # print(f"Pipe end detected at {node_key}")

                        edge_distance = 0
                        break

                elif pipe_length <= edge_distance:
                    edge_distance -= pipe_length
                    remaining_distance -= pipe_length

                    self.update_edge_attributes(
                        start_node_key,
                        end_node_key,
                        logger_key,
                        logger_gid,
                        logger_coords,
                        pipe_length,
                    )

                    processed_edges.add(pipe_id)

                    if remaining_distance > 0:
                        node_key = (
                            end_node_key
                            if start_node_key in processed_nodes
                            else start_node_key
                        )

                        if self.check_for_pipe_end(node_key=node_key):

                            # print(f"Pipe end detected at {node_key}")

                            edge_distance = 0
                            continue

                    if edge_distance > 0 and remaining_distance > 0:
                        is_initial = False
                        self.process_connected_edges(
                            node_key,
                            remaining_distance,
                            processed_edges,
                            processed_nodes,
                            pipe_material,
                            logger_key,
                            logger_gid,
                            logger_coords,
                            is_initial,
                        )
                    else:
                        break
            else:
                break

    def query_graph_dma_logger_nodes(self, dmas, utilities):
        """
        Generator function to query the graph database for loggers within a specific DMA.

        Parameters:
            dma (str): DMA code to filter loggers.

        Returns:
            results: Result object containing query results.

        """
        loggers, m = db.cypher_query(
            f"""MATCH (n:NetworkNode)-[:IN_UTILITY]-(u:Utility), (n)-[:IN_DMA]-(d:DMA) WHERE u.name IN {utilities} AND d.code IN {dmas} AND n.acoustic_logger = true
             WITH n MATCH (n)-[:HAS_ASSET]-(s:NetworkNode) RETURN n, s"""
        )
        return loggers

    def process_loggers(self, loggers):
        for logger in loggers:
            logger_key = logger[0].get("node_key")
            logger_gid = logger[0].get("tag")
            logger_coords = logger[0].get("coords_27700")
            logger_networknode_key = logger[1].get("node_key")

            connected_edges = self.get_next_edges(logger_networknode_key, set())

            processed_edges = set()
            processed_nodes = set()

            for edge in connected_edges:
                start_node_key = edge[1]._start_node.get("node_key")
                end_node_key = edge[1]._end_node.get("node_key")

                pipe_id = edge[1]._id
                pipe_material = edge[1].get("material")
                pipe_length = edge[1].get("segment_length")
                travel_distance = self.detection_dist.get(pipe_material)

                # print(
                #     "Running for Logger:",
                #     logger_key,
                #     "at ",
                #     logger_networknode_key,
                #     "edge: ",
                #     pipe_id,
                #     travel_distance,
                # )

                if pipe_length <= travel_distance:
                    remaining_distance = travel_distance - pipe_length
                    self.update_edge_attributes(
                        start_node_key,
                        end_node_key,
                        logger_key,
                        logger_gid,
                        logger_coords,
                        pipe_length,
                    )
                    processed_edges.add(pipe_id)
                    processed_nodes.add(logger_networknode_key)

                    if remaining_distance > 0:
                        node_key = (
                            end_node_key
                            if start_node_key in processed_nodes
                            else start_node_key
                        )
                        self.process_connected_edges(
                            node_key,
                            remaining_distance,
                            processed_edges,
                            processed_nodes,
                            pipe_material,
                            logger_key,
                            logger_gid,
                            logger_coords,
                            is_initial=False,
                        )
                elif pipe_length > travel_distance:
                    covered_distance = pipe_length - travel_distance
                    self.update_edge_attributes(
                        start_node_key,
                        end_node_key,
                        logger_key,
                        logger_gid,
                        logger_coords,
                        travel_distance,
                    )
                    continue

    def query_total_pipe_lengths_dma(self, dmas, utilities):
        query = f"""
            MATCH (n:NetworkNode)-[:IN_UTILITY]->(u:Utility), (n)-[:IN_DMA]->(d:DMA)
            WHERE u.name IN {utilities} AND d.code IN {dmas}
            WITH n, u, d
            MATCH (n)-[r:PipeMain]-(m)
            RETURN u.name AS utility, d.code AS dma, sum(r.segment_length) AS total_length;
            """
        results, m = db.cypher_query(query)
        return results

    def calculate_total_pipe_lengths_covered(self, df):
        total_pipe_lengths_covered = 0
        for pipe in df["pipe_id"].unique():
            dftmp = df[df["pipe_id"] == pipe].drop_duplicates()
            pipe_len = dftmp["pipe_length"].iloc[0]
            pipe_cov = dftmp["coverage_length"].sum()
            total_cov = pipe_cov if pipe_cov < pipe_len else pipe_len
            total_pipe_lengths_covered += total_cov
        return total_pipe_lengths_covered

    def summary_statistics(self, outputfile):
        summary_file = str("_summary.csv").join(self.config.outputfile.split(".csv"))
        df = pd.read_csv(outputfile, header=[0])
        dma = self.config.dma_codes
        total_pipe_lengths = self.query_total_pipe_lengths_dma(
            self.config.dma_codes, self.config.utility_names
        )
        df_summary = pd.DataFrame(
            total_pipe_lengths, columns=["utility", "dma", "total_pipe_lengths"]
        )
        coverage_data = (
            df.groupby(["utility", "dma"])
            .apply(self.calculate_total_pipe_lengths_covered)
            .reset_index()
        )
        coverage_data.columns = ["utility", "dma", "total_pipe_lengths_covered"]
        df_result = pd.merge(df_summary, coverage_data, on=["utility", "dma"])
        df_result["percentage_coverage"] = (
            df_result["total_pipe_lengths_covered"] / df_result["total_pipe_lengths"]
        ) * 100
        df_result.to_csv(summary_file)

    def update_edge_coverage_fraction(self, outputfile):
        df = pd.read_csv(outputfile, header=[0])
        for pipe in df.pipe_id.unique():
            dftmp = df.loc[df["pipe_id"] == pipe]
            dftmp = dftmp.drop_duplicates()
            pipe_len = dftmp["pipe_length"].iloc[0]
            if len(dftmp) > 1:
                pipe_cov = dftmp["coverage_length"].sum()
                total_cov = pipe_cov if pipe_cov < pipe_len else pipe_len
            else:
                total_cov = dftmp["coverage_length"].iloc[0]

            start_node_key = dftmp["start_node_key"].iloc[0]
            end_node_key = dftmp["end_node_key"].iloc[0]
            if pipe_len > 0:
                cov_fraction = (total_cov / pipe_len) * 100
            else:
                cov_fraction = 100
            query = f"""
            MATCH (n {{node_key: '{start_node_key}'}})-[r]-(m {{node_key: '{end_node_key}'}}) 
            SET r.coverageFraction = '{cov_fraction}';
            """
            db.cypher_query(query)

    def compute_cov(self):
        """
        Compute coverage.

        """
        loggers = self.query_graph_dma_logger_nodes(
            self.config.dma_codes, self.config.utility_names
        )

        self.initialise_csv()

        self.process_loggers(loggers)

        self.update_edge_coverage_fraction(self.config.outputfile)

        self.summary_statistics(self.config.outputfile)
