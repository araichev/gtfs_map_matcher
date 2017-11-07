import polyline
import requests
import googlemaps


# Mapzen map matching functions ----------
def encode_points_mapzen(points):
    """
    Given a list of longitude-latitude points, return their dictionary
    representation suitable for Mapzen's Map Matching API;
    see https://mapzen.com/documentation/mobility/map-matching/api-reference/#example-trace_attributes-requests
    """
    return [{'lon': round(p[0], 6), 'lat': round(p[1], 6)} for p in points]

def decode_points_mapzen(points):
    """
    Inverse of function :func:`encode_points_mapzen`.
    """
    return [[d['lon'], d['lat']] for d in points]

def parse_response_mapzen(response):
    pline = polyline.decode(response['trip']['legs'][0]['shape'], 6)
    return [(p[1], p[0]) for p in pline]

def match_with_mapzen(points, api_key,
  url='https://valhalla.mapzen.com/trace_route', kwargs=None):
    """
    Public server accepts at most 100 points.
    """
    data = {
        'shape': encode_points_mapzen(points),
        'costing': 'auto',
    }
    if kwargs is not None:
        data.update(kwargs)

    r = requests.post(url, params={'api_key': api_key}, json=data)
    r.raise_for_status()
    return parse_response_mapzen(r.json())

# OSRM matching functions ----------
def encode_points_osrm(points):
    """
    Given a list of longitude-latitude points, return their dictionary
    representation suitable for Mapbox's Map Matching API;
    see https://www.mapbox.com/api-documentation/#map-matching
    """
    return (';').join(['{!s},{!s}'.format(p[0], p[1]) for p in points])

def decode_points_osrm(points):
    """
    Inverse of function :func:`encode_points_mapzen`.
    """
    return [[float(x) for x in p.split(',')] for p in points.split(';')]

def parse_response_osrm(response):
    pline = []
    for m in response['matchings']:
        pline.extend(polyline.decode(m['geometry'], 6))
    return [(p[1], p[0]) for p in pline]

def match_with_osrm(points, profile='car',
  url='http://router.project-osrm.org/match/v1'):
    """
    Public server accepts at most 100 points.
    """
    url = '{!s}/{!s}/{!s}'.format(url, profile,
      encode_points_mapbox(points))
    params = {
        'geometries': 'polyline6',
    }
    r = requests.get(url, params=params)
    r.raise_for_status()
    return parse_response_osrm(r.json())


# Mapbox (which uses OSRM) map matching functions ----------
def encode_points_mapbox(points):
    """
    Given a list of longitude-latitude points, return their dictionary
    representation suitable for Mapbox's Map Matching API;
    see https://www.mapbox.com/api-documentation/#map-matching
    """
    return (';').join(['{!s},{!s}'.format(p[0], p[1]) for p in points])

def decode_points_mapbox(points):
    """
    Inverse of function :func:`encode_points_mapzen`.
    """
    return [[float(x) for x in p.split(',')] for p in points.split(';')]

def parse_response_mapbox(response):
    pline = []
    for m in response['matchings']:
        pline.extend(polyline.decode(m['geometry'], 6))
    return [(p[1], p[0]) for p in pline]

def match_with_mapbox(points, api_key, profile='driving'):
    """
    Accepts at most 100 points.
    """
    url='https://api.mapbox.com/matching/v5/mapbox'
    url = '{!s}/{!s}/{!s}'.format(url, profile,
      encode_points_mapbox(points))
    params = {
        'access_token': api_key,
        'geometries': 'polyline6',
    }
    r = requests.get(url, params=params)
    r.raise_for_status()
    return parse_response_mapbox(r.json())

# Google map matching functions -------------
def encode_points_google(points):
    """
    Given a list of longitude-latitude points, return their string
    representation suitable for Google's Snap to Roads API;
    see https://developers.google.com/maps/documentation/roads/snap.
    """
    return ('|').join(['{:.06f},{:.06f}'.format(p[1], p[0]) for p in points])

def decode_points_google(points):
    """
    Inverse of function :func:`encode_points_google`.
    """
    return [[float(x) for x in p.split(',')[::-1]] for p in points.split('|')]

def parse_response_google(response):
    return [[p['location']['longitude'], p['location']['latitude']]
        for p in response['snappedPoints']]

def match_with_google(points, api_key):
    """
    Accepts at most 100 points.
    """
    url = 'https://roads.googleapis.com/v1/snapToRoads'
    params = {
        'key': api_key,
        'path': encode_points_google(points),
        'interpolate': True,
    }
    r = requests.get(url, params=params)
    r.raise_for_status()
    return parse_response_google(r.json())