import os
import pathlib as pl
from typing import List, Optional

import pandas as pd
import numpy as np

from . import matchers


ROOT = pl.Path(os.path.abspath(os.path.dirname(__file__)))
DATA_DIR = ROOT / "data"

# GTFS route types of vehicles that travel on the road
ROAD_ROUTE_TYPES = [0, 3, 5]


def insert_points_by_num(xs: np.array, n: int) -> np.array:
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
            k = int(max(1, np.ceil(d_i / d_j - 1)))

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
        xs = np.concatenate(
            [
                xs[: i + 1],
                [xs[i] + s * d_i / (k + 1) for s in range(1, k + 1)],
                xs[i + 1 :],
            ]
        )

        # Update n
        n -= k

    return xs


def insert_points_by_dist(xs: np.array, d: float) -> np.array:
    """
    Given a strictly increasing NumPy array ``xs`` of at least two
    numbers x_1 < x_2 < ... < x_r and a nonnegative float ``d``,
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
    bins = [i * d for i in range(int(D / d))] + [xs[-1]]
    filled_bins = np.digitize(xs, bins) - 1
    ys = np.array([i * d for i in range(len(bins)) if i not in filled_bins])
    return np.sort(np.concatenate([xs, ys]))


def get_stop_patterns(
    feed: "Feed", trip_ids: Optional[List[str]] = None, sep: str = "->"
) -> pd.DataFrame:
    """
    Append to the DataFrame``feed.trips`` the additional column

    - ``'stop_pattern'``: string; the stop IDs along the
      trip joined by the separator ``sep``

    and return the resulting DataFrame.
    Restrict to the given trip IDs (defaults to all trip IDs).
    """
    st = feed.stop_times.sort_values(["trip_id", "stop_sequence"])

    if trip_ids is not None:
        st = st[st.trip_id.isin(trip_ids)].copy()

    def get_pattern(group):
        return group.stop_id.str.cat(sep=sep)

    f = (
        st.groupby("trip_id")
        .apply(get_pattern)
        .reset_index()
        .rename(columns={0: "stop_pattern"})
    )

    return feed.trips.merge(f)


def sample_trip_points(
    feed: "Feed",
    trip_ids: Optional[List[str]] = None,
    method: str = "num_points",
    value: float = 100,
) -> List[List]:
    """
    Given a GTFS feed (GTFSTK Feed instance),
    preferably with a ``feed.stop_times.shape_dist_traveled`` column,
    return a list of pairs of the form

    list of (longitude, latitude) sample points along trip,
    stop pattern

    The sample points are chosen by one of three methods.
    Consider a stop pattern with k stops and its representative trip.

    1. If ``method == 'distance'`` and d = ``value`` is a positive
      float, then do the following. Interpret d as a distance measured
      in the the feed's distance units. If the trip has a shape and all
      the ``shape_dist_traveled`` values of the trip's stop times are
      present, then choose as sample points the stops of the trip
      along with the least number of points sampled along the trip shape
      so that consecutive sample points are no more than distance d apart.
      Else, choose as sample points the stops.
    2. Else if ``method == 'num_points'`` and n = ``value`` is a
      positive integer, then do the following. If k < n, the trip has a
      shape, and all the ``shape_dist_traveled`` values of the trip's
      stop times are present, then choose as sample points the k stops
      of the trip along with n - k additional points somewhat
      evenly sampled from the trip's shape, all in the order of the
      trip's travel. Else if k > n, then choose as sample points
      only n stops: no points (n=0); the first stop (n=1);
      the first and the last stop (n=2);
      the first, last, and n - k random stops (n > 2).
      Else, choose as sample points the k stops.
    3. Else if ``method == 'stop_multiplier'`` and m = ``value`` is a
      positive float, then do the following.
      Set n = int(m*k) and choose n sample points as in the method
      ``'num_points'``.  In particular, using ``value = 1`` will choose
      the stop points as sample points. Note that in this method n
      depends on k, which varies for each trip, whereas as in
      the ``num_points`` method, n is chosen independently of k.

    Raise a value error if the method and value given differ from the
    options above.

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
    t = t[t["trip_id"].isin(trip_ids)].copy()
    if "shape_id" not in t.columns:
        # Insert NaN shape IDs for convenient processing later
        t["shape_id"] = np.nan
    t = (
        t.sort_values(["stop_pattern", "shape_id"])
        .groupby("stop_pattern")
        .agg("first")
        .reset_index()
    )
    trip_ids = t.trip_id

    # Get stops times for the representative trips
    st = feed.stop_times
    st = st[st["trip_id"].isin(trip_ids)]

    # Join in stop patterns and shapes
    st = st.merge(t[["trip_id", "shape_id", "stop_pattern"]])

    # Join in stop locations
    st = st.merge(feed.stops[["stop_id", "stop_lon", "stop_lat"]]).sort_values(
        ["stop_pattern", "stop_sequence"]
    )

    # Create shape_dist_traveled column if it does not exist
    if "shape_dist_traveled" not in st:
        st["shape_dist_traveled"] = np.nan

    # Get shape geometries
    geom_by_shape = feed.build_geometry_by_shape(shape_ids=t.shape_id) or {}

    # Build dict stop pattern -> list of (lon, lat) sample points.
    # Since it contains unique stop patterns, no computations will be repeated.
    points_and_patterns = []
    if method == "distance" and value > 0:
        # Use stop points and insert more points by distance
        d = value
        for pattern, group in st.groupby("stop_pattern"):
            shape_id = group["shape_id"].iat[0]
            if (shape_id in geom_by_shape) and group[
                "shape_dist_traveled"
            ].notnull().all():
                # Scale distances to interval [0, 1] to avoid changing
                # coordinate systems.
                D = group["shape_dist_traveled"].max()
                dists = group["shape_dist_traveled"].values / D
                new_dists = insert_points_by_dist(dists, d / D)
                geom = geom_by_shape[shape_id]
                points = [
                    list(geom.interpolate(x, normalized=True).coords[0])
                    for x in new_dists
                ]
            else:
                # Best can do is use the stop points
                points = group[["stop_lon", "stop_lat"]].values.tolist()

            points_and_patterns.append([points, pattern])

    elif method == "num_points" and value > 0:
        # Use stop points and insert more points by number
        n = value
        for pattern, group in st.groupby("stop_pattern"):
            shape_id = group["shape_id"].iat[0]
            k = group.shape[0]  # Number of stops along trip
            if (
                k < n
                and (shape_id in geom_by_shape)
                and group["shape_dist_traveled"].notnull().all()
            ):
                # Scale distances to interval [0, 1] to avoid changing
                # coordinate systems.
                D = group["shape_dist_traveled"].max()
                dists = group["shape_dist_traveled"].values / D
                new_dists = insert_points_by_num(dists, n - k)
                geom = geom_by_shape[shape_id]
                points = [
                    list(geom.interpolate(d, normalized=True).coords[0])
                    for d in new_dists
                ]
            elif k > n:
                # Use n stop points only
                if n == 0:
                    points = []
                elif n == 1:
                    # First stop
                    points = group[["stop_lon", "stop_lat"]].iloc[0].values.tolist()
                elif n == 2:
                    # First and last stop
                    ix = [0, k - 1]
                    points = group[["stop_lon", "stop_lat"]].iloc[ix].values.tolist()
                else:
                    # First, last, and n - 2 random stops
                    ix = np.concatenate(
                        [
                            [0, k - 1],
                            np.random.choice(range(1, k - 1), n - 2, replace=False),
                        ]
                    )
                    ix = sorted(ix)
                    points = group[["stop_lon", "stop_lat"]].iloc[ix].values.tolist()
            else:
                # Best can do is use the stop points
                points = group[["stop_lon", "stop_lat"]].values.tolist()

            points_and_patterns.append([points, pattern])

    elif method == "stop_multiplier" and value > 0:
        m = value
        for pattern, group in st.groupby("stop_pattern"):
            shape_id = group["shape_id"].iat[0]
            k = group.shape[0]  # Number of stops along trip
            n = int(m * k)
            if (
                k < n
                and (shape_id in geom_by_shape)
                and group["shape_dist_traveled"].notnull().all()
            ):
                # Scale distances to interval [0, 1] to avoid changing
                # coordinate systems.
                D = group["shape_dist_traveled"].max()
                dists = group["shape_dist_traveled"].values / D
                new_dists = insert_points_by_num(dists, n - k)
                geom = geom_by_shape[shape_id]
                points = [
                    list(geom.interpolate(d, normalized=True).coords[0]) + [d]
                    for d in new_dists
                ]
            elif k > n:
                # Use n stop points only
                if n == 0:
                    points = []
                elif n == 1:
                    # First stop
                    points = group[["stop_lon", "stop_lat"]].iloc[0].values.tolist()
                elif n == 2:
                    # First and last stop
                    ix = [0, k - 1]
                    points = group[["stop_lon", "stop_lat"]].iloc[ix].values.tolist()
                else:
                    # First, last, and n - 2 random stops
                    ix = np.concatenate(
                        [
                            [0, k - 1],
                            np.random.choice(range(1, k - 1), n - 2, replace=False),
                        ]
                    )
                    ix = sorted(ix)
                    points = group[["stop_lon", "stop_lat"]].iloc[ix].values.tolist()
            else:
                # Best can do is use the stop points
                points = group[["stop_lon", "stop_lat"]].values.tolist()

            points_and_patterns.append([points, pattern])

    else:
        raise ValueError("Invalid method-value combination")

    return points_and_patterns


def _get_trip_ids(
    feed: "Feed", route_types: List[int], trip_ids: Optional[List[str]] = None
) -> np.array:
    """
    Helper function.
    Given a GTFS feed (GTFSTK Feed instance), get the trip IDs of
    the given route types.
    If a list of trip IDs is given, then return those instead.
    """
    if trip_ids is None:
        t = feed.trips.merge(feed.routes)
        trip_ids = t.loc[t["route_type"].isin(route_types), "trip_id"]
    return trip_ids


def match_feed(
    feed: "Feed",
    service: str,
    api_key: Optional[str] = None,
    route_types: List[int] = ROAD_ROUTE_TYPES,
    trip_ids: Optional[List[str]] = None,
    method: str = "num_points",
    value: float = 100,
    **service_opts
) -> "Feed":
    """
    Given a GTFS feed (GTFSTK Feed instance), the name of a map matching
    web service (``'mapzen'``, ``'osrm'``, ``'mapbox'``, or
    ``'google'``) and an API key for that service, do the following.

    #. Select all trips of the given route types (defaults to road-based
      route types) xor of the given trip IDs (defaults to all trip IDs).
    #. Sample trip points using the function :func:`sample_trip_points`
      with the arguments ``method`` and ``value``. Only one list of
      sample points per stop pattern (not per trip ID) will be created.
    #. Snap the sample points to a map and route through those points
      using the given web service via the appropriate map matching
      function in the ``matchers`` module. Local Mapzen and OSRM
      services can also be used by giving a custom URL. Service calls
      are made asynchronously.
    #. Use the new shapes obtained to replace the old shapes (if any)
      of the selected trips only.  The shapes of other trips will
      remain unchanged.
    #. Return the resulting new GTFS feed.

    NOTES:

    - Extra parameters can be passed to the map matching function of
      choice using the extra keyword arguments ``service_opts``.
    - At present, the map matching services only work well for road
      travel, hence the default setting
      ``route_types=ROAD_ROUTE_TYPES``. Not yet suitable for rail,
      ferry, or gondola travel.
    - One map matching API call is made per (unique) stop pattern of
      the given trip set. Use the function
      :func:`get_num_match_calls` to compute the number of such
      calls.
    - At present, each map matching service accepts at most 100 points
      per query, so choosing a method that creates more than 100 points
      for a particular stop pattern will return empty results. This
      limit can be avoided by using a local deployment of the Mapzen
      or OSRM service.
    - Every empty map matching service result will be ignored and the
      corresponding feed shape(s) will not be updated, that is, the
      original shape(s) (if any) in ``feed`` will be copied over to the
      new feed.

    """
    # Select relevant trip IDs
    trip_ids = _get_trip_ids(feed, route_types, trip_ids)

    # Get sample points by stop pattern
    points_and_patterns = sample_trip_points(feed, trip_ids, method=method, value=value)

    # Map match sample points
    if service == "osrm":
        mpoints_and_patterns = matchers.match_with_osrm(
            points_and_patterns, **service_opts
        )
    elif service == "mapbox":
        mpoints_and_patterns = matchers.match_with_mapbox(
            points_and_patterns, api_key, **service_opts
        )
    elif service == "google":
        mpoints_and_patterns = matchers.match_with_google(
            points_and_patterns, api_key, **service_opts
        )
    else:
        valid_services = ["osrm", "mapbox", "google"]
        raise ValueError("Service must be one of {!s}".format(valid_services))

    mpoints_by_pattern = {pattern: mpoints for mpoints, pattern in mpoints_and_patterns}

    # Create new feed with matched shapes found and old shapes
    # for the rest of the trips
    t = get_stop_patterns(feed, trip_ids)
    t = t[t["stop_pattern"].isin(mpoints_by_pattern)].copy()
    mpoints_by_shape = {
        shape: mpoints_by_pattern[pattern]
        for shape, pattern in t[["shape_id", "stop_pattern"]].values
    }
    S = [
        [shape, i, lon, lat]
        for shape, mpoints in mpoints_by_shape.items()
        for i, (lon, lat) in enumerate(mpoints)
    ]
    new_shapes = pd.DataFrame(
        S, columns=["shape_id", "shape_pt_sequence", "shape_pt_lon", "shape_pt_lat"]
    )
    feed = feed.copy()

    shapes = feed.shapes.copy()
    feed.shapes = pd.concat(
        [shapes[~shapes.shape_id.isin(mpoints_by_shape)], new_shapes,]
    )

    return feed


def get_num_match_calls(
    feed: "Feed",
    route_types: List[int] = ROAD_ROUTE_TYPES,
    trip_ids: Optional[List[str]] = None,
) -> int:
    """
    Return the number of unique stop patterns for the given GTFS feed
    (GTFSTK Feed instance) and trip IDs (defaults to all trip IDs)
    by calling the function :func:`get_stop_patterns` and counting
    unique stop patterns.
    This number also equals the number of map matching API calls
    made by the function :func:`create_shapes` with the given
    route types and trip IDs.
    """
    trip_ids = _get_trip_ids(feed, route_types, trip_ids)
    p = get_stop_patterns(feed, trip_ids)
    return p.stop_pattern.nunique()
