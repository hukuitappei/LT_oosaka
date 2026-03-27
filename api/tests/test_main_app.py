from app.main import app as main_app
from app.dev_main import app as dev_app


def _route_paths(app):
    return {route.path for route in app.routes}


def test_main_app_does_not_mount_fixture_analyze_routes():
    paths = _route_paths(main_app)

    assert "/analyze/pr" not in paths
    assert "/analyze/fixtures" not in paths


def test_dev_app_mounts_fixture_analyze_routes():
    paths = _route_paths(dev_app)

    assert "/analyze/pr" in paths
    assert "/analyze/fixtures" in paths
