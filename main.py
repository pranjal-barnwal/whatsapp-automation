"""Command-line entry point for the WhatsApp client-message automation.

Examples
--------
Preview messages without opening a browser (safe, no sending)::

    python main.py --dry-run

Send to only the first 2 clients (good for a live test to yourself)::

    python main.py --limit 2

Full run, skipping anyone already messaged in a previous run::

    python main.py --resume
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src import config
from src.data_loader import load_clients
from src.message_builder import (
    build_wa_me_url,
    find_unresolved_placeholders,
    load_template,
    render_message,
)
from src import report as report_mod
from src.report import Report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send personalized WhatsApp messages to clients from an Excel sheet.",
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=config.DATA_FILE,
        help=f"Path to the Excel file (default: {config.DATA_FILE}).",
    )
    parser.add_argument(
        "--template",
        type=Path,
        default=config.TEMPLATE_FILE,
        help=f"Path to the message template (default: {config.TEMPLATE_FILE}).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview rendered messages and links without opening a browser.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Only process the first N valid clients (0 = no limit).",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip numbers already marked 'sent' in previous run reports.",
    )
    parser.add_argument(
        "--min-delay",
        type=float,
        default=config.MIN_DELAY_SECONDS,
        help="Minimum seconds to wait between messages.",
    )
    parser.add_argument(
        "--max-delay",
        type=float,
        default=config.MAX_DELAY_SECONDS,
        help="Maximum seconds to wait between messages.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the confirmation prompt before sending.",
    )
    return parser.parse_args(argv)


def _preview(name: str, phone: str, message: str) -> None:
    print("-" * 60)
    print(f"To : {name} ({phone})")
    unresolved = find_unresolved_placeholders(message)
    if unresolved:
        print(f"WARNING: unresolved placeholders: {', '.join(unresolved)}")
    print("Message:")
    print(message)
    print(f"Link: {build_wa_me_url(phone, message)}")


def run(args: argparse.Namespace) -> int:
    # --- Load inputs ---------------------------------------------------------
    try:
        template = load_template(args.template)
        clients, skipped = load_clients(args.data)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    if skipped:
        print(f"Skipping {len(skipped)} row(s) that could not be used:")
        for row in skipped:
            print(f"  - row {row.row}: {row.name or '(no name)'} "
                  f"[{row.raw_phone or 'no phone'}] -> {row.reason}")

    # --- Resume filter -------------------------------------------------------
    already_sent: set[str] = set()
    if args.resume:
        already_sent = report_mod.load_already_sent()
        before = len(clients)
        clients = [c for c in clients if c.phone not in already_sent]
        resumed = before - len(clients)
        if resumed:
            print(f"Resume: skipping {resumed} already-sent number(s).")

    if args.limit and args.limit > 0:
        clients = clients[: args.limit]

    if not clients:
        print("No valid clients to message. Nothing to do.")
        return 0

    print(f"\n{len(clients)} message(s) ready to send.")

    # --- Dry run -------------------------------------------------------------
    if args.dry_run:
        print("\n=== DRY RUN (no messages will be sent) ===")
        for client in clients:
            message = render_message(template, client.fields)
            _preview(client.name, client.phone, message)
        print("-" * 60)
        print("Dry run complete. Re-run without --dry-run to send.")
        return 0

    # --- Confirm before live send -------------------------------------------
    if not args.yes:
        answer = input(
            f"\nSend {len(clients)} WhatsApp message(s) now? [y/N]: "
        ).strip().lower()
        if answer not in {"y", "yes"}:
            print("Aborted. No messages sent.")
            return 0

    # --- Live send (import Selenium lazily so --dry-run needs no browser) -----
    try:
        from src.sender import (
            InvalidNumberError,
            SendError,
            WhatsAppSender,
            human_delay,
        )
    except ImportError as exc:
        print(
            "Error: Selenium/webdriver-manager not installed. "
            "Run: pip install -r requirements.txt\n"
            f"({exc})",
            file=sys.stderr,
        )
        return 2

    sent_count = 0
    with Report() as report:
        # Log skipped rows for a complete audit trail.
        for row in skipped:
            report.record(
                report_mod.STATUS_INVALID,
                name=row.name,
                phone=row.raw_phone,
                row=row.row,
                detail=row.reason,
            )

        try:
            with WhatsAppSender() as sender:
                total = len(clients)
                for index, client in enumerate(clients, start=1):
                    message = render_message(template, client.fields)
                    print(f"[{index}/{total}] {client.name} ({client.phone}) ... ",
                          end="", flush=True)
                    try:
                        sender.send(client.phone, message)
                    except InvalidNumberError as exc:
                        print("invalid number")
                        report.record(
                            report_mod.STATUS_INVALID,
                            name=client.name,
                            phone=client.phone,
                            row=client.row,
                            detail=str(exc),
                        )
                    except SendError as exc:
                        print(f"failed ({exc})")
                        report.record(
                            report_mod.STATUS_FAILED,
                            name=client.name,
                            phone=client.phone,
                            row=client.row,
                            detail=str(exc),
                        )
                    else:
                        print("sent")
                        sent_count += 1
                        report.record(
                            report_mod.STATUS_SENT,
                            name=client.name,
                            phone=client.phone,
                            row=client.row,
                        )

                    # Throttle between messages (not after the last one).
                    if index < total:
                        waited = human_delay(args.min_delay, args.max_delay)
                        print(f"    waiting {waited:.0f}s before next message...")
        except SendError as exc:
            print(f"\nFatal: {exc}", file=sys.stderr)
            print(f"Report saved to: {report.path}")
            return 1
        except KeyboardInterrupt:
            print("\nInterrupted by user. Partial progress saved.")

        print(f"\nDone. {sent_count}/{len(clients)} sent.")
        print(f"Summary: {report.summary()}")
        print(f"Report saved to: {report.path}")

    return 0


def main(argv: list[str] | None = None) -> int:
    return run(parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
