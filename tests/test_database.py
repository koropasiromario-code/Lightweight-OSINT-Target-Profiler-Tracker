import json


def test_sqlite_round_trip(tmp_path, monkeypatch):
    import database
    monkeypatch.setattr(database, "IS_POSTGRES", False)
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.db")
    database.initialize_database()
    profile = {"target": "https://example.com/", "collected_at": "2026-01-01T00:00:00+00:00", "title": "Example"}
    database.save_snapshot(profile["target"], profile)
    rows = database.get_snapshots(profile["target"])
    assert len(rows) == 1
    assert rows[0]["content"]["title"] == "Example"
