import geopandas as gpd
import fiona
import timeit

def report_generator(db_path):
    print("Auditing DB")
    f = open("db_audit.txt", "w")
    f.write(f'Report for DB {db_path} /n')
    layers = fiona.listlayers(db_path)
    # Anno - annotation layer (not useful for a DT), the 'w' prefix just denotes part of the water system
    layers_filtered = [l for l in layers if not l.endswith('Anno') and l.startswith('w')]
    for l in layers_filtered:
        start = timeit.timeit()
        print(f"Auditing layer {l}")
        layer_gdf = gpd.read_file(db_path, layer=l)
        print(f"read layer {l}")
        layer_info = {}
        geoms = set(layer_gdf.geom_type)
        proj = layer_gdf.crs.to_epsg()
        # ENABLED is field created for each feature in an esri geometric network
        is_geom_net = True if 'ENABLED' in layer_gdf.columns else False
        f.write(f"""
            Layer Name: {l}
            Geometry Types: {geoms}
            Projection: {proj}
            Part of Network: {is_geom_net} /n
              """)
        layer_info[l] = [geoms, proj, is_geom_net]
        col_info = {}
        f.write("Column_name  Null_Percentage  Column_Type /n")
        for col in layer_gdf.columns:
            try:
                col_info[col] = [layer_gdf[col].isnull().sum() * 100 / len(layer_gdf), layer_gdf[col].dtype]
                f.write(f"{col}  {str(round(col_info[col][0], 2))}  {col_info[col][1]} /n")
            except Exception as ex: 
                reason = f"couldnt process column {col}, reason {ex}"
        layer_info[l].append(col_info)  
        end = timeit.timeit()
        time_for_layer = end - start
        f.write(f"Audited layer {l}, took {time_for_layer}")
    f.close() 
    print("DB Audited")
    return layer_info

        
if __name__ == "__main__":
    report_generator("*/CW_20231108_060001.gdb")


