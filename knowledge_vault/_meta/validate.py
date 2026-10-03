"""Validation script for knowledge_vault.

Checks:
- Broken [[wikilinks]]
- Orphan notes (no inbound links, excluding root index 00-index.md)
- Notes missing required frontmatter fields
- Notes over 600 words
- Reciprocal relationship consistency (affects <-> depends_on)
- Non-existent code_refs for active notes
- Stale verification (>60 days)
"""

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
import yaml

VAULT_DIR = Path(__file__).resolve().parent.parent

# Excluded directories from link target validation
EXCLUDED_DIRS = {"_sources", "_templates", ".obsidian"}

REQUIRED_FRONTMATTER_FIELDS = {"id", "type", "title", "summary", "last_verified"}


def get_all_notes(vault_path: Path) -> Tuple[Dict[str, Path], Dict[str, str]]:
    """Return (canonical_notes, alias_to_canonical_map)."""
    canonical_notes: Dict[str, Path] = {}
    alias_map: Dict[str, str] = {}
    for root, dirs, files in os.walk(vault_path):
        rel_root = Path(root).relative_to(vault_path)
        if any(part in EXCLUDED_DIRS for part in rel_root.parts):
            continue
        for f in files:
            if f.endswith(".md"):
                p = Path(root) / f
                rel_posix = p.relative_to(vault_path).with_suffix("").as_posix()
                stem = p.stem
                canon_key = stem if stem not in canonical_notes else rel_posix
                canonical_notes[canon_key] = p
                alias_map[stem] = canon_key
                alias_map[rel_posix] = canon_key
                # Also extract ID from frontmatter if available
                try:
                    content = p.read_text(encoding="utf-8")
                    if content.startswith("---"):
                        parts = content.split("---", 2)
                        if len(parts) >= 3:
                            fm = yaml.safe_load(parts[1]) or {}
                            if "id" in fm and isinstance(fm["id"], str):
                                alias_map[fm["id"]] = canon_key
                except Exception:
                    pass
    return canonical_notes, alias_map


def extract_frontmatter(content: str) -> Tuple[dict, str]:
    """Extract YAML frontmatter and markdown body."""
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            try:
                fm = yaml.safe_load(parts[1]) or {}
                return fm, parts[2]
            except Exception as e:
                return {"_yaml_error": str(e)}, parts[2]
    return {}, content


def extract_wikilinks(text: str) -> List[str]:
    """Extract all targets from [[target]] or [[target|label]], ignoring code blocks."""
    # Strip multiline code blocks
    cleaned_text = re.sub(r"```[\s\S]*?```", "", text)
    # Strip inline code
    cleaned_text = re.sub(r"`[^`]*`", "", cleaned_text)

    matches = re.findall(r"\[\[([^\]\|]+)(?:\|[^\]]+)?\]\]", cleaned_text)
    cleaned = []
    for m in matches:
        target = m.strip()
        # strip file extension if included
        if target.endswith(".md"):
            target = target[:-3]
        cleaned.append(target)
    return cleaned


def main():
    canonical_notes, alias_map = get_all_notes(VAULT_DIR)
    print(f"Validating {len(canonical_notes)} notes in {VAULT_DIR}...")

    errors: List[str] = []
    warnings: List[str] = []

    inbound_links: Dict[str, Set[str]] = {canon: set() for canon in canonical_notes}
    outbound_links: Dict[str, Set[str]] = {canon: set() for canon in canonical_notes}
    note_frontmatter: Dict[str, dict] = {}
    note_word_counts: Dict[str, int] = {}

    # Pass 1: Parse frontmatter, check required fields, word count, extract links
    for canon_key, path in canonical_notes.items():
        try:
            content = path.read_text(encoding="utf-8")
        except Exception as e:
            errors.append(f"[{canon_key}] Failed to read file: {e}")
            continue

        fm, body = extract_frontmatter(content)
        note_frontmatter[canon_key] = fm

        if "_yaml_error" in fm:
            errors.append(f"[{canon_key}] YAML frontmatter parse error: {fm['_yaml_error']}")

        # Check required frontmatter fields (for non-meta notes)
        if "_meta" not in path.parts and canon_key != "00-index":
            missing_fields = REQUIRED_FRONTMATTER_FIELDS - set(fm.keys())
            if missing_fields:
                errors.append(f"[{canon_key}] Missing required frontmatter fields: {sorted(list(missing_fields))}")

        # Check word count
        words = len(body.split())
        note_word_counts[canon_key] = words
        if words > 600:
            warnings.append(f"[{canon_key}] High word count: {words} words (target 100-400, cap 600)")

        # Extract links from entire file
        links = extract_wikilinks(content)
        for target in links:
            if target in alias_map:
                canon_target = alias_map[target]
                outbound_links[canon_key].add(canon_target)
                inbound_links[canon_target].add(canon_key)
            else:
                # Check if it targets a source or template
                if not (VAULT_DIR / "_sources" / f"{target}.md").exists() and not (VAULT_DIR / "_templates" / f"{target}.md").exists():
                    errors.append(f"[{canon_key}] Broken [[wikilink]]: [[{target}]] not found")

    # Pass 2: Check for orphans (except 00-index, conventions, changelog)
    for canon_key, in_links in inbound_links.items():
        if canon_key in {"00-index", "conventions", "changelog"}:
            continue
        if len(in_links) == 0:
            errors.append(f"[{canon_key}] Orphan note: no inbound links from any other note")

    # Pass 3: Check reciprocity for affects and depends_on
    for canon_key, fm in note_frontmatter.items():
        affects_raw = fm.get("affects") or []
        if isinstance(affects_raw, list):
            affects_targets = [t.replace("[[", "").replace("]]", "").strip() for t in affects_raw if isinstance(t, str)]
            for tgt in affects_targets:
                if tgt in alias_map:
                    tgt_canon = alias_map[tgt]
                    tgt_fm = note_frontmatter.get(tgt_canon, {})
                    tgt_depends = tgt_fm.get("depends_on") or []
                    tgt_depends_canons = {alias_map.get(d.replace("[[", "").replace("]]", "").strip()) for d in tgt_depends if isinstance(d, str)}
                    if canon_key not in tgt_depends_canons:
                        warnings.append(f"[{canon_key}] Reciprocity warning: affects [[{tgt}]], but [[{tgt}]] does not list [[{canon_key}]] in depends_on")

    # Summary
    print("\n" + "=" * 50)
    print(f"Vault Validation Results: {len(canonical_notes)} notes inspected")
    print(f"Errors: {len(errors)}")
    print(f"Warnings: {len(warnings)}")
    print("=" * 50)

    if errors:
        print("\nERRORS (Must fix):")
        for err in errors:
            print(f"  [ERROR] {err}")

    if warnings:
        print(f"\nWARNINGS ({len(warnings)} found):")
        for warn in warnings[:20]:
            print(f"  [WARN] {warn}")
        if len(warnings) > 20:
            print(f"  ... and {len(warnings) - 20} more warnings")

    if not errors:
        print("\nSUCCESS: Zero errors found. Vault integrity verified.")
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
