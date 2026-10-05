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
    parser.add_argument(
        "--view",
        action="store_true",
        help="Launch interactive local web-based code property graph viewer in browser",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Port for the interactive graph viewer server (default: 8765)",
    )
    parser.add_argument(
        "--export-obsidian",
        type=str,
        nargs="?",
        const="default",
        default=None,
        help="Export canonical code graph into an Obsidian Markdown vault with [[wikilinks]] (pass 'default' or omit path to auto-detect system vault)",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Automatically open the exported vault in Obsidian Desktop via obsidian:// URI",
    )
    parser.add_argument(
        "--read-obsidian",
        type=str,
        default=None,
        help="Query symbol documentation from an exported Obsidian vault",
    )
    parser.add_argument(
        "--vault-path",
        type=Path,
        default=None,
        help="Path to the Obsidian vault directory for reading (default: ./obsidian_vault)",
    )
    parser.add_argument(
        "--snippet",
        action="store_true",
        help="Include source code snippet in lookup or context pack for zero-file-read edits",
    )
    parser.add_argument(
        "--update",
        type=Path,
        default=None,
        help="Incrementally update graph for a single modified file (<50ms)",
    )
    parser.add_argument(
        "--resolve",
        type=str,
        default=None,
        help="Resolve a natural language task to candidate symbols via hybrid retrieval (AST + BM25 + RRF)",
    )
    parser.add_argument(
        "--context",
        type=str,
        default=None,
        help="Compile task-driven context package with blast radius and constraints",
    )
    parser.add_argument(
        "--plan",
        type=str,
        default=None,
        help="Generate risk-assessed, step-by-step engineering change plan",
    )
    parser.add_argument(
        "--level",
        type=int,
        default=2,
        choices=[1, 2, 3],
        help="Progressive disclosure level for context package (1: brief, 2: standard, 3: full with snippets)",
    )
    parser.add_argument(
        "--budget",
        type=int,
        default=1500,
        help="Token budget for context compilation (default: 1500)",
    )
    parser.add_argument(
        "--co-changes",
        type=str,
        default=None,
        help="Query historical git co-change relationships and probabilities for a target file or symbol",
    )
    parser.add_argument(
        "--routes",
        action="store_true",
        help="Discover server HTTP endpoints, client calls, and cross-boundary linkages",
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
    is_query_mode = bool(
        args.serve_mcp
        or args.lookup
        or args.impact
        or args.trace
        or args.pack
        or args.view
        or args.export_obsidian
        or args.read_obsidian
        or args.update
        or args.resolve
        or args.context
        or args.plan
        or args.co_changes
        or args.routes
    )
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
            engine = GraphQueryEngine(storage_dir=storage_dir, repo_root=resolved_repo)
        else:
            from repopeek.graph.builder import GraphBuilder
            graph = GraphBuilder().build_from_directory(resolved_repo)
            engine = GraphQueryEngine(graph=graph, repo_root=resolved_repo)

        if args.read_obsidian:
            vault_dir = args.vault_path or Path("./obsidian_vault")
            from repopeek.storage import read_obsidian_node
            note = read_obsidian_node(vault_dir, args.read_obsidian)
            if note:
                print(json.dumps(note, indent=2))
                return 0
            print(f"Error: Node matching '{args.read_obsidian}' not found in Obsidian vault at '{vault_dir}'.", file=sys.stderr)
            return 1

        if args.export_obsidian:
            from repopeek.storage import (
                export_to_obsidian_vault,
                find_default_obsidian_vault,
                open_in_obsidian,
            )

            raw_target = args.export_obsidian
            if str(raw_target).lower() in ("default", "true", "none"):
                default_vault = find_default_obsidian_vault()
                if default_vault:
                    repo_folder = resolved_repo.resolve().name
                    target_vault_dir = default_vault / repo_folder
                    print(f"Auto-detected active Obsidian vault: {default_vault}")
                else:
                    print("Notice: No active Obsidian vault found on system. Exporting to ./obsidian_vault")
                    target_vault_dir = Path("./obsidian_vault")
            else:
                target_vault_dir = Path(raw_target)

            res = export_to_obsidian_vault(engine.graph, target_vault_dir)
            print(f"Obsidian vault successfully exported to: {res['vault_dir']}")
            print(f"Exported {res['exported_notes']} notes across categories: {', '.join(res['categories'])}")

            if args.open:
                print(f"Opening in Obsidian Desktop: {res['vault_dir']}")
                open_in_obsidian(Path(res["vault_dir"]))

            return 0

        if args.view:
            from repopeek.viewer import start_viewer
            server = start_viewer(engine, storage_dir=storage_dir, port=args.port, open_browser=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                print("\nShutting down RepoPeek Graph Viewer.")
                server.server_close()
            return 0

        if args.serve_mcp:
            server = RepoPeekMCPServer(engine)
            server.run_stdio()
            return 0

        if args.lookup:
            card = engine.lookup(args.lookup, include_snippet=args.snippet)
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
            pack = engine.context_pack(args.pack, include_snippet=args.snippet)
            print(pack.to_markdown())
            return 0

        if args.resolve:
            candidates = engine.resolve_task(args.resolve)
            print(json.dumps(candidates, indent=2))
            return 0

        if args.context:
            pkg = engine.compile_context(
                args.context,
                budget=args.budget,
                level=args.level,
                include_snippets=args.snippet,
            )
            print(pkg.to_markdown(level=args.level))
            return 0

        if args.plan:
            plan = engine.change_plan(args.plan)
            print(plan.to_markdown())
            return 0

        if args.co_changes:
            res = engine.co_changes(args.co_changes)
            print(json.dumps(res, indent=2))
            return 0

        if args.routes:
            res = engine.http_routes()
            print(json.dumps(res, indent=2))
            return 0

        if args.update:
            import time
            from repopeek.graph.builder import GraphBuilder
            from repopeek.storage import update_file_shard, update_sqlite_file

            target_file = args.update.resolve()
            if not target_file.exists():
                print(f"Error: Target file to update '{target_file}' does not exist.", file=sys.stderr)
                return 1

            start_t = time.perf_counter()
            builder = GraphBuilder()
            updated_graph = builder.update_file(target_file, engine.graph, repo_root=resolved_repo)

            # Update shard (which also syncs graph.json & manifest.json)
            rel_path = str(target_file.relative_to(resolved_repo)).replace("\\", "/")
            update_file_shard(storage_dir, rel_path, updated_graph)

            # Update sqlite cache if exists
            db_path = storage_dir / "cache.db"
            if db_path.exists():
                update_sqlite_file(rel_path, updated_graph, db_path)

            elapsed_ms = (time.perf_counter() - start_t) * 1000
            print(f"Updated graph for '{rel_path}' in {elapsed_ms:.1f}ms. Total nodes: {len(updated_graph.nodes)}, edges: {len(updated_graph.edges)}.")
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
