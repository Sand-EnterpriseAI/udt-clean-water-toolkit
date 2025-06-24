from django.contrib.gis.db.models.functions import GeoFunc


class LineStartPoint(GeoFunc):
    function = "ST_StartPoint"


class LineEndPoint(GeoFunc):
    function = "ST_EndPoint"
