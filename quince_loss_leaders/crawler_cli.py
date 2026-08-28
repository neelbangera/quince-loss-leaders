from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import sys

from .cli import _print_table
from .crawler import AuthorizedCrawler, CrawlConfig, CrawlResult
from .storage import Repository


def _default_database_path() -> Path:
    return Path(os.environ.get("QUINCE_DATABASE") or "data/quince-us.sqlite3")


def _rankable_ratio(result: CrawlResult) -> float | None:
    if not result.product_urls_discovered:
        return None
    return result.rankable_observations / result.product_urls_discovered


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
        default=_default_database_path(),
        help="SQLite database path (default: QUINCE_DATABASE or data/quince-us.sqlite3).",
    )
    parser.add_argument("--max-pages", type=int, default=100)
    parser.add_argument("--max-depth", type=int, default=2)
    parser.add_argument(
        "--concurrency",
        type=int,
        default=4,
        help="Maximum number of overlapping page fetches (default: 4).",
    )
    parser.add_argument("--delay-seconds", type=float, default=1.0)
    parser.add_argument("--timeout-seconds", type=float, default=20.0)
    parser.add_argument("--max-response-bytes", type=int, default=8_000_000)
    parser.add_argument(
        "--min-rankable-observations",
        type=int,
        default=1,
        help="Fail unless this many complete, rankable observations are saved (default: 1).",
    )
    parser.add_argument(
        "--fail-on-truncation",
        action="store_true",
        help="Fail if max-pages leaves URLs waiting in the crawl queue.",
    )
    parser.add_argument(
        "--min-rankable-ratio",
        type=float,
        default=0.0,
        help=(
            "Fail unless rankable observations are at least this fraction of "
            "eligible sitemap URLs (0..1; default: 0)."
        ),
    )
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
    if args.min_rankable_observations < 0:
        print("--min-rankable-observations cannot be negative.", file=sys.stderr)
        return 2
    if (
        not math.isfinite(args.min_rankable_ratio)
        or not 0 <= args.min_rankable_ratio <= 1
    ):
        print(
            "--min-rankable-ratio must be a finite number between 0 and 1.",
            file=sys.stderr,
        )
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
            concurrency=args.concurrency,
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
        "sitemaps_fetched": result.sitemaps_fetched,
        "html_pages_fetched": result.html_pages_fetched,
        "urls_discovered": result.urls_discovered,
        "product_urls_discovered": result.product_urls_discovered,
        "snapshots_saved": result.snapshots_saved,
        "product_pages_saved": result.product_pages_saved,
        "observations_saved": result.observations_saved,
        "rankable_observations": result.rankable_observations,
        "rankable_ratio": _rankable_ratio(result),
        "parse_status_counts": result.parse_status_counts,
        "non_product_pages": result.non_product_pages,
        "skipped": result.skipped,
        "truncated": result.truncated,
        "blocked": result.blocked,
        "errors": result.errors,
    }, indent=2))
    print("\nLatest complete loss observations:")
    _print_table(losses)

    validation_errors: list[str] = []
    if result.rankable_observations < args.min_rankable_observations:
        validation_errors.append(
            "saved "
            f"{result.rankable_observations} rankable observations, "
            f"fewer than required {args.min_rankable_observations}"
        )
    if args.fail_on_truncation and result.truncated:
        validation_errors.append(
            f"crawl reached max-pages with {result.skipped} URLs still queued"
        )
    if args.min_rankable_ratio > 0:
        if not result.product_urls_discovered:
            validation_errors.append(
                "no eligible sitemap URLs were discovered, so rankable coverage "
                "cannot be checked"
            )
        else:
            rankable_ratio = _rankable_ratio(result)
            assert rankable_ratio is not None
            if rankable_ratio < args.min_rankable_ratio:
                validation_errors.append(
                    f"rankable coverage was {rankable_ratio:.1%}, "
                    f"below required {args.min_rankable_ratio:.1%}"
                )
    if validation_errors:
        print("Crawl validation failed: " + "; ".join(validation_errors), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
