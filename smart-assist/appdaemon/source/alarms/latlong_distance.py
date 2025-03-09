import geopy.distance, math
# Calculates distance between two points
def latlong_distance(latitude,longitude,latitude0,longitude0,threshold):
    distance = geopy.distance.geodesic((latitude,longitude),(latitude0,longitude0)).m
    if distance > threshold:
        return True, distance
    else:
        return False, distance