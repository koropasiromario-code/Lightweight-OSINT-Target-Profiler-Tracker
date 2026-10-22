"""Run one scheduled monitoring pass over explicitly enabled targets.

Requires a persistent PostgreSQL DATABASE_URL in the scheduled runner. This script
never discovers new domains; it only processes targets stored and enabled by an operator.
"""
import logging
import os
import sys

from analyzer import create_report
from collector import CollectionError, TargetValidationError, collect_metadata
from database import get_snapshots, get_targets, initialize_database, save_snapshot
from tracker import compare_with_previous

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("scheduled_monitor")


def main() -> int:
    if not os.getenv("DATABASE_URL", "").strip():
        logger.error("DATABASE_URL is required for scheduled monitoring; ephemeral runner storage is not persistent.")
        return 2
    initialize_database()
    targets = get_targets(enabled_only=True)
    if not targets:
        logger.info("No enabled targets; nothing to do.")
        return 0

    failures = 0
    for item in targets:
        target = item["target"]
        try:
            profile = collect_metadata(target)
            previous = get_snapshots(profile["target"], limit=1)
            comparison = compare_with_previous(profile, previous[0] if previous else None)
            save_snapshot(profile["target"], profile)
            report = create_report(profile, comparison, "Scheduled daily monitoring")
            logger.info(
                "target=%s status=%s changed=%s fields_changed=%d report_schema=%s",
                profile["target"], profile.get("status_code"), comparison.get("changed"),
                len(comparison.get("differences", {})), report.get("schema_version"),
            )
        except (TargetValidationError, CollectionError) as exc:
            failures += 1
            logger.warning("target=%s failed=%s", target, str(exc))
        except Exception:
            failures += 1
            logger.exception("target=%s unexpected failure", target)
    logger.info("Monitoring pass complete: targets=%d failures=%d", len(targets), failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
