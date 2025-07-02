from cleanwater.transform.network_transform import NetworkTransform
from cwageodjango.config.settings import sqids
from ..constants import POINT_ASSET_MODELS, PIPE_MAIN_MODEL


class GisToNxController:
    """Create a Neo4J graph of assets from a geospatial
    network of assets"""

    def __init__(self, config):
        self.config = config

    def create_network(self):
        filters = {
            "utility_names": self.config.utility_names,
            "dma_codes": self.config.dma_codes,
        }

        nt = NetworkTransform()

        nt.initialise(
            "gis2nx",
            pipe_asset=PIPE_MAIN_MODEL,
            point_assets=POINT_ASSET_MODELS,
            filters=filters,
        )

        nt.run(
            srid=27700,
            sqids=sqids,
            gis_framework="geodjango",
            batch_size=self.config.batch_size,
            query_limit=self.config.query_limit,
            query_offset=self.config.query_offset,
        )
