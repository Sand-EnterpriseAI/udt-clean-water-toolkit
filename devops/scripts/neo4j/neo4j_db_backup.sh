#!/bin/bash

echo "Started udt Neo4j DB backup. We will need to stop the udt neo4j container. Ensure that all connecting services have been stopped."
echo "Ensure you have a data/db_backups/ folder in the root directory of this project. If not we will make one."

BASE_DIR=../../..
DB_BACKUPS_DIR=${BASE_DIR}/data/db_backups

if [ ! -d ${DB_BACKUPS_DIR} ]; then
    mkdir -p ${DB_BACKUPS_DIR}
fi

DB_CONTAINER_ID=`docker ps | grep udtneo4j | grep neo4j:5.20.0-community-bullseye | awk '{ print $1 }'`

CURRENT_DATETIME=`date "+%d-%m-%Y_%H-%M-%S"`
BACKUP_FILE_NAME=${DB_BACKUPS_DIR}/udt_neo4j_db_backup_${CURRENT_DATETIME}.dump

if [[ -z ${DB_CONTAINER_ID} ]];then
  echo "${DB_CONTAINER_ID} is not running, please run it using the docker-compose-neo4j.yml"
else
  docker stop ${DB_CONTAINER_ID}
  #docker run -it  --rm --env-file ../../docker/env_files/.db_env --volume=docker_neo4j-data:/data --volume=docker_neo4j:/backups neo4j/neo4j-admin neo4j-admin database dump neo4j --verbose --to-path=/backups
  docker run -it --rm --env-file ../../docker/env_files/.db_env --volume=docker_neo4j-data:/data --volume=docker_neo4j-backups:/var/lib/neo4j/backups/ neo4j:5.20.0-community-bullseye bin/neo4j-admin database dump neo4j --verbose --to-path=./backups/ --overwrite-destination=true
  docker start ${DB_CONTAINER_ID}
  docker cp ${DB_CONTAINER_ID}:/backups/neo4j.dump ${BACKUP_FILE_NAME}
fi
