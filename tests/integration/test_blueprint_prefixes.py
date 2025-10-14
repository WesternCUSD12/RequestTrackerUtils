from request_tracker_utils import create_app


def test_blueprint_prefixes_and_tag_endpoints():
    """Ensure blueprints are registered with expected prefixes and tag endpoints exist.

    This test inspects the app.url_map entries and checks that key routes are present
    and prefixed as documented. It is intentionally lightweight and only checks route
    existence (not behavior).
    """
    app = create_app()
    # Collect all rule strings
    rules = sorted({rule.rule for rule in app.url_map.iter_rules()})

    # Expected presence checks
    expected_routes = [
        '/labels/print',
        '/labels/batch',
        '/devices',  # device blueprint base
        '/students',
        '/assets',
        '/next-asset-tag',
        '/confirm-asset-tag',
        '/reset-asset-tag',
    ]

    missing = [r for r in expected_routes if not any(rule.startswith(r) for rule in rules)]

    assert not missing, f"Missing expected routes or prefixes: {missing}\nFound rules: {rules[:40]}"
