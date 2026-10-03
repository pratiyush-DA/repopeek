"""Unit tests for repository discovery, file classification, and hashing."""

from pathlib import Path
import pytest

from repopeek.discovery.classifier import FileType, classify_file, is_binary_file
from repopeek.discovery.crawler import discover_repository
from repopeek.discovery.hasher import compute_file_hashes, compute_hashes_from_bytes
from repopeek.discovery.ignore import IgnoreRuleSet

FIXTURE_REPO_PATH = Path(__file__).parent / "fixtures" / "sample_repo"


def test_hashing_calculation(tmp_path):
    """Verify SHA-256 and Git blob SHA calculation."""
    content = b"hello repopeek\n"
    test_file = tmp_path / "hello.txt"
    test_file.write_bytes(content)

    sha256, blob_sha = compute_file_hashes(test_file)
    assert len(sha256) == 64
    assert len(blob_sha) == 40

    # Ensure matches in-memory bytes hashing
    mem_sha256, mem_blob_sha = compute_hashes_from_bytes(content)
    assert sha256 == mem_sha256
    assert blob_sha == mem_blob_sha


def test_classifier():
    """Verify file classification for supported extensions and shebangs."""
    assert classify_file(Path("billing.py")) == FileType.PYTHON
    assert classify_file(Path("query.sql")) == FileType.SQL
    assert classify_file(Path("deploy.sh")) == FileType.SHELL
    assert classify_file(Path("config.json")) == FileType.JSON
    assert classify_file(Path("manifest.yaml")) == FileType.YAML
    assert classify_file(Path("styles.css")) == FileType.OTHER


def test_binary_detection(tmp_path):
    """Verify binary detection via null byte presence."""
    text_file = tmp_path / "text.py"
    text_file.write_text("print('hello')", encoding="utf-8")
    assert not is_binary_file(text_file)

    bin_file = tmp_path / "data.bin"
    bin_file.write_bytes(b"\x00\x01\x02\x03\xff")
    assert is_binary_file(bin_file)


def test_ignore_rules(tmp_path):
    """Verify default ignore rules and .repopeekignore glob matching."""
    rules = IgnoreRuleSet(tmp_path, custom_patterns=["*.log", "secret_*"])
    assert rules.is_dir_ignored(".git")
    assert rules.is_dir_ignored(".venv")
    assert rules.is_path_ignored(tmp_path / "app.log")
    assert rules.is_path_ignored(tmp_path / "secret_key.txt")
    assert not rules.is_path_ignored(tmp_path / "main.py")


def test_discover_repository_on_fixture():
    """Verify end-to-end repository discovery on fixture repository."""
    assert FIXTURE_REPO_PATH.exists()

    files = discover_repository(FIXTURE_REPO_PATH)
    assert len(files) > 0

    rel_paths = [f.rel_path for f in files]

    # Verify ignored directory was completely skipped
    assert not any("ignored_dir" in p for p in rel_paths)

    # Verify presence of expected files
    assert "src/billing/invoice.py" in rel_paths
    assert "src/billing/validators.py" in rel_paths
    assert "src/models/base.py" in rel_paths
    assert "src/scripts/broken_syntax.py" in rel_paths
    assert "db/queries.sql" in rel_paths
    assert "scripts/run_pipeline.sh" in rel_paths
    assert "config/app_config.json" in rel_paths
    assert "config/pipeline.yaml" in rel_paths

    # Verify classification
    file_map = {f.rel_path: f for f in files}
    assert file_map["src/billing/invoice.py"].file_type == FileType.PYTHON
    assert file_map["db/queries.sql"].file_type == FileType.SQL
    assert file_map["scripts/run_pipeline.sh"].file_type == FileType.SHELL
    assert file_map["config/app_config.json"].file_type == FileType.JSON
    assert file_map["config/pipeline.yaml"].file_type == FileType.YAML

    # Verify all files have valid hashes
    for f in files:
        assert len(f.sha256) == 64
        assert len(f.blob_sha) == 40
        assert f.size_bytes > 0
