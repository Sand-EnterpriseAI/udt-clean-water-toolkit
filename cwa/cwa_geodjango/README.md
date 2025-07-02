# cwa_geodjango

NB: This document is a work in progress.

## 1. Requirements

### 1.1 Packages

- Django
- psycopg2-binary
- neo4j
- matplotlib
- python-dotenv
- cwm (from this package)

These packages can be installed with the instructions in Section 2.

### 1.2 Database

#### Postgis

Only follow these instructions if you intend to run this app independently and not integrate it into another application.

The following databases are supported by GeoDjango can be used with the app*:

- SpatiaLite
- MySQL
- MariaDB
- PostGIS (recommended for use with this application)

*Please check the functions used in the application have compatability with your selected database. 

`sudo apt-get install gdal-bin binutils libproj-dev gdal-bin libgdal-dev`

#### Neo4J

## 2. Development

### 2.1 Package installation

Create a python3 virtual environment and install required modules. For example using pip:

```
# from the cwa/cwa_geodjango app dir

python3 -m venv venv

source venv/bin/activate

pip install -r requirements.txt -r dev-requirements.txt
```

Before running the `cwa_geodjango` for development one needs to package and install the `cwm` module in dev mode:

```
# navigate to the cleanwater module directory
cd ../cwm/ # for example

pip install -e .

# The module can now be imported with

import cleanwater
```

### 2.2 Postgis DB setup 

Install a postgis database and expose the required port. Before running the `docker-compose` command to setup the postgis DB. you will need set the `POSTGRES_PASSWORD` env var in `devops/docker/env/.db_env`.

```
cd devops/scripts

./postgis_server_setup.sh # install the postgis docker image on the machine

./postgis_db_init.sh # initialise the udt database and user

```

### 2.3 Environment variables

A `.env` file should be placed in the `cwa_geodjango` app dir.

### 3 Using the app

`python3 run.py -f config.txt`

### 4 Config file parameters

A `.env` file should be placed in the `cwa_geodjango` app dir.


 Example configuration file

 TO DO: Change to yml and add yml parser with validation.

```
method = gis2neo4j

srid = 27700

batch_size = 5000

parallel = false
```


## Helpful resources

- The [GeoDjango documentation](https://docs.djangoproject.com/en/4.2/ref/contrib/gis/). The tutorial is helpful. The Model, Database, Queryset, and GDAL APIs are used widely in this project and are useful references.
