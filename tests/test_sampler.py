import numpy as np

from .context import welly_feed
from bus_router import *


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
    p = get_stop_patterns(welly_feed)
    assert 'stop_pattern' in p.columns
    assert isinstance(p.stop_pattern.iat[0], str)

def test_build_sample_points():
    assert 1 == 0