
DMA_LAYER_INDEX=0
FLOW_CONTROL_LAYER_INDEX=1
HYDRANT_LAYER_INDEX=2
METER_LAYER_INDEX=3
OPERTAIONAL_SITE_LAYER_INDEX=4
WATER_PUMP_LAYER_INDEX=5
WATER_TANK_LAYER_INDEX=6
WATER_WORK_LAYER_INDEX=7
PIPES_LAYER_INDEX=8

OPTSTRING=":f:"

while getopts ${OPTSTRING} opt; do
    case ${opt} in
        f)
            python3 manage.py layer_stw_dmas_to_sql -f ${OPTARG} -x ${DMA_LAYER_INDEX}
            python3 manage.py layer_stw_mains_to_sql -f ${OPTARG} -x ${PIPES_LAYER_INDEX}
            python3 manage.py layer_stw_hydrants_to_sql -f ${OPTARG} -x ${HYDRANT_LAYER_INDEX}
            python3 manage.py layer_stw_flow_controls_to_sql -f ${OPTARG} -x ${FLOW_CONTROL_LAYER_INDEX}
            python3 manage.py layer_stw_meters_to_sql -f ${OPTARG} -x ${METER_LAYER_INDEX}
            python3 manage.py layer_stw_water_pumps_to_sql -f ${OPTARG} -x ${WATER_PUMP_LAYER_INDEX}
            python3 manage.py layer_stw_water_tanks_to_sql -f ${OPTARG} -x ${WATER_TANK_LAYER_INDEX}
            python3 manage.py layer_stw_water_works_to_sql -f ${OPTARG} -x ${WATER_WORK_LAYER_INDEX}
    esac
done
