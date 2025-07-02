from django.core.management.base import BaseCommand
from neomodel import db

class Command(BaseCommand):
    help = "Verify that data has been loaded into the Neo4j database."

    def handle(self, *args, **kwargs):
        self.stdout.write("Verifying Neo4j data...")

        try:
            # Query to count nodes
            node_results, _ = db.cypher_query("MATCH (n) RETURN count(n) AS node_count")
            node_count = node_results[0][0] if node_results else 0

            # Query to count relationships
            rel_results, _ = db.cypher_query("MATCH ()-[r]->() RETURN count(r) AS rel_count")
            rel_count = rel_results[0][0] if rel_results else 0

            if node_count > 0 and rel_count > 0:
                self.stdout.write(self.style.SUCCESS(f"Verification successful!"))
                self.stdout.write(f" - Found {node_count} nodes.")
                self.stdout.write(f" - Found {rel_count} relationships.")
            else:
                self.stdout.write(self.style.WARNING("Verification failed: No data found in Neo4j database."))
                self.stdout.write(f" - Node count: {node_count}")
                self.stdout.write(f" - Relationship count: {rel_count}")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An error occurred during verification: {e}"))
