"""Command-line interface and entry point for Repopeek."""

import argparse
import sys
from pathlib import Path

from repopeek import __version__
from repopeek.config import RepopeekConfig


def build_parser() -> argparse.ArgumentParser:
    """Build command line argument parser."""
    parser = argparse.ArgumentParser(
        prog="repopeek",
        description="Repopeek: Repository Intelligence and Semantic Code Property Graph Engine",
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--repo-path",
        type=Path,
        default=Path("."),
        help="Path to repository to inspect (default: current directory)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("./output"),
        help="Directory to save generated graph artifacts (default: ./output)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to optional JSON configuration file",
    )
    parser.add_argument(
        "--sql-dialect",
        type=str,
        default="oracle",
        help="Default SQL dialect for AST parser (default: oracle)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate environment and configuration without running pipeline",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Run enrichment in offline mode with deterministic stories (zero LLM calls)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Estimate token and cost requirements without invoking LLM APIs",
    )
    parser.add_argument(
        "--lookup",
        type=str,
        default=None,
        help="Lookup node card by symbol or ID",
    )
    parser.add_argument(
        "--impact",
        type=str,
        default=None,
        help="Compute upstream blast radius for a node",
    )
    parser.add_argument(
        "--trace",
        type=str,
        default=None,
        help="Trace def-use flow for a variable or table entity",
    )
    parser.add_argument(
        "--pack",
        type=str,
        nargs="+",
        default=None,
        help="Generate a minimal budget-governed context pack for targets",
    )
    parser.add_argument(
        "--serve-mcp",
        action="store_true",
        help="Run stdio JSON-RPC MCP server for autonomous coding agents",
    )
    return parser


def main(argv=None) -> int:
    """Main CLI entry point function."""
    parser = build_parser()
    args = parser.parse_args(argv)

    # Initialize configuration
    if args.config and args.config.exists():
        config = RepopeekConfig.from_json_file(args.config)
        # CLI overrides
        if args.repo_path != Path("."):
            config.repo_path = args.repo_path
        if args.output_dir != Path("./output"):
            config.output_dir = args.output_dir
    else:
        config = RepopeekConfig(
            repo_path=args.repo_path,
            output_dir=args.output_dir,
            sql_dialect=args.sql_dialect,
        )

    resolved_repo = config.repo_path.resolve()
    is_query_mode = bool(args.serve_mcp or args.lookup or args.impact or args.trace or args.pack)
    if not is_query_mode:
        print(f"Repopeek v{__version__} - Repository Intelligence Engine")
        print(f"Target repository: {resolved_repo}")
        print(f"Supported file extensions: {', '.join(config.supported_extensions)}")
        print(f"SQL dialect: {config.sql_dialect}")
        print(f"Graph destination: {config.graph_output_path.resolve()}")

    if not resolved_repo.exists():
        print(f"Error: Target repository path '{resolved_repo}' does not exist.", file=sys.stderr)
        return 1

    if args.check:
        print("Configuration check passed successfully.")
        return 0

    # Query dispatch handling
    if is_query_mode:
        import json
        from repopeek.query import GraphQueryEngine, RepoPeekMCPServer

        if args.output_dir != Path("./output") and (config.output_dir / "graph.json").exists():
            storage_dir = config.output_dir
        elif (resolved_repo / ".repopeek" / "graph.json").exists():
            storage_dir = resolved_repo / ".repopeek"
        elif (config.output_dir / "graph.json").exists():
            storage_dir = config.output_dir
        else:
            storage_dir = resolved_repo / ".repopeek"

        if (storage_dir / "graph.json").exists():
            engine = GraphQueryEngine(storage_dir=storage_dir)
        else:
            from repopeek.graph.builder import GraphBuilder
            graph = GraphBuilder().build_from_directory(resolved_repo)
            engine = GraphQueryEngine(graph=graph)

        if args.serve_mcp:
            server = RepoPeekMCPServer(engine)
            server.run_stdio()
            return 0

        if args.lookup:
            card = engine.lookup(args.lookup)
            if card:
                print(json.dumps(card.model_dump(exclude_none=True), indent=2))
                return 0
            print(f"Error: Node matching '{args.lookup}' not found.", file=sys.stderr)
            return 1

        if args.impact:
            res = engine.impact(args.impact)
            print(json.dumps(res, indent=2))
            return 0

        if args.trace:
            res = engine.data_trace(args.trace)
            print(json.dumps(res, indent=2))
            return 0

        if args.pack:
            pack = engine.context_pack(args.pack)
            print(pack.to_markdown())
            return 0

    from repopeek.discovery import discover_repository
    from repopeek.graph.builder import GraphBuilder
    from repopeek.storage import build_sqlite_cache, save_canonical_graph

    print("\nScanning repository...")
    discovered = discover_repository(resolved_repo, config)
    print(f"Discovered {len(discovered)} files.")

    counts = {}
    for f in discovered:
        counts[f.file_type.value] = counts.get(f.file_type.value, 0) + 1

    for ft, count in sorted(counts.items()):
        print(f"  - {ft}: {count}")

    print("\nBuilding canonical property graph...")
    builder = GraphBuilder()
    graph = builder.build_from_directory(resolved_repo)
    print(f"Graph assembled: {len(graph.nodes)} nodes, {len(graph.edges)} edges.")

    print("\nEnriching nodes with semantic stories (5-tier cascade)...")
    from repopeek.enrichment import StoryPipeline
    from repopeek.llm import get_llm_provider

    provider = get_llm_provider("fallback" if args.offline else None)
    pipeline = StoryPipeline(
        provider=provider,
        cache_dir=config.output_dir,
        dry_run=args.dry_run,
    )
    report = pipeline.enrich(graph)
    print(
        f"Enrichment completed: {report.stories_generated} stories "
        f"({report.cached_hits} cached, {report.deterministic_stories} deterministic, {report.llm_stories} LLM)."
    )

    print(f"\nPersisting artifacts to {config.output_dir.resolve()}...")
    manifest = save_canonical_graph(graph, config.output_dir, repo_root=resolved_repo)
    print(
        f"Deterministic JSON graph, {len(manifest.get('lenses', {}))} lenses, "
        f"and {len(manifest.get('shards', {}))} shards saved."
    )

    db_path = config.output_dir / "cache.db"
    build_sqlite_cache(graph, db_path)
    print(f"SQLite traversal cache created at {db_path}.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
