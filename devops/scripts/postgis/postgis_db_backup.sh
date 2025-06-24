#!/bin/bash

echo "Started udt postgis DB backup. Ensure you have a data/db_backups/ folder in the root directory of this project. If not we will make one."
echo

BASE_DIR=../../..
DB_BACKUPS_DIR=${BASE_DIR}/data/db_backups

if [ ! -d ${DB_BACKUPS_DIR} ]; then
    mkdir -p ${DB_BACKUPS_DIR}
fi

DB_CONTAINER_ID=`docker ps | grep udtpostgis | grep postgis/postgis | awk '{ print $1 }'`

CURRENT_DATETIME=`date "+%d-%m-%Y_%H-%M-%S"`
BACKUP_FILE_NAME=${DB_BACKUPS_DIR}/udt_postgis_db_backup_${CURRENT_DATETIME}.sql

#https://stackoverflow.com/questions/24718706/backup-restore-a-dockerized-postgresql-database
#docker exec -it ${DB_CONTAINER_ID} pg_dump -U udt -Fc udt ${BACKUP_FILE_NAME}


#https://stackoverflow.com/a/63934857
docker exec -it ${DB_CONTAINER_ID} bash -c 'pg_dump -Fc -U udt > /udt_db_dump.sql'
docker cp ${DB_CONTAINER_ID}:/udt_db_dump.sql ${BACKUP_FILE_NAME}
