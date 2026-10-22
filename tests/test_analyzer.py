from analyzer import create_report


def test_report_is_versioned_and_has_limitations():
    profile = {"target": "https://example.com/", "collected_at": "2026-01-01T00:00:00+00:00", "status_code": 200, "title": "Example"}
    report = create_report(profile, {"previous_exists": False, "changed": False, "differences": {}}, "test case")
    assert report["schema_version"] == "1.1"
    assert report["case_name"] == "test case"
    assert report["limitations"]
    assert "identitas" in report["summary"]
