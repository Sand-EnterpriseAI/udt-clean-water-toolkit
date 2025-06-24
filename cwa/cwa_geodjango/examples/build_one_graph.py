import setup

import networkx as nx
from osgeo import gdal, ogr

gdal.UseExceptions()


def edges_from_line(geom, attrs, simplify=True):
    if geom.GetGeometryType() == ogr.wkbLineString:
        if simplify:
            edge_attrs = attrs.copy()
            last = geom.GetPointCount() - 1
            yield (geom.GetPoint_2D(0), geom.GetPoint_2D(last), edge_attrs)
    elif geom.GetGeometryType() == ogr.wkbMultiLineString:
        for i in range(geom.GetGeometryCount()):
            geom_i = geom.GetGeometryRef(i)
            yield from edges_from_line(geom_i, attrs, simplify)


def read_shp(simplify=True, strict=True):
    # Bespoke replacement for nx.read_shp
    # TODO: Replace with path to your own data. A sample is included in the /data directory.
    path = "../../data/sample_data.gdb.zip"

    node_pair_duplicates = 0
    node_pairs = []
    net = nx.DiGraph()  # can presumably change this to undirected graph
    shp = ogr.Open(path)
    if shp is None:
        raise RuntimeError(f"Unable to open {path}")

    # relevant_layers = ["wLogger", "wTrunkMain", "wNetworkMeter"]
    relevant_layers = ["wTrunkMain"]

    for lyr in shp:
        if lyr.GetName() not in relevant_layers:  # modification
            continue  # modification
        print(lyr.GetName())

        fields = [x.GetName() for x in lyr.schema]
        for f in lyr:
            g = f.geometry()
            if g.GetGeometryType() not in [
                2,
                5,
            ]:  # only ogr.wkbLineString, ogr.wkbMultiLineString  # modification
                continue  # modification
            if g is None:
                if strict:
                    continue  # modification
                    # print("Bad data: feature missing geometry")
                    # raise nx.NetworkXError("Bad data: feature missing geometry")
                else:
                    continue
            flddata = [f.GetField(f.GetFieldIndex(x)) for x in fields]
            attributes = dict(zip(fields, flddata))
            attributes["ShpName"] = lyr.GetName()
            # Note:  Using layer level geometry type
            # No points found in shapefile
            if g.GetGeometryType() in (ogr.wkbLineString, ogr.wkbMultiLineString):
                for edge in edges_from_line(g, attributes, simplify):
                    e1, e2, attr = edge
                    net.add_edge(e1, e2)
                    net[e1][e2].update(attr)
            else:
                if strict:
                    raise nx.NetworkXError(
                        "GeometryType {} not supported".format(g.GetGeometryType())
                    )

    return net


def main():
    g = read_shp()
    g = g.to_undirected()
    import pdb

    pdb.set_trace()


main()
