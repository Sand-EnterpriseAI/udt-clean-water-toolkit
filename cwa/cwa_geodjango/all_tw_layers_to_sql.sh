
# dictionary["wChamber"]="GISID,SHORTGISID,shape"
# dictionary["wDistributionMain"]="GISID,SUBTYPECD,LIFECYCLESTATUS,MEASUREDLENGTH,WATERTRACEWEIGHT,MAINOWNER,OPERATINGPRESSURE,NETWORKCODE,MATERIAL,PROTECTION,METRICCALCULATED,WATERTYPE,HYDARULICFAMILYTYPE,shape"
# dictionary["wHydrant"]="GISID,SUBTYPECD,HYDRANTTYPE,HEIGHT,GLOBALID,SUPPLYPURPOSE,HYDRANTUSE,FMZCODE,shape"
# dictionary["wLogger"]="GISID,LIFECYCLESTATUS,LOGGEROWNER,SUBTYPECD,LOGGERPURPOSE,LOGGERNUMBER,shape"
# dictionary["wNetworkMeter"]="GISID,LIFECYCLESTATUS,SUBTYPECD,HEIGHT,SUPPLYPURPOSE,METERTYPE,METERCONTYPE,shape"
# dictionary["wNetworkOptValve"]="LIFECYCLESTATUS,SUBTYPECD,NORMALPOSITION,VALVEOWNER,HEIGHT,SUPPLYPURPOSE,VALVEGROUP,VALVECONTMETHOD,VALVEFACE,ORIGINALVALVESTATUS,shape"
# dictionary["wOperationalSite"]="GISID,LIFECYCLESTATUS,SUBTYPECD,OPTSITEOWNER,CORPASSETCODE,ASSETNAME,shape"
# dictionary["wPressureContValve"]="GISID,LIFECYCLESTATUS,SUBTYPECD,VALVEOWNER,CONTROLREF,SUPPLYPURPOSE,NORMALPOSITION,VALVEFACE,VALVECONTMETHOD,SYMBOLCODE,shape"
# dictionary["wPressureFitting"]="GISID,LIFECYCLESTATUS,SUBTYPECD,NETWORKCODE,shape"
# dictionary["wTrunkMain"]="GISID,SUBTYPECD,LIFECYCLESTATUS,MEASUREDLENGTH,MAINOWNER,WATERTRACEWEIGHT,OPERATINGPRESSURE,PROTECTION,NETWORKCODE,WATERTYPE,MATERIAL,OPERATION,PRESSURETYPE,HYDARULICFAMILYTYPE,shape"
# dictionary["wConnectionMain"]="GISID,SUBTYPECD,LIFECYCLESTATUS,MEASUREDLENGTH,WATERTRACEWEIGHT,MAINOWNER,MATERIAL,shape"



# admin_boundary -> dma 
# DMA_LAYER_INDEX=0
DMA_LAYER_INDEX=admin_boundary

# asset_line_1
# PIPES_LAYER_INDEX=11
PIPES_LAYER_INDEX=asset_lines_1

# asset_pnts_1
# WCHAMBER_LAYER_INDEX=0
WCHAMBER_LAYER_INDEX=asset_pnts_1

# asset_pnts_2
WCONNECTIONMETER_LAYER_INDEX=1
WCONNECTIONMETER_LAYER_INDEX=asset_pnts_2

# asset_pnts_3
WCONSUMPTIONMETER_LAYER_INDEX=2
WCONSUMPTIONMETER_LAYER_INDEX=asset_pnts_3

# asset_pnts_4
WHYDRANT_LAYER_INDEX=5
WHYDRANT_LAYER_INDEX=asset_pnts_4

# asset_pnts_5
WLOGGER_LAYER_INDEX=4
WLOGGER_LAYER_INDEX=asset_pnts_5


# asset_pnts_6
WNETWORKMETER_LAYER_INDEX=5
WNETWORKMETER_LAYER_INDEX=asset_pnts_6


# asset_pnts_7
WNETWORKOPTVALVE_LAYER_INDEX=6
WNETWORKOPTVALVE_LAYER_INDEX=asset_pnts_6


# asset_pnts_8
WOPERATIONALSITE_LAYER_INDEX=7
WOPERATIONALSITE_LAYER_INDEX=asset_pnts_8


# asset_pnts_9
WPRESSURECONTVALVE_LAYER_INDEX=8
WPRESSURECONTVALVE_LAYER_INDEX=asset_pnts_9


# asset_pnts_10
WPRESSUREFITTING_LAYER_INDEX=9
WPRESSUREFITTING_LAYER_INDEX=asset_pnts_10




OPTSTRING=":f:"

while getopts ${OPTSTRING} opt; do
    case ${opt} in
        f)
            python3 manage.py layer_tw_dmas_to_sql -f ${OPTARG} -x ${DMA_LAYER_INDEX}
            python3 manage.py layer_tw_network_meters_to_sql -f ${OPTARG} -x ${WNETWORKMETER_LAYER_INDEX}
            python3 manage.py layer_tw_pressure_control_valve_to_sql -f ${OPTARG} -x ${WPRESSURECONTVALVE_LAYER_INDEX}
            python3 manage.py layer_tw_hydrants_to_sql -f ${OPTARG} -x ${WHYDRANT_LAYER_INDEX}
            python3 manage.py layer_tw_mains_to_sql -f ${OPTARG} -x ${PIPES_LAYER_INDEX}
            python3 manage.py layer_tw_loggers_to_sql -f ${OPTARG} -x ${WLOGGER_LAYER_INDEX}
            python3 manage.py layer_tw_pressure_fittings_to_sql -f ${OPTARG} -x ${WPRESSUREFITTING_LAYER_INDEX}
            python3 manage.py layer_tw_operational_site_to_sql -f ${OPTARG} -x ${WOPERATIONALSITE_LAYER_INDEX}
            python3 manage.py layer_tw_chambers_to_sql -f ${OPTARG} -x ${WCHAMBER_LAYER_INDEX}
            python3 manage.py layer_tw_network_opt_valve_to_sql -f ${OPTARG} -x ${WNETWORKOPTVALVE_LAYER_INDEX}
            python3 manage.py layer_tw_connection_meters_to_sql -f ${OPTARG} -x ${WCONNECTIONMETER_LAYER_INDEX}
            python3 manage.py layer_tw_consumption_meters_to_sql -f ${OPTARG} -x ${WCONSUMPTIONMETER_LAYER_INDEX}
    esac
done


