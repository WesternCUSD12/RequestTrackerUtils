from request_tracker_utils.routes.tag_routes import AssetTagManager


def test_asset_tag_manager_sequence_file_lifecycle(tmp_path):
    # Use a temporary working directory to avoid touching real files
    working_dir = tmp_path / "workdir"
    working_dir.mkdir()

    # Build a minimal config that points to our temp working dir
    config = {"WORKING_DIR": str(working_dir), "PREFIX": "TEST-"}

    mgr = AssetTagManager(config)

    # Initially the sequence file should be created and set to 0
    seq = mgr.get_current_sequence()
    assert isinstance(seq, int)
    assert seq == 0

    # Next tag should match the prefix and zero-padded digits
    next_tag = mgr.get_next_tag()
    assert next_tag.startswith("TEST-")
    assert next_tag.endswith("00000")

    # Increment and ensure sequence increases
    new_seq = mgr.increment_sequence()
    assert new_seq == 1
    assert mgr.get_current_sequence() == 1

    # Reset sequence to a larger number and verify formatting expands digits
    mgr.set_sequence(99999)
    assert mgr.get_current_sequence() == 99999
    tag_before = mgr.get_next_tag()
    assert tag_before.endswith("99999")

    # Increment to force digit expansion (100000 -> 6 digits)
    mgr.increment_sequence()
    tag_after = mgr.get_next_tag()
    assert tag_after.endswith("100000")

    # Log a confirmation and ensure log file contains the entry
    mgr.log_confirmation(tag_after, "RT123")
    entries = mgr.get_log_entries(limit=10)
    assert any(e["asset_tag"] == tag_after for e in entries)

