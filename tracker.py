TRACKED_FIELDS = (
    "title", "description", "status_code", "canonical_url", "og_title",
    "robots_meta", "html_language", "content_type", "server_header",
    "body_sha256",
)


def compare_with_previous(current: dict, previous_snapshot: dict | None) -> dict:
    if previous_snapshot is None:
        return {"previous_exists": False, "changed": False, "differences": {}}
    previous = previous_snapshot["content"]
    differences = {
        field: {"before": previous.get(field), "after": current.get(field)}
        for field in TRACKED_FIELDS
        if previous.get(field) != current.get(field)
    }
    return {
        "previous_exists": True,
        "changed": bool(differences),
        "differences": differences,
        "tracked_fields": list(TRACKED_FIELDS),
    }
