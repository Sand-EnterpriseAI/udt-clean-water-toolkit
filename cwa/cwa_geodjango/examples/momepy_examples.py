import setup  # Required. Do not remove.
from django.core.serializers import serialize
from cwageodjango.assets.models import Logger
from cwageodjango.core.constants import DEFAULT_SRID
from cwageodjango.network import GisToGraphNetwork
from cwageodjango.assets.controllers import TrunkMainsController


# https://docs.djangoproject.com/en/5.0/ref/contrib/gis/db-api/#spatial-lookups
# https://docs.djangoproject.com/en/5.0/ref/contrib/gis/geoquerysets/#std-fieldlookup-dwithin


# NOTE: The crux of the below two examples is that one can contruct a graph from
# lines or points using geojson. Need to figure out how to create graph that has combined assets


# https://stackoverflow.com/a/65324191
# https://postgis.net/docs/ST_ClosestPoint.html
# https://docs.djangoproject.com/en/5.0/ref/contrib/gis/functions/#django.contrib.gis.db.models.functions.ClosestPoint


# https://networkx.org/documentation/stable/auto_examples/geospatial/plot_lines.html
def graph_from_trunk_mains_demo():
    import matplotlib.pyplot as plt
    import momepy
    import networkx as nx

    tm_controller = TrunkMainsController()
    trunk_mains_gdf = tm_controller.trunk_mains_to_geodataframe()

    trunk_mains_as_single_lines_gdf = trunk_mains_gdf.explode(index_parts=True)
    G = momepy.gdf_to_nx(trunk_mains_as_single_lines_gdf, approach="primal")

    positions = {n: [n[0], n[1]] for n in list(G.nodes)}

    f, ax = plt.subplots(1, 2, figsize=(12, 6), sharex=True, sharey=True)
    trunk_mains_gdf.plot(color="k", ax=ax[0])
    for i, facet in enumerate(ax):
        facet.set_title(("TrunkMains Geospatial", "TrunkMains Graph")[i])
        facet.axis("off")

    nx.draw(G, positions, ax=ax[1], node_size=5)

    plt.show()


# https://docs.momepy.org/en/stable/user_guide/graph/convert.html # alternate
# Lots of island loggers as expected
def graph_from_loggers_demo():
    import matplotlib.pyplot as plt
    from libpysal import weights
    import geopandas as gpd
    import networkx as nx
    from contextily import add_basemap
    import numpy as np

    logger_data = serialize(
        "geojson", Logger.objects.all(), geometry_field="geometry", srid=DEFAULT_SRID
    )

    logger_gdf = gpd.read_file(logger_data)

    coordinates = np.column_stack((logger_gdf.geometry.x, logger_gdf.geometry.y))

    knn3 = weights.KNN.from_dataframe(logger_gdf, k=3)

    dist = weights.DistanceBand.from_array(coordinates, threshold=50)

    knn_graph = knn3.to_networkx()
    dist_graph = dist.to_networkx()

    positions = dict(zip(knn_graph.nodes, coordinates))

    f, ax = plt.subplots(1, 2, figsize=(8, 4))
    for i, facet in enumerate(ax):
        logger_gdf.plot(marker=".", color="orangered", ax=facet)
        add_basemap(facet)
        facet.set_title(("KNN-3", "50-meter Distance Band")[i])
        facet.axis("off")
    nx.draw(knn_graph, positions, ax=ax[0], node_size=5, node_color="b")
    nx.draw(dist_graph, positions, ax=ax[1], node_size=5, node_color="b")
    plt.show()


def main():
    graph_from_trunk_mains()
    # graph_from_trunk_mains_demo()
    # graph_from_loggers_demo()


main()
