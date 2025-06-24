# from geopandas import GeoDataFrame
# from momepy import gdf_to_nx
import wntr
import networkit as nk

# from networkx import Graph
from . import GeoDjangoDataManager


# TO DO: fixing inheritence in data managers
class NetworkDataManager(GeoDjangoDataManager):

    # def gdf_lines_to_nx_graph(self, geodataframe: GeoDataFrame, method: str = "momepy") -> Graph | None:
    #     """Convert a geopandas dataframe with lines or multilines
    #     only to a networkx graph"""
    #     if method == "momepy":
    #         return self.momepy_gdf_lines_to_graph(geodataframe)
    #     elif method == "abinitio":
    #         pass

    # def momepy_gdf_lines_to_graph(self, geodataframe: GeoDataFrame) -> Graph:
    #     """Convert a geopandas dataframe with lines or multilines
    #     only to a networkx graph using the momepy gdf_to_nx method"""
    #     gdf: GeoDataFrame = geodataframe.explode(index_parts=True)
    #     return gdf_to_nx(gdf, approach="primal")

    @staticmethod
    def nk_to_graphml(graph, out_file):
        nk.writeGraph(graph, out_file, nk.Format.GML)

    @staticmethod
    def wntr_to_inp(graph, out_file):
        """
        Exports the WNTR model to an INP (EPANET input file) format.

        """
        wntr.network.write_inpfile(graph, filename=out_file)

    @staticmethod
    def wntr_to_json(graph, out_file):
        """
        Exports the WNTR model to a JSON format.

        Parameters:
            filename (str): Name of the JSON file to export.

        """
        wntr.network.write_json(graph, path_or_buf=out_file)
