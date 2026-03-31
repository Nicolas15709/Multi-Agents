#!/usr/bin/env python3
"""CLI for processing queued notifications."""

import argparse
import sys
from .pathlib import Path

# Add runtime/python to path for imports when run directly
sys.path.insert(0, str(Path(__file__).resolve().parent))

from .config import RuntimeConfig
from .db import Database
from .notification_sender import NotificationDeliveryService, NotificationProcessor
from .repository import NotificationRepository


def main():
    parser = argparse.ArgumentParser(description="Process queued notifications")
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum number of notifications to process (default: 50)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Check what would be sent without actually sending",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    args = parser.parse_args()

    config = RuntimeConfig.from_env()
    db = Database(config.db_path)
    db.init()

    notification_repo = NotificationRepository(db)
    delivery_service = NotificationDeliveryService.from_env()
    processor = NotificationProcessor(delivery_service, notification_repo)

    if args.dry_run:
        pending = notification_repo.recent_notifications(limit=args.limit)
        pending = [n for n in pending if n["status"] == "queued"]

        results = {"pending_count": len(pending), "would_send": [], "would_skip": []}

        for notification in pending:
            channel = notification["channel"]
            if delivery_service.is_configured(channel):
                results["would_send"].append({
                    "id": notification["id"],
                    "channel": channel,
                    "kind": notification["kind"],
                    "summary": notification["summary"],
                })
            else:
                results["would_skip"].append({
                    "id": notification["id"],
                    "channel": channel,
                    "reason": f"{channel} not configured",
                })

        if args.json:
            import json
            print(json.dumps(results, indent=2))
        else:
            print(f"Would process {len(results['would_send'])} notifications, skip {len(results['would_skip'])}")
            for item in results["would_send"][:5]:
                print(f"  - [{item['channel']}] {item['summary']}")
            if len(results['would_skip']) > 0:
                print("  Skipped:")
                for item in results["would_skip"][:5]:
                    print(f"  - [{item['channel']}] {item['reason']}")
        db.close()
        return

    results = processor.process_pending(limit=args.limit)

    if args.json:
        import json
        print(json.dumps(results, indent=2))
    else:
        print(f"Processed: {results['sent']} sent, {results['failed']} failed, {results['skipped']} skipped")

    db.close()


if __name__ == "__main__":
    main()
