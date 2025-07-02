#!/bin/bash

echo "Started udt neo4j DB restore."
echo

OPTSTRING=":f:"

DB_CONTAINER_ID=`docker ps | grep udtneo4j | grep neo4j:5.20.0-community-bullseye | awk '{ print $1 }'`

while getopts ${OPTSTRING} opt; do
    case ${opt} in
        f)
            if [[ -z ${DB_CONTAINER_ID} ]];then
                echo "${DB_CONTAINER_ID} is not running, please run it using the docker-compose-neo4j.yml"
            else
            docker cp ${OPTARG} ${DB_CONTAINER_ID}:/backups/neo4j.dump
            docker stop ${DB_CONTAINER_ID}
            # Start the backup container
            # docker run -it --rm --env-file ../../docker/env_files/.db_env --volume=docker_neo4j-data:/data --volume=docker_neo4j-backup:/backups neo4j/neo4j-admin neo4j-admin database load neo4j --from-path=/backups/ --verbose --overwrite-destination=true
            docker run -it --rm --env-file ../../docker/env_files/.db_env --volume=docker_neo4j-data:/data --volume=docker_neo4j-backups:/var/lib/neo4j/backups/ neo4j:5.20.0-community-bullseye bin/neo4j-admin database load neo4j --from-path=/var/lib/neo4j/backups/ --verbose --overwrite-destination=true
            docker start ${DB_CONTAINER_ID}
            echo
            echo "udt neo4j DB restore complete."
            fi
    esac
done
