### For storing constants only
### Do not import app objects into this file to avoid circular imports

DEFAULT_SRID = 27700

PIPE_MAIN__NAME = "pipe_main"

HYDRANT__NAME = "hydrant"

LOGGER__NAME = "logger"

NETWORK_METER__NAME = "network_meter"

CONNECTION_METER__NAME = "connection_meter"

CONSUMPTION_METER__NAME = "consumption_meter"

NETWORK_OPT_VALVE__NAME = "network_opt_valve"

OPERATIONAL_SITE__NAME = "operational_site"

PRESSURE_CONTROL_VALVE__NAME = "pressure_control_valve"

PRESSURE_FITTING__NAME = "pressure_fitting"

PIPE_END__NAME = "pipe_end"

PIPE_JUNCTION__NAME = "pipe_junction"

POINT_ASSET__NAME = "point_asset"

ISOLATION_VALVE__NAME = "isolation_valve"

BULK_METER__NAME = "bulk_meter"

BOREHOLE__NAME = "boreholes"

NON_RETURN_VALVE__NAME = "nonreturnvalve"

PORTABLE_WATER_STORAGE__NAME = "potable_water_storage"

REGULATOR__NAME = "regulator"

REVENUE_METER__NAME = "revenue_meter"

WATER_FACILITY_CONNECTION__NAME = "waterfacilityconnection"

WATER_PIPE_CONNECTION__NAME = "waterpipeconnection"

WATER_PUMPING_FACILITY__NAME = "water_pumping_facility"

WATER_TREATMENT_WORK__NAME = "water_treatment_work"
PIPE_ASSETS__CHOICES = [
    (PIPE_MAIN__NAME, "Pipe Main"),
]

GEOS_LINESTRING_TYPES = [1, 5]

GEOS_POINT_TYPES = [0]

UTILITIES = [
    ("thames_water", "Thames Water"),
    ("severn_trent_water", "Severn Trent Water"),
]

ROUGHNESS_FACTORS = {
    "Steel": 140,
    "Ductile Iron": 130,
    "Unknown": 120,
    "Cast Iron": 120,
    "Medium Density Polyethylene": 140,
    "High Performance Polyethylene": 150,
    "Polyolefin": 150,
    "Glass Reinforced Plastic": 140,
    "Unplasticized Polyvinyl Chloride": 140,
    "Copper": 140,
    "Stainless Steel": 140,
    "Asbestos Cement": 140,
    "Concrete Steel": 120,
    "Other": 120,
    "Mild Steel Epoxy Coated": 140,
    "Low Density Polyethylene": 150,
    "Bituminous": 120,
    "Polyvinyl Chloride": 140,
    "Brick": 120,
    "Fiberglass": 140,
    "Galvanized Iron": 120,
    "Aluminium": 140,
    "Plastic": 140,
    "Glass": 140,
    "High Density Polyethylene": 150,
    "Polyethylene": 140,
    "Polyethylene Aluminium Composite": 140,
    "Polyurethane": 150,
    "Lead": 120,
    "PVC": 140,
    "Vinyl Chloride": 140,
    "Polypropylene": 140,
    "Galvanised": 120,
    "Steel High Pressure Polyethylene": 140,
    "Assumed smooth": 0,
    "Marble": 120,
}
