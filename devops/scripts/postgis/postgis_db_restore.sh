#!/bin/bash

echo "Started udt postgis DB restore."
echo

OPTSTRING=":f:"

DB_CONTAINER_ID=`docker ps | grep udtpostgis | grep postgis/postgis | awk '{ print $1 }'`


while getopts ${OPTSTRING} opt; do
  case ${opt} in
    f)
        docker cp ${OPTARG} ${DB_CONTAINER_ID}:/udt_db_dump.sql
        docker exec -it ${DB_CONTAINER_ID} bash -c "pg_restore -j 4 -U udt -d udt udt_db_dump.sql"
      ;;
  esac
done


echo
echo "udt DB restore complete."
