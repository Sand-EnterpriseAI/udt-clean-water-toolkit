from shapely import LineString, Point, line_locate_point, ops


def normalised_point_position_on_line(line_string_coords, end_point_coords):
    """Get the normalised position of a Point geometry on a LineString geometry relative to the
    LineString start Point.

    https://zach.se/geodesic-distance-between-points-in-geodjango/
    https://docs.djangoproject.com/en/5.0/ref/contrib/gis/geos/

    Params:
           line_string_coords (LineString coordinates, required)
           end_point_coords (point corodinates, required)

    Returns:
           distance_from_line_start (float)
           normalised_position_on_line (float)
    """

    line_geom: LineString = LineString(line_string_coords)

    end_point_geom: Point = Point(end_point_coords)

    distance_from_line_start = line_locate_point(line_geom, end_point_geom)

    line_part = ops.substring(
        line_geom, start_dist=0, end_dist=distance_from_line_start
    )

    normalised_position_on_line = 1 - (
        (line_geom.length - distance_from_line_start) / line_geom.length
    )

    return line_part.length, normalised_position_on_line
