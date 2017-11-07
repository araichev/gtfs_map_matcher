import pandas as pd
import numpy as np
import requests

from . import matchers


def insert_points_by_num(xs, n):
    """
    Given a strictly increasing NumPy array ``xs`` of at least two
    numbers x_1 < x_2 < ... < x_r and a nonnegative integer ``n``,
    insert into the list ``n`` more numbers between x_1 and x_r
    in a spread-out way.
    Return the resulting list as a NumPy array.
    """
    while n > 0:
        diffs = np.diff(xs)

        # Get indices i, j of biggest diffs d_i > d_j.
        # Use the method at https://stackoverflow.com/a/23734295 for speed.
        try:
            indices = np.argpartition(diffs, -2)[-2:]
            i, j = indices[np.argsort(diffs[indices])[::-1]]
            d_i, d_j = diffs[i], diffs[j]

            # Choose k => 1 least such that d_i/(k + 1) < d_j
            # with the intent of inserting k evenly spaced points
            # between x_i and x_{i+1}
            k = int(max(1, np.ceil(d_i/d_j - 1)))

            # Shrink k if necessary so as not to exceed number of
            # remaining points
            k = min(k, n)
        except ValueError:
            # Here xs has only two elements, hence diffs has only one element.
            # Using try-except because faster than if-else.
            i = 0
            d_i = diffs[0]
            k = n

        # Insert the k points, updating xs
        xs = np.concatenate([
          xs[:i + 1],
          [xs[i] + s*d_i/(k + 1) for s in range(1, k + 1)],
          xs[i + 1:]
          ])

        # Update n
        n -= k

    return xs

def insert_points_by_dist(xs, d):
    """
    Given a strictly increasing NumPy array ``xs`` of at least two
    numbers x_1 < x_2 < ... < x_r and a nonnegative float ``dist``,
    partition the interval [x_1, x_r] in bins of size ``d``,
    except for the last bin, which might be shorter.
    Form a new array of numbers (points in the intevral) as follows.
    Iterate through the bins from left to right.
    If a point of ``xs`` lies in the bin, then append that point to the
    new arary.
    Otherwise, append the left endpoint of the bin to the new array.
    Return the resulting array, which will have a maximum distance of
    ``d`` between consecutive points.
    """
    if xs.size < 2 or d >= xs[-1] - xs[0] or d <= 0:
        return xs

    D = xs[-1] - xs[0]
    bins = [i*d for i in range(int(D/d))] + [xs[-1]]
    filled_bins = np.digitize(xs, bins) - 1
    ys = np.array([i*d for i in range(len(bins)) if i not in filled_bins])
    return np.sort(np.concatenate([xs, ys]))

def get_stop_patterns(feed, sep='-'):
    """
    Append to the DataFrame``feed.trips`` the additional column

    - ``'stop_pattern'``: string; the stop IDs along the
      trip joined by the separator ``sep``

    and return the resulting DataFrame.
    """
    st = feed.stop_times.sort_values(['trip_id', 'stop_sequence'])

    def get_pattern(group):
        return group.stop_id.str.cat(sep=sep)

    f = st.groupby('trip_id').apply(get_pattern).reset_index().rename(
      columns={0: 'stop_pattern'})

    return feed.trips.merge(f)

def sample_trip_points(feed, trip_ids=None, num_points=100, point_dist=None):
    """
    Given a GTFS feed (GTFSTK Feed instance),
    preferably with a ``feed.stop_times.shape_dist_traveled`` column,
    return a dictionary of the form

    stop pattern
    -> list of (longitude, latitude) sample points along trip.

    Regarding the list of sample points, first suppose
    that ``point_dist`` is ``None`` and consider a stop pattern
    with k stops and its representative trip.
    If k < n, the trip has a shape, and all the ``shape_dist_traveled``
    values of the trip's stop times are present, then the sample points
    comprise the k stops of the trip along with ``n - k`` additional
    points somewhat evenly sampled from the trip's shape, all in the
    order of the trip's travel.
    Else if k > n, then the sample points include only n stops:
    no points (n=0); the first stop (n=1);
    the first and the last stop (n=2);
    the first, last, and n - k random stops (n > 2).
    Else, the sample points are the k stops.

    Now suppose that a positive float ``point_dist`` is given and is
    measured in the distance units of the feed.
    If the trip has a shape and all the ``shape_dist_traveled`` values
    of the trip's stop times are present, then the sample points
    comprise the k stops of the trip along with the least number points
    sampled along the trip shape so that consecutive points are no
    more than ``point_dist`` apart.
    Else, the sample points are the k stop.

    If a list of trip IDs is given, then restrict to the stop patterns
    of those trips.
    Otherwise, build sample points for every stop pattern.

    NOTES:

    - In the case of choosing random stops, the choices will be the same
      for across all runs of this function (by using a fixed
      random number generator seed), which is good for debugging.
    - The implementation assumes that if two trips have the same stop
      pattern, then they also have the same shape.
    """
    # Seed random number generator for reproducible results
    np.random.seed(42)

    if trip_ids is None:
        # Use all trip IDs
        trip_ids = feed.trips.trip_id

    # Get stop patterns and choose a representative trip for each one
    t = get_stop_patterns(feed)
    t = t.sort_values(['stop_pattern', 'shape_id'])\
      .groupby('stop_pattern').agg('first').reset_index()
    trip_ids = t.trip_id

    # Get stops times for the representative trips
    st = feed.stop_times
    st = st[st['trip_id'].isin(trip_ids)]

    # Join in stop patterns and shapes
    st = st.merge(t[['trip_id', 'shape_id', 'stop_pattern']])

    # Join in stop locations
    st = st.merge(feed.stops[['stop_id', 'stop_lon', 'stop_lat']])\
      .sort_values(['stop_pattern', 'stop_sequence'])

    # Create shape_dist_traveled column if it does not exist
    if 'shape_dist_traveled' not in st:
        st['shape_dist_traveled'] = np.nan

    # Get shape geometries
    geom_by_shape = feed.build_geometry_by_shape(shape_ids=t.shape_id) or {}

    # Build dict stop pattern -> list of (lon, lat) sample points.
    # Since t contains unique stop patterns, no computations will be repeated.
    points_by_sp = {}
    if point_dist is not None:
        # Insert points into stop points by distance
        for stop_pattern, group in st.groupby('stop_pattern'):
            shape_id = group['shape_id'].iat[0]
            if (shape_id in geom_by_shape)\
              and group['shape_dist_traveled'].notnull().all():
                # Scale distances to interval [0, 1] to avoid changing
                # coordinate systems.
                D = group['shape_dist_traveled'].max()
                dists = group['shape_dist_traveled'].values/D
                new_dists = insert_points_by_dist(dists, point_dist/D)
                geom = geom_by_shape[shape_id]
                points = [list(geom.interpolate(d, normalized=True).coords[0])
                  for d in new_dists]
            else:
                # Best can do is use the stop points
                points = group[['stop_lon', 'stop_lat']].values.tolist()

            points_by_sp[stop_pattern] = points
    else:
        # Insert points into stop points by number
        n = num_points
        for stop_pattern, group in st.groupby('stop_pattern'):
            shape_id = group['shape_id'].iat[0]
            k = group.shape[0]  # Number of stops along trip
            if k < n and (shape_id in geom_by_shape)\
              and group['shape_dist_traveled'].notnull().all():
                # Scale distances to interval [0, 1] to avoid changing
                # coordinate systems.
                D = group['shape_dist_traveled'].max()
                dists = group['shape_dist_traveled'].values/D
                new_dists = insert_points_by_num(dists, n - k)
                geom = geom_by_shape[shape_id]
                points = [
                  list(geom.interpolate(d, normalized=True).coords[0]) + [d]
                  for d in new_dists]
            elif k > n:
                # Use n stop points only
                if n == 0:
                    points = []
                elif n == 1:
                    # First stop
                    points = group[['stop_lon', 'stop_lat']
                      ].iloc[0].values.tolist()
                elif n == 2:
                    # First and last stop
                    ix = [0, k - 1]
                    points = group[['stop_lon', 'stop_lat']
                      ].iloc[ix].values.tolist()
                else:
                    # First, last, and n - 2 random stops
                    ix = np.concatenate([[0, k - 1],
                      np.random.choice(range(1, k - 1), n - 2, replace=False)])
                    ix = sorted(ix)
                    points = group[['stop_lon', 'stop_lat']
                      ].iloc[ix].values.tolist()
            else:
                # Best can do is use the stop points
                points = group[['stop_lon', 'stop_lat']].values.tolist()

            points_by_sp[stop_pattern] = points

    return points_by_sp

def map_match(feed, service, api_key, custom_url=None, service_kwargs=None,
  route_types=[0, 3, 5], num_points=100, point_dist=None):
    """
    """
    # Get sample points for stop patterns of the given route types
    t = feed.trips.merge(feed.routes)
    t = t[t['route_type'].isin(route_types)].copy()
    points_by_pattern = sample_trip_points(feed, t.trip_id,
      num_points=num_points, point_dist=point_dist)

    # Match sample points to map
    if service == 'mapzen':
        if custom_url is not None:
            def matcher(points):
                return matchers.match_with_mapzen(points, api_key,
                  url=custom_url, kwargs=service_kwargs)
        else:
            def matcher(points):
                return matchers.match_with_mapzen(points, api_key,
                  kwargs=service_kwargs)

    elif service == 'osrm':
        if custom_url is not None:
            def matcher(points):
                return matchers.match_with_osrm(points, api_key,
                  url=custom_url, kwargs=service_kwargs)
        else:
            def matcher(points):
                return matchers.match_with_osrm(points, api_key,
                  kwargs=service_kwargs)

    elif service == 'mapbox':
        def matcher(points):
            return matchers.match_with_mapbox(points, api_key,
              kwargs=service_kwargs)

    elif service == 'google':
        def matcher(points):
            return matchers.match_with_google(points, api_key)

    else:
        valid_services = ['mapzen', 'osrm', 'mapbox', 'google']
        raise ValueError('Service must be one of {!s}'.format(
          valid_services))

    print('Map matching {!s} stop patterns...'.format(len(points_by_pattern)))
    mpoints_by_pattern = {}
    for i, (pattern, points) in enumerate(points_by_pattern.items()):
        print(i + 1)
        try:
            mpoints = matcher(points)
            if mpoints:
                mpoints_by_pattern[pattern] = mpoints
        except requests.HTTPError:
            # Skip failed match
            continue

    # Create new feed with matched shapes found and old shapes
    # for the rest of the trips
    t = get_stop_patterns(feed)
    t = t[t['stop_pattern'].isin(mpoints_by_pattern)].copy()
    mpoints_by_shape = {shape: mpoints_by_pattern[pattern]
      for shape, pattern in t[['shape_id', 'stop_pattern']].values}
    S = [[shape, i, lon, lat] for shape, mpoints in mpoints_by_shape.items()
      for i, (lon, lat) in enumerate(mpoints)]
    new_shapes = pd.DataFrame(S, columns=['shape_id', 'shape_pt_sequence',
      'shape_pt_lon', 'shape_pt_lat'])
    feed = feed.copy()
    feed.shapes.loc[feed.shapes['shape_id'].isin(new_shapes.shape_id)] =\
        new_shapes

    return feed
