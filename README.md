# Unlocking Digital Twins (UDT) - Clean Water Toolkit

NB: This project is in active development and the toolkit is in alpha.

## Overview

This project is a Proof-of-Concept (PoC) for a clean water toolkit that combines aspects of a digital twin with clean water modelling and analysis. The project was funded by Ofwat in collaboration with Thames Water and Severn Trent Water.

The core innovation of this toolkit is a performant and efficient algorithm for transforming water distribution network data from a traditional geospatial format into a rich graph-based data structure. This unlocks new analytical capabilities that are not easily achievable with standard GIS models.

### Core Concepts

The toolkit was developed to address several key challenges in the water industry:
- **Limitations of Geospatial Models:** While essential for visualisation, traditional GIS models are not optimised for complex network analysis.
- **Power of Graph Technology:** Graph databases excel at pathfinding, centrality analysis, and predictive analytics, providing a more powerful way to model the intricate relationships within a water network.
- **Reducing Redundant Work:** By creating a generalisable, scalable, and flexible open-source toolkit, the project aims to provide a foundational "recipe" for creating digital twins, reducing the need for each utility to reinvent the wheel.

### Project Structure

The repository is organised into two main components:
- **`cwm` (Clean Water Module):** A core Python library containing the reusable logic for data transformation, network analysis, and modelling.
- **`cwa` (Clean Water Application):** A Django-based application that uses the `cwm` module and provides an API for interacting with the digital twin.

## 💻 Using the Toolkit

### Prerequisites

Before you begin, ensure you have met the following requirements:

- [Docker installation](https://www.docker.com/get-started/)

### Technology Stack
This project is built entirely on open-source technologies:
- **Backend:** Python, Django / GeoDjango
- **Database:** PostgreSQL with PostGIS (for geospatial data) and Neo4j (for graph data).
- **Core Libraries:** NetworkX, GeoPandas, Momepy, WNTR.
- **Containerization:** Docker and Docker Compose.

### Setup and Configuration

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/Explore-AI/udt-clean-water-toolkit.git
    cd udt-clean-water-toolkit
    ```

2.  **Configure Environment Variables**
    The toolkit uses an `.env` file to manage sensitive configuration like passwords and secret keys. A template is provided in the `.env.example` file.

    *   Copy the example file:
        ```bash
        cp .env.example .env
        ```
    *   Open the newly created `.env` file in a text editor and update the placeholder values:
        *   `NEO4J_AUTH`: This sets the authentication for the Neo4j database.
            *   Format: `neo4j/YourStrongPasswordHere`
            *   **Important:** Replace `YourStrongPasswordHere` with a strong, unique password. Neo4j version 5.x and later **do not allow** the default password `neo4j`.
        *   `DJANGO_SECRET_KEY__ENV_VAR`: This is a secret key for the Django application.
            *   Replace `your-django-secret-key` with a unique, unpredictable value.
            *   You can generate one using Python: `python3 -c "import secrets; print(secrets.token_hex(32))"`
        *   `CWA_NEO4J_HOST`: Should remain `udtneo4j` (the service name in Docker Compose).
        *   `CWA_NEO4J_USER`: Should remain `neo4j`.
        *   `CWA_NEO4J_PASSWORD`: This **must match** the password you set in `NEO4J_AUTH`. For example, if `NEO4J_AUTH=neo4j/YourStrongPasswordHere`, then `CWA_NEO4J_PASSWORD=YourStrongPasswordHere`.

### Running the Toolkit

Once configured, you can start all the services using Docker Compose:

```bash
docker-compose up -d
```

The first time you run this, Docker will download the necessary images and build the `cwageodjango` image, which may take a few minutes.
After the containers are started, an `orchestrator` service will run to install Python dependencies and apply database migrations. You can monitor its progress by checking its logs:
```bash
docker-compose logs -f orchestrator
```
Wait for the orchestrator to complete its tasks (you should see messages about migrations being applied or "No migrations to apply").

### Getting Started

There are two ways to get started with the toolkit:

1.  **Generate a Synthetic Network (Recommended):** Use the built-in command to generate a complete, fictional network. This is the quickest way to see the toolkit in action without needing any external data.
2.  **Use Your Own Data:** If you have your own geospatial data, you can ingest it into the toolkit.

#### Option 1: Generate a Synthetic Network

The toolkit includes a command to generate a sample network, including pipes, hydrants, valves, and synthetic flow data.

Run the following command from your host machine's terminal:
```bash
docker-compose exec udtcwageodjango python manage.py generate_synthetic_network
```
This will populate the PostGIS database with a ready-to-use sample network.

Once the data is in PostGIS, you can load it into Neo4j to visualize and query it as a graph. Run the following command:
```bash
docker-compose exec udtcwageodjango python3 manage.py load_network_to_neo4j
```

#### Option 2: Use Your Own Data

After setting up the environment, you can start using the toolkit with your own data.

##### 1. Add Your Data

- Create a `data/` directory at the root of the project if it doesn't exist.
- Place your geospatial data files (e.g., GeoPackage, Shapefile, etc.) into this `data/` directory. The toolkit is configured to access files from here.

##### 2. Ingest Your Data

The toolkit uses Django management commands to load data from your files into the PostGIS database. You need to run these commands from within the `cwageodjango` container.

Here is an example of how to ingest a layer of water mains data from a GeoPackage file:

```bash
# The -f flag points to the path inside the container
# The -x flag is the layer index (0 for the first layer)
docker-compose exec udtcwageodjango python manage.py layer_tw_mains_to_sql -f /opt/udt/data/your_data_file.gpkg -x 0
```

You can find other ingestion scripts in `cwa/cwa_geodjango/cwageodjango/core/scripts/`.

##### 3. Run the Examples

Once you have data in the database (either by generating a synthetic network or ingesting your own), you can run the example scripts and notebooks located in `cwa/cwa_geodjango/examples/`.

To see the graph network, open the **Neo4j Browser** and run a Cypher query. For example, to see a sample of your network, run:
```cypher
MATCH (n) RETURN n LIMIT 25
```

### Accessing Services

1.  **Neo4j Browser**
    *   URL: http://localhost:7474/browser/
    *   Connection:
        *   **Connect URL**: `bolt://localhost:7687` (usually pre-filled)
        *   **Authentication type**: Username / Password
        *   **Username**: The username part of your `NEO4J_AUTH` value in the `.env` file (e.g., `neo4j`).
        *   **Password**: The password part of your `NEO4J_AUTH` value in the `.env` file (e.g., `YourStrongPasswordHere`).

2.  **PostGIS Database**
    *   The PostGIS database is accessible on `localhost:5432`.
    *   Database Name: `postgis`
    *   Username: `postgis`
    *   Password: `postgis` (as set in `docker-compose.yml`)
    *   You can connect to this using tools like `psql` or a GUI like DBeaver or pgAdmin.

3.  **cwageodjango Application**
    *   (Further details on accessing any exposed API or web interface for the `cwageodjango` application will be added here as the project develops. Currently, its primary role is to support backend processes and data management, with its setup handled by the `orchestrator`.)

### Data Examples and Usage

The toolkit's functionality can be understood through various data interaction points within the repository:

*   **Example Scripts and Notebooks:**
    *   The `cwa/cwa_geodjango/examples/` directory contains scripts (`.py`) and a Jupyter Notebook (`.ipynb`) that demonstrate how to use the toolkit with various data sources (e.g., GeoDatabases, Django models, GeoPackages, CSVs, Neo4j).
*   **Data Ingestion and Processing:**
    *   Scripts in `cwa/cwa_geodjango/cwageodjango/core/scripts/` are Django management commands designed to import external data from user-provided files into the database.
*   **Data Generation:**
    *   The script `cwa/cwa_geodjango/cwageodjango/core/scripts/generate_flow_data.py` is a Django management command that demonstrates how synthetic flow data can be generated and stored within the system's database.

## Acknowledgements

This project was made possible through the collaboration and funding of the following organizations:
- **Ofwat**
- **Thames Water**
- **Severn Trent Water**
- **Sand Technologies**
