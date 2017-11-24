"""
API functions for several popular map matching services.
"""
from functools import partial

import polyline
import requests
from requests_futures.sessions import FuturesSession


MAX_WORKERS = 50  # Max number of concurrent threads for async HTTP requests

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
    try:
        r = response.json()
        pline = polyline.decode(r['trip']['legs'][0]['shape'], 6)
        points = [(p[1], p[0]) for p in pline]
    except KeyError:
        points = []
    return points

def match_with_mapzen(points_by_key, api_key,
  url='https://valhalla.mapzen.com/trace_route',
  **kwargs):
    """
    Public server accepts at most 100 points per request.
    """
    session = FuturesSession(max_workers=MAX_WORKERS)
    params = {'api_key': api_key}

    def build_data(points, **kwargs):
        data = {
          'shape': encode_points_mapzen(points),
          'costing': 'auto',  # Why doesn't 'bus' work?
          }
        if kwargs:
            data.update(kwargs)
        return data

    def parse(key, session, response):
        mpoints = parse_response_mapzen(response)
        if mpoints:
            data = (key, mpoints)
        else:
            data = None
        response.data = data

    futures = (session.post(url, params=params,
      json=build_data(points, **kwargs),
      background_callback=partial(parse, key))
      for key, points in points_by_key.items())

    return dict([f.result().data for f in futures if f.result().data])

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
    try:
        r = response.json()
        pline = []
        for m in r['matchings']:
            pline.extend(polyline.decode(m['geometry'], 6))
        points = [[p[1], p[0]] for p in pline]
    except KeyError:
        points = []
    return points

def match_with_osrm(points_by_key,
  url='http://router.project-osrm.org/match/v1/car', **kwargs):
    """
    Public server accepts at most 100 points per request.
    """
    session = FuturesSession(max_workers=MAX_WORKERS)

    def build_url(points):
        return '{!s}/{!s}'.format(url, encode_points_osrm(points))

    params = {
        'geometries': 'polyline6',
        'overview': 'full',
    }
    if kwargs:
        params.update(kwargs)

    def parse(key, session, response):
        mpoints = parse_response_osrm(response)
        if mpoints:
            data = (key, mpoints)
        else:
            data = None
        response.data = data

    futures = (session.get(build_url(points), params=params,
      background_callback=partial(parse, key))
      for key, points in points_by_key.items())

    return dict([f.result().data for f in futures if f.result().data])

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
    try:
        r = response.json()
        pline = []
        for m in r['matchings']:
            pline.extend(polyline.decode(m['geometry'], 6))
        points = [[p[1], p[0]] for p in pline]
    except KeyError:
        points = []
    return points

def match_with_mapbox(points_by_key, api_key, **kwargs):
    session = FuturesSession(max_workers=MAX_WORKERS)

    url = 'https://api.mapbox.com/matching/v5/mapbox/driving'

    def build_url(points):
        return '{!s}/{!s}'.format(url, encode_points_mapbox(points))

    params = {
        'access_token': api_key,
        'geometries': 'polyline6',
        'overview': 'full',
    }
    if kwargs:
        params.update(kwargs)

    def parse(key, session, response):
        mpoints = parse_response_mapbox(response)
        if mpoints:
            data = (key, mpoints)
        else:
            data = None
        response.data = data

    futures = (session.get(build_url(points), params=params,
      background_callback=partial(parse, key))
      for key, points in points_by_key.items())

    return dict([f.result().data for f in futures if f.result().data])

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
    try:
        r = response.json()
        points = [[p['location']['longitude'], p['location']['latitude']]
          for p in r['snappedPoints']]
    except KeyError:
        points = []
    return points

def match_with_google(points_by_key, api_key):
    session = FuturesSession(max_workers=MAX_WORKERS)

    url = 'https://roads.googleapis.com/v1/snapToRoads'

    def build_params(points):
        return {
          'key': api_key,
          'path': encode_points_google(points),
          'interpolate': True,
          }

    def parse(key, session, response):
        mpoints = parse_response_google(response)
        if mpoints:
            data = (key, mpoints)
        else:
            data = None
        response.data = data

    futures = (session.get(url, params=build_params(points),
      background_callback=partial(parse, key))
      for key, points in points_by_key.items())

    return dict([f.result().data for f in futures if f.result().data])

# # Match wrapper ----------
# def map_match(points_by_key, service, api_key, **kwargs):
#     """
#     """
#     if service == 'mapzen':
#         return match_with_mapzen(points_by_key, api_key, **kwargs)
#     elif service == 'osrm':
#         return match_with_osrm(points_by_key, **kwargs)
#     elif service == 'mapbox':
#         return match_with_mapbox(points_by_key, api_key, **kwargs)
#     elif service == 'google':
#         return match_with_google(points_by_key, api_key)
#     else:
#         valid_services = ['mapzen', 'osrm', 'mapbox', 'google']
#         raise ValueError('Service must be one of {!s}'.format(
#           valid_services))
