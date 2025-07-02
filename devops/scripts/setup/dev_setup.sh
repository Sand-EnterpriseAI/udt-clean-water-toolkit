#!/bin/bash

echo "Setting up the udt toolkit for development."
echo "The following actions will take place:"
echo "udt postgis server will be setup."
echo "A udt postgis database will be created."
echo "A udt superuser will be created on the postgis database."
echo "udt neo4j server will be setup with credentials specified by the docker compose env variables."
echo "pip packages will be installed for the cwa_geodjango app."
echo "pip packages will be installed for the cwm in dev mode."
echo


docker compose -f ../../docker/docker-compose-postgis.yml -f ../../docker/docker-compose-neo4j.yml -f ../../docker/docker-compose-cwa-geodjango.yml -f ../../docker/docker-compose-cwa-geoalchemy.yml -f ../../docker/docker-compose-api-drf-dev.yml up -d --build

CWA_GEODORM_CONTAINER_ID=`docker ps | grep udtcwageodjango | grep cwa_geodjango | awk '{ print $1 }'`
CWA_GEOALCHEMY_CONTAINER_ID=`docker ps | grep udtcwageoalchemy | grep cwa_geoalchemy | awk '{ print $1 }'`
API_DRF_CONTAINER_ID=`docker ps | grep udtapidrf | grep api_drf_dev | awk '{ print $1 }'`


docker exec -it ${CWA_GEODORM_CONTAINER_ID} pip install -r requirements.txt -r dev-requirements.txt

docker exec -it ${CWA_GEOALCHEMY_CONTAINER_ID} pip install -r requirements.txt

docker exec -it ${CWA_GEODORM_CONTAINER_ID} pip install -e ../../cwm/

docker exec -it ${CWA_GEODORM_CONTAINER_ID} bash -c "cd /opt/udt/api/api_drf/ && pip install -r requirements.txt -r dev-requirements.txt"

docker exec -it ${CWA_GEODORM_CONTAINER_ID} bash ln -s /opt/cwa/cwa_geodjango/cwa_geod/ /opt/api/api_drf/

docker exec -it ${API_DRF_CONTAINER_ID} pip3 install -r requirements.txt -r dev-requirements.txt

../postgis/postgis_db_init.sh

echo
echo "cwa_geodjango app dev setup complete."
echo "cwa_geoalchemy app dev setup complete."
echo "api_drf app dev setup complete."
echo "GeoServer app setup complete."
