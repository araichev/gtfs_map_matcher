GTFS Map Matcher
*****************
.. image:: https://travis-ci.org/araichev/gtfs_map_matcher.svg?branch=master
    :target: https://travis-ci.org/araichev/gtfs_map_matcher

A Python 3.4+ library to match General Transit Feed Specification (GTFS) shapes to Open Street Map using any of the following web services:

- Mapzen Map Matching (remote or `local <https://github.com/valhalla/valhalla>`_ server)
- OSRM Map Matching (remote or `local <https://github.com/Project-OSRM/osrm-backend>`_ server)
- Mapbox Map Matching (remote server)
- Google Snap to Roads (remote server); snaps to Google's road database instead of Open Street Map


Installation
=============
``pipenv install gtfs_map_matcher``


Usage
======
Use as a library as demonstrated in the Jupyter notebook at ``ipynb/examples.ipynb``.


Authors
========
- Alexander Raichev (2017-11)


Notes
======
- Project inspired by `bus-router <https://github.com/atlregional/bus-router>`_.
- Development status is Alpha
- Uses semantic versioning
- Thanks to `MRCagney <http://www.mrcagney.com>`_ for partially funding this project


Changes
========

v2.0.0, 2017-11-23
--------------------
- Improved the interface to the various sample point methods


v1.0.0, 2017-11-23
--------------------
- First release