"""Verify a published GitHub Release against its tag, manifest, and changelog."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Callable, Sequence

from scripts.check_release_tag import validate_release_tag
from scripts.check_version_changelog import ROOT, MANIFEST_PATH, _version_tuple
from scripts.release_notes import release_notes


DEFAULT_ATTEMPTS = 5
RETRY_DELAYS_SECONDS = (2, 4, 8, 16)


class VerificationError(ValueError):
    """A permanent or exhausted release verification failure."""


class RetryableApiError(VerificationError):
    """A GitHub API response that can become available after a short delay."""


def _is_retryable_api_error(message: str) -> bool:
    text = message.casefold()
    retryable = (
        "http 404",
        "not found",
        "http 429",
        "rate limit",
        "http 500",
        "http 502",
        "http 503",
        "http 504",
        "timed out",
        "timeout",
        "connection reset",
        "connection refused",
        "network is unreachable",
        "temporary failure in name resolution",
        "could not resolve",
        "failed to connect",
    )
    return any(marker in text for marker in retryable)


def _api_json(
    endpoint: str,
    runner: Callable[..., subprocess.CompletedProcess[str]],
) -> dict:
    try:
        result = runner(
            ["gh", "api", endpoint],
            capture_output=True,
            check=False,
            text=True,
            timeout=20,
        )
    except subprocess.TimeoutExpired as error:
        raise RetryableApiError("GitHub API request timed out after 20 seconds.") from error
    except OSError as error:
        raise VerificationError(f"Could not run GitHub CLI: {error}") from error
    if result.returncode:
        detail = (result.stderr or result.stdout or "GitHub API request failed").strip()
        error_type = (
            RetryableApiError
            if _is_retryable_api_error(detail)
            else VerificationError
        )
        raise error_type(detail)
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise VerificationError(
            f"GitHub API returned invalid JSON for {endpoint}."
        ) from error
    if not isinstance(payload, dict):
        raise VerificationError(f"GitHub API returned invalid data for {endpoint}.")
    return payload


def _validate_manifest_tag(tag: str, version: str) -> None:
    try:
        # The remote Git reference is checked through the API below. The
        # publishing job can create that tag after its checkout was made.
        validate_release_tag(tag, version, [tag])
    except ValueError as error:
        raise VerificationError(str(error)) from error


def _read_manifest_version(root: Path) -> str:
    manifest_path = root / MANIFEST_PATH
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise VerificationError(f"Could not read integration manifest: {error}") from error
    version = manifest.get("version") if isinstance(manifest, dict) else None
    if not isinstance(version, str) or _version_tuple(version) is None:
        raise VerificationError("Integration manifest must contain a stable X.Y.Z version.")
    return version


def _normalized_notes(value: str) -> str:
    return value.replace("\r\n", "\n").strip()


def verify_release(
    tag: str,
    *,
    root: Path = ROOT,
    repository: str | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    sleeper: Callable[[float], None] | None = None,
    attempts: int = DEFAULT_ATTEMPTS,
) -> None:
    """Verify the published GitHub Release, retrying temporary API delays."""
    if not tag.startswith("v") or _version_tuple(tag[1:]) is None:
        raise VerificationError("Release tag must use stable vX.Y.Z format.")
    if attempts < 1:
        raise VerificationError("Verification attempts must be at least one.")

    repository = repository or os.environ.get("GITHUB_REPOSITORY")
    if not repository or "/" not in repository:
        raise VerificationError("GITHUB_REPOSITORY must identify owner/repository.")
    runner = runner or subprocess.run
    sleeper = sleeper or time.sleep

    version = _read_manifest_version(root)
    _validate_manifest_tag(tag, version)
    expected_notes = release_notes((root / "CHANGELOG.md").read_text(encoding="utf-8"), tag)
    tag_endpoint = f"repos/{repository}/git/ref/tags/{tag}"
    release_endpoint = f"repos/{repository}/releases/tags/{tag}"

    for attempt in range(attempts):
        try:
            ref = _api_json(tag_endpoint, runner)
            expected_ref = f"refs/tags/{tag}"
            tag_object = ref.get("object")
            if ref.get("ref") != expected_ref or not isinstance(tag_object, dict):
                raise VerificationError(f"GitHub tag reference does not match {expected_ref}.")
            sha = tag_object.get("sha")
            if (
                tag_object.get("type") not in {"commit", "tag"}
                or not isinstance(sha, str)
                or re.fullmatch(r"[0-9a-fA-F]{40,64}", sha) is None
            ):
                raise VerificationError(f"GitHub tag reference {expected_ref} has no object SHA.")

            release = _api_json(release_endpoint, runner)
            if release.get("tag_name") != tag:
                raise VerificationError(
                    f"GitHub Release tag {release.get('tag_name')!r} does not match {tag}."
                )
            if release.get("draft") is not False:
                raise VerificationError(
                    f"GitHub Release {tag} is still a draft or has invalid draft data."
                )
            if release.get("prerelease") is not False:
                raise VerificationError(f"GitHub Release {tag} is marked as a pre-release.")
            if not isinstance(release.get("published_at"), str) or not release[
                "published_at"
            ]:
                raise VerificationError(f"GitHub Release {tag} has no publication timestamp.")
            body = release.get("body")
            if (
                not isinstance(body, str)
                or _normalized_notes(body) != _normalized_notes(expected_notes)
            ):
                raise VerificationError(
                    f"GitHub Release notes for {tag} do not match the CHANGELOG.md section."
                )
            return
        except RetryableApiError as error:
            if attempt + 1 >= attempts:
                raise VerificationError(
                    f"GitHub publication was not verifiable after {attempts} attempts: {error}"
                ) from error
            sleeper(RETRY_DELAYS_SECONDS[min(attempt, len(RETRY_DELAYS_SECONDS) - 1)])


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag")
    parser.add_argument("--attempts", type=int, default=DEFAULT_ATTEMPTS)
    args = parser.parse_args(argv)
    try:
        verify_release(args.tag, attempts=args.attempts)
    except (OSError, VerificationError, ValueError) as error:
        print(f"GitHub Release verification failed: {error}", file=sys.stderr)
        return 1
    print(f"GitHub Release {args.tag} is published with the expected tag and release notes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
