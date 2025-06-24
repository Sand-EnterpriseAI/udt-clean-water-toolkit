#!/bin/bash
DATA_PATH=/tmp/GIS_output/Water_assets_points
GEOPACKAGE_OUTPUT=/tmp/svn_data.gpkg

if [ -n "$1" ];then
	DATA_PATH=$1
fi
FORMAT='GPKG'
#Export directly to PostgreSQL
if [[ ${FORMAT} == 'GPKG' ]];then
   export EXPORT_FORMAT='-f GPKG /tmp/svn_data.gpkg'
fi
# Import master DMA into geopackage
current_dir=$(pwd)
assets_path=(Area_district  DMA_polygon  Water_accountabilty_zone  Water_assets_line  Water_assets_points)
for i in "${assets_path[@]}"; do
  FULL_DATA_PATH="${DATA_PATH}"/${i}
  pushd "${FULL_DATA_PATH}" || exit


  # Generate the ogr2ogr command based on key value pairs
  for layer in $(ls *.shp); do
      layer_prefix=${layer%.*}
      table_name=${layer_prefix,,}
      if [[ ${i} =~ points ]];then
        GEOM_TYPE=POINT
        final_sql="SELECT CAST("TAG" AS varchar) as tag,CAST("SUBTYPE" AS varchar) as sub_type,"geometry",CAST(ST_AsText(ST_Transform("geometry",4326)) AS TEXT) geometry_4326 FROM ${layer_prefix}"
        SQL_SELECT="-dialect sqlite -sql \"$final_sql\" "
      elif [[ ${i} =~ line ]];then
        GEOM_TYPE=LINESTRING
        final_sql="SELECT CAST("Tag" AS varchar) as tag,CAST("SubTypeCD_" AS varchar) as sub_type,"geometry",CAST(ST_AsText(ST_Transform("geometry",4326)) AS TEXT) geometry_4326 FROM ${layer_prefix}"
        SQL_SELECT="-dialect sqlite -sql \"$final_sql\" "
      else
        GEOM_TYPE=PROMOTE_TO_MULTI
        SQL_SELECT=""
      fi

      # Final SQL command
      echo -e "\e[32m ---------------------------------------------------- \033[0m"
      echo -e "[Data Conversion] Converting shp layer : \e[1;31m ${layer} \033[0m"

      command="ogr2ogr -progress --config PG_USE_COPY YES ${EXPORT_FORMAT}  ${layer} ${layer_prefix} -overwrite -lco GEOMETRY_NAME=geom -lco FID=id -nln ${table_name} -nlt ${GEOM_TYPE} --config OGR_ORGANIZE_POLYGONS SKIP -forceNullable -makevalid --config OGR-SQLITE-CACHE 2000 --config OGR_SQLITE_SYNCHRONOUS OFF --config OGR_GPKG_NUM_THREADS ALL_CPUS ${SQL_SELECT} "
      # evaluate the ogr2ogr command
      echo $command
      #eval "$command"
      update_sql="alter table ${table_name} add column acoustic_logger boolean DEFAULT FALSE"
      update_layer_command="ogrinfo -dialect sqlite -sql \"$update_sql\" /tmp/svn_data.gpkg"
      echo $update_layer_command
      #eval $update_layer_command
  done
done
pushd ${current_dir} || exit
