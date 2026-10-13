"""Prepare a stable release version and a traceable changelog draft."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.check_release_tag import _version_tuple, validate_release_tag
from scripts.check_version_changelog import (
    CHANGELOG_PATH,
    MANIFEST_PATH,
    requires_versioned_release,
    validate_version_changelog,
)


CONVENTIONAL_HEADER = re.compile(
    r"^(?P<type>[a-z][a-z0-9-]*)(?:\([^)]+\))?(?P<breaking>!)?:\s*(?P<subject>.+)$"
)
BREAKING_FOOTER = re.compile(r"(?im)^BREAKING(?:-| )CHANGE:\s*(.+)$")
SOURCE_MARKER = re.compile(r"<!-- prepare-release:([0-9a-z-]{7,40}) -->", re.IGNORECASE)
VAGUE_SUBJECTS = {
    "change", "changes", "cleanup", "fix", "fixes", "improve", "improvements",
    "misc", "stuff", "update", "updates", "work", "wip",
}
VERSION_PATH = "custom_components/smart_shutter/manifest.json"
RELEASE_ONLY_PATHS = {VERSION_PATH, CHANGELOG_PATH}
CATEGORY_ORDER = (
    "Added",
    "Changed",
    "Fixed",
    "Removed",
    "Security",
    "Breaking Changes",
    "Review Required",
)
TYPE_CATEGORIES = {
    "feat": "Added",
    "fix": "Fixed",
    "perf": "Changed",
    "refactor": "Changed",
    "docs": "Changed",
    "build": "Changed",
    "ci": "Changed",
    "test": "Changed",
    "style": "Changed",
    "chore": "Changed",
    "remove": "Removed",
    "removed": "Removed",
    "security": "Security",
}


@dataclass(frozen=True)
class PreparationResult:
    version: str
    previous_tag: str
    bumped: bool
    reviewed_commits: int
    included_commits: int


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, check=False, text=True
    )
    if result.returncode:
        detail = result.stderr.strip() or "git command failed"
        raise ValueError(detail)
    return result.stdout


def _working_tree_paths(root: Path) -> set[str]:
    tracked = _git(root, "diff", "--name-only", "-z", "HEAD").split("\0")
    untracked = _git(root, "ls-files", "--others", "--exclude-standard", "-z").split("\0")
    return {path for path in (*tracked, *untracked) if path}


def _guard_release_files(root: Path) -> set[str]:
    changed_paths = _working_tree_paths(root)
    protected = changed_paths & {MANIFEST_PATH, CHANGELOG_PATH}
    if protected:
        raise ValueError(
            "Release preparation will not overwrite existing changes in "
            f"{', '.join(sorted(protected))}. Commit or stash those files first; "
            "no files were changed."
        )
    return {
        path for path in changed_paths if requires_versioned_release({path})
    }


def _read_manifest(root: Path) -> tuple[str, str]:
    path = root / MANIFEST_PATH
    try:
        contents = path.read_text(encoding="utf-8")
        manifest = json.loads(contents)
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Cannot read integration manifest: {error}") from error
    version = manifest.get("version") if isinstance(manifest, dict) else None
    if not isinstance(version, str) or _version_tuple(version) is None:
        raise ValueError("Integration manifest must contain a stable X.Y.Z version.")
    return contents, version


def _latest_stable_tag(root: Path) -> tuple[str, tuple[int, int, int], list[str]]:
    tags = _git(root, "tag", "--list", "v*").splitlines()
    stable_tags = [
        (tag, parsed)
        for tag in tags
        if tag.startswith("v") and (parsed := _version_tuple(tag[1:])) is not None
    ]
    if not stable_tags:
        raise ValueError(
            "No stable vX.Y.Z Git tag was found. Fetch the repository's release tags first."
        )
    tag, version = max(stable_tags, key=lambda item: item[1])
    return tag, version, tags


def _bump(version: str, part: str) -> str:
    parsed = _version_tuple(version)
    if parsed is None:
        raise ValueError("Current integration version must use stable X.Y.Z SemVer.")
    major, minor, patch = parsed
    if part == "major":
        return f"{major + 1}.0.0"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def _direct_bump(previous: tuple[int, int, int], current: tuple[int, int, int]) -> bool:
    major, minor, patch = previous
    return current in {
        (major, minor, patch + 1),
        (major, minor + 1, 0),
        (major + 1, 0, 0),
    }


def _commits_since(root: Path, tag: str) -> list[tuple[str, str, str, set[str]]]:
    raw = _git(
        root,
        "log",
        "--reverse",
        "--no-merges",
        "--format=%H%x1f%s%x1f%b%x00",
        f"{tag}..HEAD",
    )
    commits: list[tuple[str, str, str, set[str]]] = []
    for record in raw.split("\x00"):
        record = record.strip("\n")
        if not record:
            continue
        pieces = record.split("\x1f", 2)
        if len(pieces) != 3:
            raise ValueError("Could not parse Git commit metadata for the changelog draft.")
        sha, subject, body = pieces
        paths = set(
            _git(
                root,
                "diff-tree",
                "--no-commit-id",
                "--name-only",
                "-r",
                sha,
            ).splitlines()
        )
        commits.append((sha, subject.strip(), body.strip(), paths))
    return commits


def _is_clear_subject(subject: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", " ", subject.casefold()).strip()
    return len(normalized) >= 12 and normalized not in VAGUE_SUBJECTS


def _commit_entry(sha: str, subject: str, body: str) -> tuple[str, str]:
    match = CONVENTIONAL_HEADER.fullmatch(subject)
    marker = f"<!-- prepare-release:{sha[:12]} -->"
    if match is None or not _is_clear_subject(match.group("subject")):
        return "Review Required", f"- [Review required] {subject} (`{sha[:12]}`) {marker}"

    category = TYPE_CATEGORIES.get(match.group("type"))
    if category is None:
        return "Review Required", f"- [Review required] {subject} (`{sha[:12]}`) {marker}"

    breaking_detail = BREAKING_FOOTER.search(body)
    if match.group("breaking") or breaking_detail:
        category = "Breaking Changes"
    title = match.group("subject").strip()
    title = f"{title[:1].upper()}{title[1:]}" if title else title
    if breaking_detail:
        title = f"{title}: {breaking_detail.group(1).strip()}"
    return category, f"- {title} {marker}"


def _bullet_key(line: str) -> str:
    text = SOURCE_MARKER.sub("", line).strip()
    text = re.sub(r"^-\s*\[Review required\]\s*", "- ", text, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", text.lstrip("- ").strip()).casefold()


def _merge_category(lines: list[str], category: str, entries: list[str]) -> list[str]:
    if not entries:
        return lines
    heading = f"### {category}"
    positions = [index for index, line in enumerate(lines) if line.strip() == heading]
    if len(positions) > 1:
        raise ValueError(f"Changelog draft contains duplicate '{heading}' headings.")

    existing_hashes = {
        value.casefold()
        for line in lines
        for value in SOURCE_MARKER.findall(line)
    }
    existing_bullets = {
        _bullet_key(line)
        for line in lines
        if line.lstrip().startswith("- ")
    }
    additions = []
    for entry in entries:
        marker = SOURCE_MARKER.search(entry)
        if marker and marker.group(1).casefold() in existing_hashes:
            continue
        if _bullet_key(entry) in existing_bullets:
            continue
        additions.append(entry)
        existing_bullets.add(_bullet_key(entry))
        if marker:
            existing_hashes.add(marker.group(1).casefold())
    if not additions:
        return lines

    if positions:
        start = positions[0]
        end = next(
            (index for index in range(start + 1, len(lines)) if lines[index].startswith("### ")),
            len(lines),
        )
        while end > start + 1 and not lines[end - 1].strip():
            end -= 1
        return lines[:end] + [*additions, ""] + lines[end:]

    result = list(lines)
    while result and not result[-1].strip():
        result.pop()
    if result:
        result.append("")
    result.extend([heading, "", *additions])
    return result


def _validate_existing_draft(section: list[str], version: str) -> None:
    categories = [line.strip() for line in section if line.startswith("### ")]
    if len(categories) != len(set(categories)):
        raise ValueError(f"Draft v{version} contains duplicate changelog category headings.")

    source_ids = [
        marker.casefold()
        for line in section
        for marker in SOURCE_MARKER.findall(line)
    ]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError(f"Draft v{version} contains duplicate source commit markers.")

    bullet_keys = [
        _bullet_key(line)
        for line in section
        if line.lstrip().startswith("- ")
    ]
    if len(bullet_keys) != len(set(bullet_keys)):
        raise ValueError(f"Draft v{version} contains duplicate changelog entries.")


def _updated_changelog(
    changelog: str,
    version: str,
    commits: list[tuple[str, str, str, set[str]]],
    working_tree_paths: set[str] | None = None,
) -> tuple[str, int, int]:
    heading = f"## v{version}"
    lines = changelog.splitlines()
    positions = [index for index, line in enumerate(lines) if line.strip() == heading]
    if len(positions) > 1:
        raise ValueError(f"CHANGELOG.md already contains duplicate '{heading}' headings.")

    if positions:
        start = positions[0]
        all_headings = [
            index for index, line in enumerate(lines) if line.startswith("## ")
        ]
        if not all_headings or all_headings[0] != start:
            raise ValueError(f"Existing draft '{heading}' must be the top changelog section.")
        end = next(
            (index for index in range(start + 1, len(lines)) if lines[index].startswith("## ")),
            len(lines),
        )
        section = lines[start + 1 : end]
        suffix = lines[end:]
        prefix = lines[:start]
    else:
        end = next(
            (index for index, line in enumerate(lines) if line.startswith("## ")),
            len(lines),
        )
        prefix = lines[:end]
        section = []
        suffix = lines[end:]

    while section and not section[0].strip():
        section.pop(0)
    while section and not section[-1].strip():
        section.pop()

    _validate_existing_draft(section, version)

    grouped: dict[str, list[str]] = {category: [] for category in CATEGORY_ORDER}
    included = 0
    reviewed = 0
    for sha, subject, body, paths in commits:
        if paths and paths.issubset(RELEASE_ONLY_PATHS):
            continue
        category, entry = _commit_entry(sha, subject, body)
        grouped[category].append(entry)
        included += 1
        reviewed += category == "Review Required"

    if working_tree_paths:
        path_summary = ", ".join(f"`{path}`" for path in sorted(working_tree_paths))
        digest = hashlib.sha256("\0".join(sorted(working_tree_paths)).encode()).hexdigest()[:12]
        grouped["Review Required"].append(
            "- [Review required] Uncommitted release-relevant changes in "
            f"{path_summary}; summarize these changes manually. "
            f"<!-- prepare-release:worktree-{digest} -->"
        )
        included += 1
        reviewed += 1

    for category in CATEGORY_ORDER:
        section = _merge_category(section, category, grouped[category])

    if not any(line.lstrip().startswith("- ") for line in section):
        raise ValueError(
            f"No changelog entries were found since the last stable release. "
            "The version was not changed."
        )

    new_section = [heading, "", *section]
    updated = "\n".join([*prefix, *new_section, "", *suffix]).rstrip() + "\n"
    return updated, included, reviewed


def _replace_manifest_version(contents: str, version: str) -> str:
    pattern = re.compile(r'("version"\s*:\s*)"[^"]+"')
    updated, count = pattern.subn(lambda match: f'{match.group(1)}"{version}"', contents)
    if count != 1:
        raise ValueError("Integration manifest must contain exactly one version field.")
    json.loads(updated)
    return updated


def _atomic_write(path: Path, contents: str) -> None:
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as output:
            output.write(contents)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary_path, path)
    except OSError:
        temporary_path.unlink(missing_ok=True)
        raise


def prepare_release(part: str, *, root: Path = ROOT) -> PreparationResult:
    """Prepare or refresh the current unreleased draft without creating Git refs."""
    if part not in {"patch", "minor", "major"}:
        raise ValueError("Version increment must be patch, minor, or major.")
    working_tree_paths = _guard_release_files(root)

    manifest_contents, current_version = _read_manifest(root)
    current_tuple = _version_tuple(current_version)
    assert current_tuple is not None
    previous_tag, previous_tuple, all_tags = _latest_stable_tag(root)

    if current_tuple < previous_tuple:
        raise ValueError(
            f"Manifest version {current_version} is behind latest stable tag {previous_tag}."
        )
    if current_tuple == previous_tuple:
        target_version = _bump(current_version, part)
        bumped = True
    else:
        if not _direct_bump(previous_tuple, current_tuple):
            raise ValueError(
                f"Manifest version {current_version} is more than one SemVer step "
                f"ahead of {previous_tag}; resolve the existing version draft first."
            )
        target_version = current_version
        bumped = False

    validate_release_tag(f"v{target_version}", target_version, all_tags)
    manifest_updated = _replace_manifest_version(manifest_contents, target_version)
    changelog_path = root / CHANGELOG_PATH
    try:
        changelog_contents = changelog_path.read_text(encoding="utf-8")
        base_manifest = _git(root, "show", f"{previous_tag}:{MANIFEST_PATH}")
        base_changelog = _git(root, "show", f"{previous_tag}:{CHANGELOG_PATH}")
    except OSError as error:
        raise ValueError(f"Cannot read release files: {error}") from error

    commits = _commits_since(root, previous_tag)
    changelog_updated, included, reviewed = _updated_changelog(
        changelog_contents, target_version, commits, working_tree_paths
    )
    validate_version_changelog(
        base_manifest,
        manifest_updated,
        base_changelog,
        changelog_updated,
        allow_review_items=True,
    )

    manifest_path = root / MANIFEST_PATH
    _atomic_write(manifest_path, manifest_updated)
    try:
        _atomic_write(changelog_path, changelog_updated)
    except OSError:
        _atomic_write(manifest_path, manifest_contents)
        raise

    return PreparationResult(
        version=target_version,
        previous_tag=previous_tag,
        bumped=bumped,
        reviewed_commits=reviewed,
        included_commits=included,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("increment", choices=("patch", "minor", "major"))
    args = parser.parse_args()
    try:
        result = prepare_release(args.increment)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Release preparation failed: {error}", file=sys.stderr)
        return 1

    action = "bumped" if result.bumped else "kept the existing unreleased draft"
    print(
        f"Prepared v{result.version} ({action}) from changes since "
        f"{result.previous_tag}: {result.included_commits} commit(s) included."
    )
    print("Updated custom_components/smart_shutter/manifest.json and CHANGELOG.md.")
    if result.reviewed_commits:
        print(
            f"Manual review required for {result.reviewed_commits} item(s). "
            "Resolve the 'Review Required' entries before CI or publication."
        )
    else:
        print("Review the generated changelog before committing the release draft.")
    print("No Git tag, commit, push, or GitHub Release was created.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
