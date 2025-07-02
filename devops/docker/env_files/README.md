Docker environment variables are placed in this directory.

1. Create env file for the database and neo4j and call it `.db_env`
    ```bash
    POSTGRES_PASSWORD=
    NEO4J_AUTH=
    ```
2. Create env file for the GeoServer and call it `.geoserver_env`
    ```bash
    GEOSERVER_ADMIN_PASSWORD=
    INITIAL_MEMORY=2G
    MAXIMUM_MEMORY=4G
    STABLE_EXTENSIONS=
    COMMUNITY_EXTENSIONS=
    ```

3. You will need to also add django env variables.