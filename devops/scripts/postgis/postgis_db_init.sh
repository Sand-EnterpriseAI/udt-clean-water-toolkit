#!/bin/bash

echo "Started udt postgis DB initialisation."
echo "The following actions will take place:"
echo "A udt postgis database will be created."
echo "A udt superuser will be created."
echo

DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
source "$DIR/../../docker/env_files/.db_env"

DB_CONTAINER_ID=`docker ps | grep udtpostgis | grep postgis/postgis | awk '{ print $1 }'`

docker exec -it ${DB_CONTAINER_ID} psql --user postgres -c "create database udt"
docker exec -it ${DB_CONTAINER_ID} psql --user postgres -c "create user udt with superuser password '${POSTGRES_PASSWORD}'"

echo
echo "DB intilisation complete."
