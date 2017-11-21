import numpy as np
import responses

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
    d = sample_trip_points(test_feed, [trip_id], 30)
    assert len(d) == 1
    pattern, points = list(d.items())[0]
    assert len(points) == 30

    d = sample_trip_points(test_feed, [trip_id], point_dist=0.010)
    assert len(d) == 1
    pattern, points = list(d.items())[0]
    assert len(points) > 100

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
    url = 'https://valhalla.mapzen.com/trace_route'
    json = {
        'trip': {
            'summary': {
                'length': 1.946,
                'min_lon': 174.828232,
                'max_lat': -41.130627,
                'min_lat': -41.137566,
                'max_lon': 174.842667,
                'time': 224
            },
            'status': 0,
            'units': 'kilometers',
            'locations': [{
                'lon': 174.843231,
                'lat': -41.137424,
                'type': 'break'
            }, {
                'lon': 174.828156,
                'lat': -41.130638,
                'type': 'break'
            }],
            'status_message': 'Found route between points',
            'language': 'en-US',
            'legs': [{
                'summary': {
                    'length': 1.946,
                    'min_lon': 174.828232,
                    'max_lat': -41.130627,
                    'min_lat': -41.137566,
                    'max_lon': 174.842667,
                    'time': 224
                },
                'shape': 'ht{_Fscui`@bHhA'  # Contains 2 points
            }]
        }
    }
    responses.add(responses.POST, url, status=200, json=json)

    tid, shid = test_feed.trips[['trip_id', 'shape_id']].iloc[0].values
    mm_feed = match_feed(test_feed, 'mapzen', 'key', trip_ids=[tid])
    test_shapes = test_feed.shapes[test_feed.shapes.shape_id == shid]
    assert test_shapes.shape[0] > 2
    mm_shapes = mm_feed.shapes[mm_feed.shapes.shape_id == shid]
    assert mm_shapes.shape[0] == 2

def test_get_num_match_calls():
    route_types = test_feed.routes.route_type.unique()
    n = get_num_match_calls(test_feed, route_types=route_types)
    assert n == get_stop_patterns(test_feed).stop_pattern.nunique()

    tid = test_feed.trips.trip_id.iat[0]
    n = get_num_match_calls(test_feed, trip_ids=[tid])
    assert n == 1
