from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .cli import _print_table
from .crawler import AuthorizedCrawler, CrawlConfig
from .storage import Repository


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Crawl an authorized, allowlisted product source and save HTML snapshots."
    )
    parser.add_argument(
        "--authorized",
        action="store_true",
        help="Explicitly confirm that this source may be crawled.",
    )
    parser.add_argument("--seed", action="append", default=[], help="HTML seed URL; repeatable.")
    parser.add_argument(
        "--sitemap", action="append", default=[], help="Sitemap URL; repeatable."
    )
    parser.add_argument(
        "--allowed-host",
        action="append",
        required=True,
        help="Exact allowlisted hostname; repeatable, e.g. www.example.com.",
    )
    parser.add_argument(
        "--url-pattern",
        help="Optional regex restricting discovered HTML URLs.",
    )
    parser.add_argument(
        "--snapshot-dir",
        type=Path,
        default=Path("data/pages"),
        help="Directory for immutable HTML snapshots (default: data/pages).",
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=Path("data/quince.sqlite3"),
        help="SQLite database path (default: data/quince.sqlite3).",
    )
    parser.add_argument("--max-pages", type=int, default=100)
    parser.add_argument("--max-depth", type=int, default=2)
    parser.add_argument("--delay-seconds", type=float, default=1.0)
    parser.add_argument("--timeout-seconds", type=float, default=20.0)
    parser.add_argument("--max-response-bytes", type=int, default=8_000_000)
    parser.add_argument(
        "--user-agent",
        default="QuinceLossLeaderResearch/0.1 (+authorized crawler)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.seed and not args.sitemap:
        print("Provide at least one --seed or --sitemap URL.", file=sys.stderr)
        return 2

    try:
        config = CrawlConfig(
            seed_urls=tuple(args.seed),
            sitemap_urls=tuple(args.sitemap),
            allowed_hosts=tuple(args.allowed_host),
            snapshot_dir=args.snapshot_dir,
            authorized=args.authorized,
            max_pages=args.max_pages,
            max_depth=args.max_depth,
            delay_seconds=args.delay_seconds,
            timeout_seconds=args.timeout_seconds,
            max_response_bytes=args.max_response_bytes,
            user_agent=args.user_agent,
            url_pattern=args.url_pattern,
        )
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2

    with Repository(args.database) as repository:
        result = AuthorizedCrawler(config, repository).run()
        losses = repository.loss_leaders()

    print(json.dumps({
        "attempted": result.attempted,
        "fetched": result.fetched,
        "snapshots_saved": result.snapshots_saved,
        "product_pages_saved": result.product_pages_saved,
        "observations_saved": result.observations_saved,
        "skipped": result.skipped,
        "blocked": result.blocked,
        "errors": result.errors,
    }, indent=2))
    print("\nLatest complete loss observations:")
    _print_table(losses)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

