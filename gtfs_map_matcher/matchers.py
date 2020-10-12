"""
API functions for several popular map matching services.
"""
from typing import List
from functools import partial

from loguru import logger
import polyline
from requests_futures.sessions import FuturesSession


MAX_WORKERS = 50  # Max number of concurrent threads for async HTTP requests


# OSRM matching functions ----------
def encode_points_osrm(points: List[List[float]]) -> str:
    """
    Given a list of longitude-latitude points, return their string
    representation suitable for OSRM's Map Matching API
    """
    return (";").join(["{!s},{!s}".format(p[0], p[1]) for p in points])


def decode_points_osrm(points: str) -> List[List[float]]:
    """
    Inverse of function :func:`encode_points_osrm`.
    """
    return [[float(x) for x in p.split(",")] for p in points.split(";")]


def parse_response_osrm(response):
    r = response.json()
    if "matchings" in r:
        pline = []
        for m in r["matchings"]:
            pline.extend(polyline.decode(m["geometry"], 6))
        points = [[p[1], p[0]] for p in pline]
    else:
        logger.warning(r)
        points = []

    return points


def match_with_osrm(
    points_and_ids: List[List],
    url: str = "http://router.project-osrm.org/match/v1/car",
    **kwargs
) -> List[List]:
    """
    Public server accepts at most 100 points per request.
    """
    session = FuturesSession(max_workers=MAX_WORKERS)

    def build_url(points):
        return "{!s}/{!s}".format(url, encode_points_osrm(points))

    params = {
        "geometries": "polyline6",
        "overview": "full",
    }
    if kwargs:
        params.update(kwargs)

    def parse(id_, response, *args, **kwargs):
        mpoints = parse_response_osrm(response)
        if mpoints:
            data = (mpoints, id_)
        else:
            data = None
        response.data = data

    futures = (
        session.get(
            build_url(points), params=params, hooks={"response": partial(parse, id_)},
        )
        for points, id_ in points_and_ids
    )

    return [f.result().data for f in futures if f.result().data]


# Mapbox (which uses OSRM) map matching functions ----------
def encode_points_mapbox(points: List[List[float]]) -> str:
    """
    Given a list of longitude-latitude points, return their dictionary
    representation suitable for Mapbox's Map Matching API;
    see https://www.mapbox.com/api-documentation/#map-matching
    """
    return (";").join(["{!s},{!s}".format(p[0], p[1]) for p in points])


def decode_points_mapbox(points: str) -> List[List[float]]:
    """
    Inverse of function :func:`encode_points_mapzen`.
    """
    return [[float(x) for x in p.split(",")] for p in points.split(";")]


def parse_response_mapbox(response):
    r = response.json()
    if "matchings" in r:
        pline = []
        for m in r["matchings"]:
            pline.extend(polyline.decode(m["geometry"], 6))
        points = [[p[1], p[0]] for p in pline]
    else:
        logger.warning(r)
        points = []

    return points


def match_with_mapbox(points_and_ids: List[List], api_key: str, **kwargs):
    session = FuturesSession(max_workers=MAX_WORKERS)

    url = "https://api.mapbox.com/matching/v5/mapbox/driving"

    def build_url(points):
        return "{!s}/{!s}".format(url, encode_points_mapbox(points))

    params = {
        "access_token": api_key,
        "geometries": "polyline6",
        "overview": "full",
    }
    if kwargs:
        params.update(kwargs)

    def parse(id_, response, *args, **kwargs):
        mpoints = parse_response_mapbox(response)
        if mpoints:
            data = (mpoints, id_)
        else:
            data = None
        response.data = data

    futures = (
        session.get(
            build_url(points), params=params, hooks={"response": partial(parse, id_)},
        )
        for points, id_ in points_and_ids
    )

    return [f.result().data for f in futures if f.result().data]


# def match_with_mapbox(points_and_ids: List[List], api_key: str, **kwargs):
#     session = FuturesSession(max_workers=MAX_WORKERS)

#     url = f"https://api.mapbox.com/matching/v5/mapbox/driving?access_token={api_key}"

#     headers = {
#         "Content-Type": "application/x-www-form-urlencoded",
#     }
#     def make_params(points, kwargs):
#         params = {
#             "geometries": "polyline6",
#             "overview": "full",
#             "coordinates": encode_points_mapbox(points),
#         }

#         if kwargs:
#             params.update(kwargs)

#         return params

#     def parse(id_, response, *args, **kwargs):
#         mpoints = parse_response_mapbox(response)
#         if mpoints:
#             data = (mpoints, id_)
#         else:
#             data = None
#         response.data = data

#     futures = (
#         session.post(
#             url, data=make_params(points, kwargs), headers=headers, hooks={"response": partial(parse, id_)},
#         )
#         for points, id_ in points_and_ids
#     )

#     return [f.result().data for f in futures if f.result().data]


# Google map matching functions -------------
def encode_points_google(points: List[List]) -> str:
    """
    Given a list of longitude-latitude points, return their string
    representation suitable for Google's Snap to Roads API;
    see https://developers.google.com/maps/documentation/roads/snap.
    """
    return ("|").join(["{:.06f},{:.06f}".format(p[1], p[0]) for p in points])


def decode_points_google(points: str) -> List[List]:
    """
    Inverse of function :func:`encode_points_google`.
    """
    return [[float(x) for x in p.split(",")[::-1]] for p in points.split("|")]


def parse_response_google(response):
    r = response.json()
    if "snappedPoints" in r:
        points = [
            [p["location"]["longitude"], p["location"]["latitude"]]
            for p in r["snappedPoints"]
        ]
    else:
        logger.warning(r)
        points = []

    return points


def match_with_google(points_and_ids: List[List], api_key: str):
    session = FuturesSession(max_workers=MAX_WORKERS)

    url = "https://roads.googleapis.com/v1/snapToRoads"

    def build_params(points):
        return {
            "key": api_key,
            "path": encode_points_google(points),
            "interpolate": True,
        }

    def parse(id_, response, *args, **kwargs):
        mpoints = parse_response_google(response)
        if mpoints:
            data = (mpoints, id_)
        else:
            data = None
        response.data = data

    futures = (
        session.get(
            url, params=build_params(points), hooks={"response": partial(parse, id_)},
        )
        for points, id_ in points_and_ids
    )

    return [f.result().data for f in futures if f.result().data]
