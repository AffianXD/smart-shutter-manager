"""Run the repository's mechanical pre-commit checks for the current worktree."""

from __future__ import annotations

import argparse
import re
import shlex
import subprocess
import sys
from pathlib import Path

from scripts.check_version_changelog import (
    CHANGELOG_PATH,
    MANIFEST_PATH,
    _backfill_versions_from_subjects,
    _git_show,
    _manifest_version,
    requires_versioned_release,
    validate_backfill_changelog,
    validate_version_changelog,
)


ROOT = Path(__file__).resolve().parents[1]
CARD_PATH = "custom_components/smart_shutter/www/smart-shutter-card.js"
SUBJECT_PATTERN = re.compile(
    r"^(build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test)"
    r"(?:\([a-z0-9][a-z0-9._/-]*\))?!?: (.+)$"
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-ref", required=True)
    parser.add_argument("--default-branch-ref", required=True)
    parser.add_argument("--subject", required=True, help="proposed commit subject")
    parser.add_argument(
        "--backfill-version",
        help="validate an explicit historical release entry instead of a new bump",
    )
    return parser.parse_args()


def _git_output(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        check=True,
        cwd=ROOT,
        text=True,
    )
    return result.stdout


def _changed_paths(base_ref: str) -> set[str]:
    tracked = _git_output("diff", "--name-only", base_ref, "--").splitlines()
    untracked = _git_output("ls-files", "--others", "--exclude-standard").splitlines()
    return {path for path in tracked + untracked if path}


def _resolve_base(base_ref: str, default_branch_ref: str) -> str:
    return default_branch_ref if re.fullmatch(r"0+", base_ref) else base_ref


def _validate_subject(subject: str, backfill_version: str | None) -> list[str]:
    match = SUBJECT_PATTERN.fullmatch(subject)
    if match is None:
        return [
            "Commit subject must use Conventional Commits, for example "
            "feat(card): describe the user-visible change."
        ]

    summary = match.group(2)
    if subject != subject.strip() or "\n" in subject or "\r" in subject:
        return ["Commit subject must be a single trimmed line."]
    if len(summary) < 12:
        return ["Commit subject summary must describe the change in at least 12 characters."]
    if len(subject) > 72:
        return ["Commit subject must be 72 characters or fewer."]
    subject_backfills = _backfill_versions_from_subjects([subject])
    if subject_backfills and not backfill_version:
        return ["Pass --backfill-version when the subject explicitly marks a backfill."]
    if backfill_version and subject_backfills != {backfill_version}:
        return [
            "Backfill commit subject must use the explicit marker "
            f"'backfill v{backfill_version}'."
        ]
    return []


def _print_tail(output: str, limit: int = 8) -> None:
    lines = output.strip().splitlines()
    if len(lines) > limit:
        lines = ["... output truncated ...", *lines[-limit:]]
    for line in lines:
        print(f"  {line}")


def _run_check(label: str, command: list[str]) -> bool:
    print(f"RUN {label}: {shlex.join(command)}")
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            check=False,
            cwd=ROOT,
            text=True,
        )
    except FileNotFoundError as error:
        print(f"FAIL {label}: executable not found: {error.filename}")
        return False

    if result.returncode == 0:
        print(f"PASS {label}")
        if result.stdout.strip():
            _print_tail(result.stdout)
        return True

    print(f"FAIL {label} (exit {result.returncode})")
    if result.stdout.strip():
        _print_tail(result.stdout, limit=20)
    if result.stderr.strip():
        _print_tail(result.stderr, limit=20)
    return False


def _policy_violations(
    args: argparse.Namespace, base_ref: str, paths: set[str]
) -> list[str]:
    try:
        base_manifest = _git_show(base_ref, MANIFEST_PATH)
        base_changelog = _git_show(base_ref, CHANGELOG_PATH)
    except subprocess.CalledProcessError as error:
        return [
            f"Could not read {error.cmd[-1]!r} from base revision {base_ref!r}: "
            f"{error.stderr.strip()}"
        ]

    current_manifest = (ROOT / MANIFEST_PATH).read_text(encoding="utf-8")
    current_changelog = (ROOT / CHANGELOG_PATH).read_text(encoding="utf-8")
    try:
        if args.backfill_version:
            validate_backfill_changelog(
                version=args.backfill_version,
                base_manifest=base_manifest,
                head_manifest=current_manifest,
                base_changelog=base_changelog,
                head_changelog=current_changelog,
                changed_paths=paths,
            )
        else:
            validate_version_changelog(
                base_manifest,
                current_manifest,
                base_changelog,
                current_changelog,
            )
    except ValueError as error:
        return [str(error)]
    return []


def _untracked_whitespace_findings() -> list[str]:
    findings = []
    untracked = _git_output(
        "ls-files", "--others", "--exclude-standard"
    ).splitlines()
    for relative_path in untracked:
        path = ROOT / relative_path
        try:
            contents = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for line_number, line in enumerate(contents.splitlines(), start=1):
            if line.endswith((" ", "\t")):
                findings.append(f"{relative_path}:{line_number}: trailing whitespace")
    return findings


def main() -> int:
    args = _parse_args()
    base_ref = _resolve_base(args.base_ref, args.default_branch_ref)
    try:
        paths = _changed_paths(base_ref)
    except subprocess.CalledProcessError as error:
        print(
            f"Could not compare worktree against {base_ref!r}: {error.stderr.strip()}",
            file=sys.stderr,
        )
        return 2

    if not paths:
        print("No changed or untracked files found against the selected base.")
        return 1

    failures = []
    print(f"Base: {base_ref}")
    print(f"Changed paths: {len(paths)}")

    release_related = requires_versioned_release(paths)
    if release_related or args.backfill_version:
        policy_errors = _policy_violations(args, base_ref, paths)
        if policy_errors:
            failures.extend(policy_errors)
            for error in policy_errors:
                print(f"FAIL version/changelog: {error}")
        else:
            mode = f"backfill v{args.backfill_version}" if args.backfill_version else "new version"
            print(f"PASS version/changelog: {mode}")
    else:
        print("SKIP version/changelog: no integration or release-documentation files changed.")

    subject_errors = _validate_subject(args.subject, args.backfill_version)
    if subject_errors:
        failures.extend(subject_errors)
        for error in subject_errors:
            print(f"FAIL commit subject: {error}")
    else:
        print(f"PASS commit subject: {args.subject}")

    whitespace_ok = _run_check(
        "tracked whitespace", ["git", "diff", "--check", base_ref, "--"]
    )
    untracked_whitespace = _untracked_whitespace_findings()
    if untracked_whitespace:
        print("FAIL untracked whitespace")
        for finding in untracked_whitespace:
            print(f"  {finding}")
        whitespace_ok = False
    else:
        print("PASS untracked whitespace")
    if not whitespace_ok:
        failures.append("Whitespace check failed.")

    python_changed = any(path.endswith(".py") for path in paths)
    integration_python_changed = any(
        path.startswith("custom_components/smart_shutter/") and path.endswith(".py")
        for path in paths
    )
    card_changed = any(
        path == CARD_PATH
        or path.startswith("tests/") and path.endswith(".js")
        or path in {"package.json", "package-lock.json"}
        for path in paths
    )

    if python_changed:
        if not _run_check("Python tests", [sys.executable, "-m", "pytest", "-q"]):
            failures.append("Python tests failed.")
    else:
        print("SKIP Python tests: no Python files changed.")

    if integration_python_changed:
        commands = [
            (
                "integration AST check",
                [sys.executable, "ast_walker.py", "custom_components/smart_shutter"],
            ),
            (
                "integration compile check",
                [
                    sys.executable,
                    "-m",
                    "compileall",
                    "-q",
                    "custom_components/smart_shutter",
                ],
            ),
        ]
        for label, command in commands:
            if not _run_check(label, command):
                failures.append(f"{label} failed.")
    else:
        print("SKIP integration AST/compile checks: no integration Python files changed.")

    if card_changed:
        card_commands = [
            (
                "card method-reference check",
                [sys.executable, "method_ref_checker.py", CARD_PATH],
            ),
            ("card syntax check", ["npm", "run", "check:card"]),
            ("card interaction tests", ["npm", "run", "test:card"]),
        ]
        for label, command in card_commands:
            if not _run_check(label, command):
                failures.append(f"{label} failed.")
    else:
        print("SKIP card checks: no card, JavaScript test, or npm manifest changed.")

    if release_related and not args.backfill_version:
        manifest = (ROOT / MANIFEST_PATH).read_text(encoding="utf-8")
        version = _manifest_version(manifest, "Current")
        if version and not _run_check(
            "release tag/version check",
            [sys.executable, "scripts/check_release_tag.py", f"v{version}"],
        ):
            failures.append("Release tag/version check failed.")

    if failures:
        print(f"PRE-COMMIT GATE FAILED: {len(failures)} issue(s).")
        return 1
    print("PRE-COMMIT GATE PASSED. Codex should now report its semantic review.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
