#!/bin/bash

echo "Started udt postgis DB reset."
echo "Ensure all connections to the udt postgis DB are closed."
echo "The following actions will take place:"
echo "The udt postgis database will be dropped."
echo "A udt postgis database will be created."
echo

source ../../docker/env_files/.db_env

DB_CONTAINER_ID=`docker ps | grep udtpostgis | grep postgis/postgis | awk '{ print $1 }'`

#docker exec -it ${DB_CONTAINER_ID} psql --user udt -c "select pg_terminate_backend(pid) from pg_stat_activity where datname='udt_api2';"

docker exec -it ${DB_CONTAINER_ID} psql --user postgres -c "drop database udt"
docker exec -it ${DB_CONTAINER_ID} psql --user postgres -c "create database udt"
#docker exec -it ${DB_CONTAINER_ID} psql --user postgres -c "create user udt with superuser password '${POSTGRES_PASSWORD}'"

echo
echo "udt DB reset complete."
