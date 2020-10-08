import numpy as np
import responses
import re

from .context import test_feed
from gtfs_map_matcher import *
from gtfs_map_matcher.main import _get_trip_ids


def test_insert_points_by_num():
    xs = np.array([0, 3/4, 1])
    assert np.array_equal(insert_points_by_num(xs, 0),
      xs)
    assert np.array_equal(insert_points_by_num(xs, 1),
      np.array([0, 3/8, 3/4, 1]))
    assert np.array_equal(insert_points_by_num(xs, 2),
      np.array([0, 1/4, 1/2, 3/4, 1]))
    assert np.array_equal(insert_points_by_num(xs, 3),
      np.array([0, 1/4, 1/2, 3/4, 7/8, 1]))

def test_insert_points_by_dist():
    xs = np.array([0, 3/4, 1])
    assert np.array_equal(insert_points_by_dist(xs, 0),
      xs)
    assert np.array_equal(insert_points_by_dist(xs, 1/2),
      xs)
    assert np.array_equal(insert_points_by_dist(xs, 1/4),
      np.array([0, 1/4, 1/2, 3/4, 1]))
    assert np.array_equal(insert_points_by_dist(xs, 2),
      xs)

def test_get_stop_patterns():
    p = get_stop_patterns(test_feed)
    assert 'stop_pattern' in p.columns
    assert isinstance(p.stop_pattern.iat[0], str)

def test_sample_trip_points():
    trip_id = test_feed.trips.trip_id.iat[0]

    # Point dist
    points_and_patterns = sample_trip_points(test_feed, [trip_id], method='distance',
      value=0.010)
    assert len(points_and_patterns) == 1
    points, pattern = points_and_patterns[0]
    assert len(points) > 100

    # Num points
    points_and_patterns = sample_trip_points(test_feed, [trip_id], method='num_points',
      value=30)
    assert len(points_and_patterns) == 1
    points, pattern = points_and_patterns[0]
    assert len(points) == 30

    # Stop multiplier
    points_and_patterns = sample_trip_points(test_feed, [trip_id], method='stop_multiplier',
      value=1)
    assert len(points_and_patterns) == 1
    points, pattern = points_and_patterns[0]
    assert len(points) == len(pattern.split('->'))


def test_get_trip_ids():
    tids = _get_trip_ids(test_feed, [3])
    assert len(tids) > 0

    tids = _get_trip_ids(test_feed, [5])
    assert len(tids) == 0

    tid = test_feed.trips.trip_id.iat[0]
    tids = _get_trip_ids(test_feed, [0], trip_ids=[tid])
    assert tids == [tid]

@responses.activate
def test_match_feed():
    # Create mock API response with a shape that only contains 2 points
    url = 'http://router.project-osrm.org/match/v1/car'  # URL prefix
    url = re.compile(url + '*')
    json = {
        'tracepoints': [{
            'name': 'Gothic Street',
            'location': [174.805053, -41.223382],
            'matchings_index': 0,
            'waypoint_index': 0,
            'alternatives_count': 0
        }, {
            'name': 'Ranui Crescent',
            'location': [174.796743, -41.247018],
            'matchings_index': 0,
            'waypoint_index': 1,
            'alternatives_count': 1
        }],
        'matchings': [{
            'weight': 471.9,
            'duration': 402.1,
            'confidence': 0.0001488819862893731,
            'geometry': 'bmrzFqr|i`@vrC|r@',
            'distance': 3424.5,
            'weight_name': 'routability',
            'legs': [{
                'weight': 471.9,
                'distance': 3424.5,
                'steps': [],
                'summary': '',
                'duration': 402.1
            }]
        }],
        'code': 'Ok'
    }
    responses.add(responses.GET, url, status=200, json=json)

    tid, shid = test_feed.trips[['trip_id', 'shape_id']].iloc[0]

    mm_feed = match_feed(test_feed, 'osrm', trip_ids=[tid])
    test_shapes = test_feed.shapes.loc[lambda x: x.shape_id == shid]
    assert test_shapes.shape[0] > 2

    mm_shapes = mm_feed.shapes.loc[lambda x: x.shape_id == shid]
    assert mm_shapes.shape[0] == 2

def test_get_num_match_calls():
    route_types = test_feed.routes.route_type.unique()
    n = get_num_match_calls(test_feed, route_types=route_types)
    assert n == get_stop_patterns(test_feed).stop_pattern.nunique()

    tid = test_feed.trips.trip_id.iat[0]
    n = get_num_match_calls(test_feed, trip_ids=[tid])
    assert n == 1
