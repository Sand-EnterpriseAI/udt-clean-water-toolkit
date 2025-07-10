#!/bin/sh

CWA_GEODORM_CONTAINER_ID=`docker ps | grep udtcwageodjango | grep cwa_geodjango | awk '{ print $1 }'`

echo "the container ID == ${CWA_GEODORM_CONTAINER_ID}"

docker exec ${CWA_GEODORM_CONTAINER_ID} pip install -r requirements.txt -r dev-requirements.txt

docker exec ${CWA_GEODORM_CONTAINER_ID} bash -c "cd ../../cwm && pip install -e ."

docker exec ${CWA_GEODORM_CONTAINER_ID} python3 manage.py migrate
