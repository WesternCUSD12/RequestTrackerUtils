import pytest

from request_tracker_utils import create_app


@pytest.fixture
def app_with_temp_workdir(tmp_path, monkeypatch):
    # Create a temporary working directory and ensure the app uses it
    workdir = tmp_path / "workdir"
    workdir.mkdir()

    app = create_app()
    # Override working dir in config
    app.config["WORKING_DIR"] = str(workdir)

    # Enable testing mode so auth hooks are skipped in tests
    app.testing = True

    # Monkeypatch RT API calls so tests don't rely on external services
    # Monkeypatch RT API calls so tests don't rely on external services
    try:
        import request_tracker_utils.utils.rt_api as rt_api

        def fake_fetch(asset_id, config):
            return {"Name": "OldName"}

        def fake_request(method, path, data=None, config=None):
            return {"status": "ok"}

        monkeypatch.setattr(rt_api, "fetch_asset_data", fake_fetch)
        monkeypatch.setattr(rt_api, "rt_api_request", fake_request)
    except Exception:
        # If the module can't be imported, allow tests to run without RT calls
        pass

    return app


@pytest.fixture
def app(app_with_temp_workdir):
    """Compatibility shim for pytest-flask: provide an `app` fixture."""
    return app_with_temp_workdir


def test_next_and_reset_asset_tag(client, app_with_temp_workdir):
    app = app_with_temp_workdir
    client = app.test_client()

    # GET next tag initially
    resp = client.get("/next-asset-tag")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "next_asset_tag" in data

    # Reset sequence to 100
    reset_resp = client.post("/reset-asset-tag", json={"start_number": 100})
    assert reset_resp.status_code == 200
    reset_data = reset_resp.get_json()
    assert reset_data.get("new_start_tag")

    # Confirm next-asset-tag now reflects the reset
    resp2 = client.get("/next-asset-tag")
    assert resp2.status_code == 200
    assert resp2.get_json()["next_asset_tag"].endswith("00100")


def test_confirm_asset_tag(client, app_with_temp_workdir):
    app = app_with_temp_workdir
    client = app.test_client()

    # Ensure starting sequence is predictable
    client.post("/reset-asset-tag", json={"start_number": 0})

    next_resp = client.get("/next-asset-tag")
    next_tag = next_resp.get_json()["next_asset_tag"]

    # Confirm the asset tag
    confirm_resp = client.post(
        "/confirm-asset-tag",
        json={"asset_tag": next_tag, "request_tracker_id": "123"},
    )

    assert confirm_resp.status_code == 200
    content = confirm_resp.get_json()
    # We expect a success message or a success with a warning if RT update failed
    assert "message" in content
