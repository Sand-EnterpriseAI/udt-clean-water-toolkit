from cleanwater.transform.network_transform import NetworkTransform


class Neo4jToNkController:
    def __init__(self, config):
        self.config = config

    def create_network(self):

        filters = {
            "utility_names": self.config.utility_names,
            "dma_codes": self.config.dma_codes,
        }

        nt = NetworkTransform()

        nt.initialise(
            "neo4j2nk",
            filters=filters,
        )

        nt.run(
            srid=27700,
            batch_size=self.config.batch_size,
            outputfile=self.config.outputfile,
        )
