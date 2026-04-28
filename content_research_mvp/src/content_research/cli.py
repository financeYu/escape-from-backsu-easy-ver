"""Command line interface for content_research_mvp."""

from __future__ import annotations

import argparse
from pathlib import Path

from content_research.collection import HourlyCollectionProcess
from content_research.config import load_config
from content_research.pipeline.orchestrator import ContentResearchOrchestrator


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="content-research")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Create an MVP research bundle without external API calls.")
    run_parser.add_argument("--topic", required=True, help="Korean content research topic.")
    run_parser.add_argument("--config", default=None, help="Path to TOML config.")
    run_parser.add_argument("--output-dir", default=None, help="Output directory for Markdown and JSONL.")

    collect_once_parser = subparsers.add_parser(
        "collect-once",
        help="Run one hourly collection cycle and write a collection manifest.",
    )
    collect_once_parser.add_argument("--config", default=None, help="Path to TOML config.")
    collect_once_parser.add_argument("--output-dir", default=None, help="Output directory for collection manifests.")
    collect_once_parser.add_argument("--interval-minutes", type=int, default=None, help="Collection interval in minutes.")

    collect_daemon_parser = subparsers.add_parser(
        "collect-daemon",
        help="Run the hourly collection process continuously.",
    )
    collect_daemon_parser.add_argument("--config", default=None, help="Path to TOML config.")
    collect_daemon_parser.add_argument("--output-dir", default=None, help="Output directory for collection manifests.")
    collect_daemon_parser.add_argument("--interval-minutes", type=int, default=None, help="Collection interval in minutes.")
    collect_daemon_parser.add_argument(
        "--max-cycles",
        type=int,
        default=None,
        help="Optional limit for test runs. Omit for continuous collection.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "run":
        config = load_config(args.config)
        orchestrator = ContentResearchOrchestrator(config)
        bundle = orchestrator.run(args.topic)
        markdown_path, jsonl_path = orchestrator.write_outputs(bundle, Path(args.output_dir) if args.output_dir else None)
        print(f"wrote {markdown_path}")
        print(f"wrote {jsonl_path}")
        return 0
    if args.command == "collect-once":
        config = load_config(args.config)
        process = HourlyCollectionProcess(
            output_dir=Path(args.output_dir) if args.output_dir else config.collection.output_dir,
            interval_minutes=args.interval_minutes or config.collection.interval_minutes,
            timezone_name=config.collection.timezone,
        )
        manifest, jsonl_path, markdown_path = process.run_once()
        print(f"wrote {markdown_path}")
        print(f"wrote {jsonl_path}")
        print(f"next run {manifest.next_run_at}")
        return 0
    if args.command == "collect-daemon":
        config = load_config(args.config)
        process = HourlyCollectionProcess(
            output_dir=Path(args.output_dir) if args.output_dir else config.collection.output_dir,
            interval_minutes=args.interval_minutes or config.collection.interval_minutes,
            timezone_name=config.collection.timezone,
        )
        manifests = process.run_forever(max_cycles=args.max_cycles)
        if manifests:
            print(f"completed {len(manifests)} collection cycle(s)")
            print(f"last next run {manifests[-1].next_run_at}")
        return 0
    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
