from tracker import compare_with_previous


def test_first_snapshot():
    result = compare_with_previous({"title": "A"}, None)
    assert result["previous_exists"] is False
    assert result["differences"] == {}


def test_detect_change():
    current = {"title": "B", "status_code": 200}
    previous = {"content": {"title": "A", "status_code": 200}}
    result = compare_with_previous(current, previous)
    assert result["changed"] is True
    assert result["differences"]["title"] == {"before": "A", "after": "B"}


def test_no_change():
    current = {"title": "A", "status_code": 200}
    previous = {"content": {"title": "A", "status_code": 200}}
    result = compare_with_previous(current, previous)
    assert result["changed"] is False
