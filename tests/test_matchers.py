import re
import responses

from .context import test_feed
from gtfs_map_matcher import *


points_by_key = {
    'bingo': [
        [174.843234, -41.137425],
        [174.828152, -41.130639],
    ],
    'bongo': [
        [174.80496399999998, -41.22333],
        [174.796785, -41.247057],
    ]
}

@responses.activate
def test_match_with_mapzen():
    # Create mock response
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
                'shape': 'jsymmAsqpnlIl@\\|@\\\\^\\xAFxBU|@_@z@k@^sA\\}@?{@}@_@{@UyB}E\\uD?s`@?u@?gX{@wS_@iC?sF^cFxAcV`SyCvCgDxByB|@yBz@]?kF^sG\\sFz@uDzAeEtEyBvCcGfNO|@U\\cAvD{ArE{AtEeOxk@mAnIk@tE_@tE|@?t@z@\\^TxAF^?\\Gz@]|@}@|@t@rEVvD?vCLrG\\fMl@`h@FxB~Hrn@lArGxLju@iHnH_vAfaBtOxVzElKtJha@rk@|{Bj@vCf@nI?jLGtDm@rFoDhMaCvDgDtDwHrFiCzAgC\\qH|@zAzj@FvCWtE{@vCsBvC_ItF{ExBy`Abe@}OpGiRrFck@lK'
            }]
        }
    }
    responses.add(responses.POST, url, status=200, json=json)

    r = match_with_mapzen(points_by_key, 'api_key')
    assert isinstance(r, dict)
    assert len(r) == len(points_by_key)

@responses.activate
def test_match_with_osrm():
    # Create mock response
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
            'geometry': 'jlasmAybgllIo@o@qGeHwAOwCSsA@iARoAdA_AtAiB~DbClDjHbLpCpChQxQht@vg@hInBnOfHtMdIzp@hm@vY|Pdj@fRbUzG~O|EhMnBjJnEjrA|aAtEbE^m@f@_@j@Mn@@j@Rb@b@^v@NbA?fAS`Aa@t@tVfg@rNzVlM~OpZxWbKbHhLlEzMhCtMl@z@Df]p@fg@VtaD~Af\\LdDB|c@Pvc@p@zIr@nItAlGfBnKzDrP~G`PxIpHdE~KrStFlLfHbPlLzUvIrPrNnY~IrNhHhKzGfItBbBhDfClQxLvHvIxEzFhEvMlGxRjN`f@vA`HpCdGxFzGtDtBhQjJvW}}@f@_BXmA`@oAtGkVtDiVjA_GpBgB|D_@xBp@zEzDfDjD~Yd[zIlCnJ\\lReDnI_@tCPnDzBxAlA`CjCzCoF~CaGnJkb@dBqJlF}LpMeVvOoZxNePra@al@rFqGpLuJlGxMdEbI',
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

    r = match_with_osrm(points_by_key)
    assert isinstance(r, dict)
    assert len(r) == len(points_by_key)

@responses.activate
def test_match_with_mapbox():
    # Create mock response
    url = 'https://api.mapbox.com/matching/v5/mapbox/driving'
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
            'geometry': 'jlasmAybgllIo@o@qGeHwAOwCSsA@iARoAdA_AtAiB~DbClDjHbLpCpChQxQht@vg@hInBnOfHtMdIzp@hm@vY|Pdj@fRbUzG~O|EhMnBjJnEjrA|aAtEbE^m@f@_@j@Mn@@j@Rb@b@^v@NbA?fAS`Aa@t@tVfg@rNzVlM~OpZxWbKbHhLlEzMhCtMl@z@Df]p@fg@VtaD~Af\\LdDB|c@Pvc@p@zIr@nItAlGfBnKzDrP~G`PxIpHdE~KrStFlLfHbPlLzUvIrPrNnY~IrNhHhKzGfItBbBhDfClQxLvHvIxEzFhEvMlGxRjN`f@vA`HpCdGxFzGtDtBhQjJvW}}@f@_BXmA`@oAtGkVtDiVjA_GpBgB|D_@xBp@zEzDfDjD~Yd[zIlCnJ\\lReDnI_@tCPnDzBxAlA`CjCzCoF~CaGnJkb@dBqJlF}LpMeVvOoZxNePra@al@rFqGpLuJlGxMdEbI',
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

    r = match_with_mapbox(points_by_key, 'api_key')
    assert isinstance(r, dict)
    assert len(r) == len(points_by_key)

@responses.activate
def test_match_with_google():
    # Create mock response
    url = 'https://roads.googleapis.com/v1/snapToRoads'
    json = {
        'warningMessage': "Input path is too sparse. You should provide a path where consecutive points are closer to each other. Refer to the 'path' parameter in Google Roads API documentation.",
        'snappedPoints': [{
            'location': {
                'longitude': 174.80501397147776,
                'latitude': -41.22335545870424
            },
            'originalIndex': 0,
            'placeId': 'ChIJ8dqN_LetOG0RzRAx6EPYfqQ'
        }, {
            'location': {
                'longitude': 174.7967170172291,
                'latitude': -41.246993559684476
            },
            'originalIndex': 1,
            'placeId': 'ChIJTcHE8XSuOG0RQLWtBmHvABM'
        }]
    }
    responses.add(responses.GET, url, status=200, json=json)

    r = match_with_google(points_by_key, 'api_key')
    assert isinstance(r, dict)
    assert len(r) == len(points_by_key)
