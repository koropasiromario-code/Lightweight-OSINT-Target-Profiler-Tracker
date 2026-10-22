from tracker import compare_with_previous


def test_first_snapshot_has_no_changes():
    result = compare_with_previous({"title": "A"}, None)
    assert result["previous_exists"] is False
    assert result["changed"] is False
    assert result["differences"] == {}


def test_detects_tracked_field_changes():
    previous = {"content": {"title": "Old", "status_code": 200, "body_sha256": "a"}}
    current = {"title": "New", "status_code": 200, "body_sha256": "b"}
    result = compare_with_previous(current, previous)
    assert result["previous_exists"] is True
    assert result["changed"] is True
    assert result["differences"]["title"] == {"before": "Old", "after": "New"}
    assert result["differences"]["body_sha256"] == {"before": "a", "after": "b"}


def test_untracked_fields_are_ignored():
    previous = {"content": {"title": "Same", "response_time_ms": 100}}
    current = {"title": "Same", "response_time_ms": 120}
    result = compare_with_previous(current, previous)
    assert result["changed"] is False
