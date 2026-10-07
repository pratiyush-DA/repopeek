"""Tests for Repopeek configuration and CLI entry point."""

from pathlib import Path
import pytest
from repopeek.config import RepopeekConfig
from repopeek.cli import build_parser, main


def test_default_config():
    """Verify default configuration attributes."""
    cfg = RepopeekConfig()
    assert cfg.repo_path == Path(".")
    assert ".py" in cfg.supported_extensions
    assert ".sql" in cfg.supported_extensions
    assert ".json" in cfg.supported_extensions
    assert ".ts" in cfg.supported_extensions
    assert ".tsx" in cfg.supported_extensions
    assert cfg.sql_dialect == "oracle"
    assert cfg.graph_output_path == Path("output/graph.json")


def test_config_serialization(tmp_path: Path):
    """Verify JSON export and import for RepopeekConfig."""
    cfg = RepopeekConfig(
        repo_path=tmp_path,
        output_dir=tmp_path / "artifacts",
        sql_dialect="oracle",
        max_file_size_kb=512,
    )
    target_json = tmp_path / "repopeek.json"
    cfg.to_json_file(target_json)

    loaded = RepopeekConfig.from_json_file(target_json)
    assert loaded.repo_path == tmp_path
    assert loaded.output_dir == tmp_path / "artifacts"
    assert loaded.sql_dialect == "oracle"
    assert loaded.max_file_size_kb == 512


def test_cli_parser_defaults():
    """Verify CLI argument parser default values."""
    parser = build_parser()
    args = parser.parse_args([])
    assert args.repo_path == Path(".")
    assert args.output_dir == Path("./output")
    assert args.sql_dialect == "oracle"
    assert args.check is False


def test_cli_main_check_flag():
    """Verify main entry point with --check flag returns exit code 0."""
    exit_code = main(["--check"])
    assert exit_code == 0


def test_cli_main_scan_repo():
    """Verify main entry point scans target fixture repository."""
    fixture_path = Path(__file__).parent / "fixtures" / "sample_repo"
    exit_code = main(["--repo-path", str(fixture_path)])
    assert exit_code == 0

