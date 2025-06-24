#!/bin/bash
DATA_PATH=/tmp/CW_20231108_060001.gdb

if [ -n "$1" ];then
  DATA_PATH=$1
fi

FORMAT=GPKG
if [ -n "$2" ];then
  DATA_PATH=$2
fi

#Export directly to PostgreSQL
if [[ ${FORMAT} == 'GPKG' ]];then
   export EXPORT_FORMAT='-f GPKG /tmp/data.gpkg'
fi
# Import master DMA into geopackage
directory=$(dirname "$DATA_PATH")
pushd "${directory}" || exit
if [ -f dma.csv ];then
  csv_import="ogr2ogr -progress --config PG_USE_COPY YES ${EXPORT_FORMAT}  -overwrite -lco GEOMETRY_NAME=geom -lco FID=gid -nln "dma" -s_srs EPSG:27700 -t_srs EPSG:27700 -skipfailures -gt 300000 dma.csv -oo AUTODETECT_TYPE=YES --config OGR_ORGANIZE_POLYGONS SKIP -forceNullable -makevalid --config OGR-SQLITE-CACHE 2000 --config OGR_SQLITE_SYNCHRONOUS OFF --config OGR_GPKG_NUM_THREADS ALL_CPUS"
  eval "$csv_import"
fi

# Define columns needed to be converted for each column. Shape is the name of the geom column
declare -A dictionary
array=(wChamber wDistributionMain wHydrant wLogger wNetworkMeter wNetworkOptValve wOperationalSite wPressureContValve wPressureFitting wTrunkMain wConnectionMain)

# Define columns needed to be converted for each column. Shape is the name of the geom column
dictionary["wChamber"]="GISID,SHORTGISID,shape"
dictionary["wDistributionMain"]="GISID,SUBTYPECD,LIFECYCLESTATUS,MEASUREDLENGTH,WATERTRACEWEIGHT,MAINOWNER,OPERATINGPRESSURE,NETWORKCODE,MATERIAL,PROTECTION,METRICCALCULATED,WATERTYPE,HYDARULICFAMILYTYPE,shape"
dictionary["wHydrant"]="GISID,SUBTYPECD,HYDRANTTYPE,HEIGHT,GLOBALID,SUPPLYPURPOSE,HYDRANTUSE,FMZCODE,shape"
dictionary["wLogger"]="GISID,LIFECYCLESTATUS,LOGGEROWNER,SUBTYPECD,LOGGERPURPOSE,LOGGERNUMBER,shape"
dictionary["wNetworkMeter"]="GISID,LIFECYCLESTATUS,SUBTYPECD,HEIGHT,SUPPLYPURPOSE,METERTYPE,METERCONTYPE,shape"
dictionary["wNetworkOptValve"]="LIFECYCLESTATUS,SUBTYPECD,NORMALPOSITION,VALVEOWNER,HEIGHT,SUPPLYPURPOSE,VALVEGROUP,VALVECONTMETHOD,VALVEFACE,ORIGINALVALVESTATUS,shape"
dictionary["wOperationalSite"]="GISID,LIFECYCLESTATUS,SUBTYPECD,OPTSITEOWNER,CORPASSETCODE,ASSETNAME,shape"
dictionary["wPressureContValve"]="GISID,LIFECYCLESTATUS,SUBTYPECD,VALVEOWNER,CONTROLREF,SUPPLYPURPOSE,NORMALPOSITION,VALVEFACE,VALVECONTMETHOD,SYMBOLCODE,shape"
dictionary["wPressureFitting"]="GISID,LIFECYCLESTATUS,SUBTYPECD,NETWORKCODE,shape"
dictionary["wTrunkMain"]="GISID,SUBTYPECD,LIFECYCLESTATUS,MEASUREDLENGTH,MAINOWNER,WATERTRACEWEIGHT,OPERATINGPRESSURE,PROTECTION,NETWORKCODE,WATERTYPE,MATERIAL,OPERATION,PRESSURETYPE,HYDARULICFAMILYTYPE,shape"
dictionary["wConnectionMain"]="GISID,SUBTYPECD,LIFECYCLESTATUS,MEASUREDLENGTH,WATERTRACEWEIGHT,MAINOWNER,MATERIAL,shape"
# Generate the ogr2ogr command based on key value pairs
for layer in "${!dictionary[@]}"; do
  table_name=${layer,,}
    # It seems line layers are stored as multi curve and others can be stored as multi
  if [[ $layer == 'wDistributionMain' || $layer == 'wTrunkMain' || $layer == 'wConnectionMain' ]];then
    GEOM_TYPE='LINESTRING'
  else
    GEOM_TYPE='POINT'
  fi
    # Split the string stored in dictionary[$layer] by comma
    IFS=',' read -ra values <<< "${dictionary[$layer]}"

    # Initialize a variable to store values for each iteration
    sql_statement=""

    # Concatenate values with double quotes and comma
    for (( j=0; j<${#values[@]}; j++ )); do
        sql_statement+="\"${values[$j]}\""
        if (( j < ${#values[@]} - 1 )); then
            sql_statement+=","
        fi
    done

    # SQL statement to select desired columns and also convert to wkt
    if [[ $layer == 'wDistributionMain' || $layer == 'wTrunkMain' || $layer == 'wConnectionMain' ]];then
      final_sql="SELECT $sql_statement,'$layer' as type,CAST(ST_AsText(ST_Transform("shape",4326)) AS TEXT) wkt_geom_4326 FROM $layer"
    else
      final_sql="SELECT $sql_statement,CAST(ST_AsText(ST_Transform("shape",4326)) AS TEXT) wkt_geom_4326 FROM $layer"
    fi


    # Final SQL command
    echo -e "\e[32m ---------------------------------------------------- \033[0m"
    echo -e "[Data Conversion] Converting FGDB layer : \e[1;31m ${layer} \033[0m"
    if [[ $layer == 'wDistributionMain' || $layer == 'wTrunkMain' ]];then
      command="ogr2ogr -progress --config PG_USE_COPY YES ${EXPORT_FORMAT}  ${DATA_PATH} ${layer} -overwrite -lco GEOMETRY_NAME=geom -lco FID=gid -addfields -nln pipes -s_srs EPSG:27700 -t_srs EPSG:27700 -skipfailures -gt 300000 -nlt ${GEOM_TYPE} -dialect sqlite -sql \"$final_sql\" --config OGR_ORGANIZE_POLYGONS SKIP -forceNullable -makevalid --config OGR-SQLITE-CACHE 2000 --config OGR_SQLITE_SYNCHRONOUS OFF --config OGR_GPKG_NUM_THREADS ALL_CPUS"
    else
      command="ogr2ogr -progress --config PG_USE_COPY YES ${EXPORT_FORMAT}  ${DATA_PATH} ${layer} -overwrite -lco GEOMETRY_NAME=geom -lco FID=gid -nln "${table_name}" -s_srs EPSG:27700 -t_srs EPSG:27700 -skipfailures -gt 300000 -nlt ${GEOM_TYPE} -dialect sqlite -sql \"$final_sql\" --config OGR_ORGANIZE_POLYGONS SKIP -forceNullable -makevalid --config OGR-SQLITE-CACHE 2000 --config OGR_SQLITE_SYNCHRONOUS OFF --config OGR_GPKG_NUM_THREADS ALL_CPUS"
    fi
    # evaluate the ogr2ogr command
    eval "$command"
    if [[ $layer == 'wDistributionMain' || $layer == 'wTrunkMain' || $layer == 'wConnectionMain' ]];then
      geom_update="update ${table_name} set wkt_geom_4326 = ST_AsText(ST_Transform(geom,4326))"
      update_geom_sql="ogrinfo -dialect sqlite -sql \"$geom_update\" /tmp/data.gpkg"
      eval $update_geom_sql
    fi
    if [[ $layer == 'wHydrant' || $layer == 'wNetworkOptValve' ]];then
      update_table="alter table ${table_name} ADD COLUMN acoustic_logger boolean DEFAULT FALSE"
      update_table_sql="ogrinfo -dialect sqlite -sql \"$update_table\" /tmp/data.gpkg"
      eval $update_table_sql
    fi
done

