#!/bin/bash

echo "Started udt postgis server setup."
echo

docker-compose -f ../../docker/docker-compose-postgis.yml up -d

echo
echo "Postgis server setup complete."
