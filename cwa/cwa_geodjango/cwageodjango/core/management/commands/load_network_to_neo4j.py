import sys
sys.path.append('/opt/udt/')

from django.core.management.base import BaseCommand
from neomodel import db
from cwm.cleanwater.transform.gis_to_neo4j import GisToNeo4j
from cwageodjango.core.constants import (
    HYDRANT__NAME,
    NETWORK_OPT_VALVE__NAME,
    DEFAULT_SRID,
)
from sqids import Sqids
from cwageodjango.assets.models import PipeMain

class Command(BaseCommand):
    help = "Load the geospatial network from PostGIS into Neo4j."

    def clear_neo4j(self):
        self.stdout.write("Clearing Neo4j database...")
        db.cypher_query("MATCH (n) DETACH DELETE n")

    def handle(self, *args, **kwargs):
        self.clear_neo4j()
        
        self.stdout.write("Starting PostGIS to Neo4j transformation...")

        # Define the point assets to include in the graph
        point_asset_names = [
            HYDRANT__NAME,
            NETWORK_OPT_VALVE__NAME,
        ]
        
        sqids = Sqids()

        # Instantiate the transformation class
        self.stdout.write("Instantiating GisToNeo4j...")
        gis_to_neo4j = GisToNeo4j(
            srid=DEFAULT_SRID,
            sqids=sqids,
            point_asset_names=point_asset_names,
        )

        # Get all pipes from the database
        self.stdout.write("Fetching pipe data from PostGIS...")
        pipes = PipeMain.objects.all()

        # Calculate the graph components
        self.stdout.write("Calculating graph components...")
        gis_to_neo4j.calc_pipe_point_relative_positions(pipes)

        # Run the transformation and load into Neo4j
        self.stdout.write("Creating Neo4j graph...")
        gis_to_neo4j.create_neo4j_graph()

        self.stdout.write(self.style.SUCCESS("Successfully loaded network into Neo4j."))
