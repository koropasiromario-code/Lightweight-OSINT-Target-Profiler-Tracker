from database import add_target, get_targets, remove_target, set_target_enabled


def test_targets_start_disabled_and_can_be_enabled(tmp_path, monkeypatch):
    import database
    monkeypatch.setattr(database, "IS_POSTGRES", False)
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "targets.db")
    database.initialize_database()
    database.add_target("https://example.com/", 24)
    targets = database.get_targets()
    assert len(targets) == 1
    assert targets[0]["enabled"] in (False, 0)
    database.set_target_enabled(targets[0]["id"], True)
    enabled = database.get_targets(enabled_only=True)
    assert len(enabled) == 1
    assert enabled[0]["target"] == "https://example.com/"
    database.remove_target(enabled[0]["id"])
    assert database.get_targets() == []


def test_rejects_unsupported_interval(tmp_path, monkeypatch):
    import pytest
    import database
    monkeypatch.setattr(database, "IS_POSTGRES", False)
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "interval.db")
    database.initialize_database()
    with pytest.raises(ValueError):
        database.add_target("https://example.com/", 5)
