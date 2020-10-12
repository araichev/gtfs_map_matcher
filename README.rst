GTFS Map Matcher
*****************
.. image:: https://travis-ci.org/araichev/gtfs_map_matcher.svg?branch=master
    :target: https://travis-ci.org/araichev/gtfs_map_matcher

A Python 3.8+ library to match General Transit Feed Specification (GTFS) shapes to Open Street Map using any of the following web services:

- OSRM Map Matching (remote or `local <https://github.com/Project-OSRM/osrm-backend>`_ server)
- Mapbox Map Matching (remote server)
- Google Snap to Roads (remote server); snaps to Google's road database instead of Open Street Map


Installation
=============
``poetry add gtfs_map_matcher``


Usage
======
Use as a library as demonstrated in the Jupyter notebook at ``notebooks/examples.ipynb``.


Authors
========
- Alex Raichev (2017-11)


Notes
======
- Project inspired by `bus-router <https://github.com/atlregional/bus-router>`_.
- Development status is Alpha
- Uses semantic versioning
- Thanks to `MRCagney <http://www.mrcagney.com>`_ for partially funding this project


Changes
========

3.0.0, 2020-10-12
-----------------
- Upgraded to Python 3.8 and updated dependencies.
- Removed functions involving the now defunct Mapzen service.
- Refactored some, changing the form of some inputs.
- Bugfixed ``sample_trip_points(method='num_points')``.
- Added type hints.


2.0.0, 2017-11-23
--------------------
- Improved the interface to the various sample point methods


1.0.0, 2017-11-23
--------------------
- First release