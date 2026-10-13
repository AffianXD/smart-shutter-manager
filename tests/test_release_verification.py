"""Test GitHub Release verification without network access."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

from scripts.verify_release import VerificationError, verify_release


REPOSITORY = "example/smart-shutter"
TAG = "v1.2.3"
EXPECTED_NOTES = "## v1.2.3\n\n### Fixed\n- Correct the shutter option default.\n"


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, capture_output=True, check=True, text=True)


@pytest.fixture
def tagged_release(tmp_path: Path) -> Path:
    root = tmp_path
    _git(root, "init", "-q")
    manifest = root / "custom_components/smart_shutter/manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"domain": "smart_shutter", "version": "1.2.3"}))
    (root / "CHANGELOG.md").write_text(
        "# Changelog\n\n## v1.2.3\n\n### Fixed\n- Correct the shutter option default.\n"
    )
    _git(root, "add", "custom_components/smart_shutter/manifest.json", "CHANGELOG.md")
    _git(root, "-c", "user.name=Release Tests", "-c", "user.email=release@example.invalid",
         "commit", "-m", "chore(release): prepare test release")
    _git(root, "tag", TAG)
    return root


def _response(payload: object = None, *, error: str = "", code: int = 0):
    output = json.dumps(payload) if payload is not None else ""
    return SimpleNamespace(returncode=code, stdout=output, stderr=error)


def _valid_payloads():
    return {
        f"repos/{REPOSITORY}/git/ref/tags/{TAG}": {
            "ref": f"refs/tags/{TAG}",
            "object": {"sha": "a" * 40, "type": "commit"},
        },
        f"repos/{REPOSITORY}/releases/tags/{TAG}": {
            "tag_name": TAG,
            "draft": False,
            "prerelease": False,
            "published_at": "2026-10-13T12:00:00Z",
            "body": EXPECTED_NOTES,
        },
    }


def _fake_runner(payloads, *, failures=None):
    failures = failures or {}
    calls = []

    def runner(command, **kwargs):
        endpoint = command[-1]
        calls.append(endpoint)
        configured = failures.get(endpoint, [])
        if configured:
            response = configured.pop(0)
            if isinstance(response, BaseException):
                raise response
            if response is not None:
                return response
        return _response(payloads[endpoint])

    return runner, calls


def test_verifies_remote_tag_manifest_release_flags_and_exact_notes(tagged_release: Path) -> None:
    payloads = _valid_payloads()
    runner, calls = _fake_runner(payloads)

    verify_release(TAG, root=tagged_release, repository=REPOSITORY, runner=runner)

    assert calls == list(payloads)


@pytest.mark.parametrize(
    ("endpoint_suffix", "error"),
    [
        ("releases/tags/", "HTTP 404: Not Found"),
        ("git/ref/tags/", "HTTP 429: API rate limit exceeded"),
        ("releases/tags/", "HTTP 503: Service Unavailable"),
    ],
)
def test_retries_temporary_github_api_errors(
    tagged_release: Path, endpoint_suffix: str, error: str
) -> None:
    payloads = _valid_payloads()
    failing_endpoint = next(endpoint for endpoint in payloads if endpoint_suffix in endpoint)
    failures = {failing_endpoint: [_response(error=error, code=1)]}
    runner, calls = _fake_runner(payloads, failures=failures)
    delays = []

    verify_release(
        TAG,
        root=tagged_release,
        repository=REPOSITORY,
        runner=runner,
        sleeper=delays.append,
    )

    assert delays == [2]
    assert calls.count(failing_endpoint) == 2


def test_permanent_api_authentication_error_fails_without_retry(tagged_release: Path) -> None:
    payloads = _valid_payloads()
    endpoint = f"repos/{REPOSITORY}/git/ref/tags/{TAG}"
    runner, calls = _fake_runner(
        payloads, failures={endpoint: [_response(error="HTTP 401: Bad credentials", code=1)]}
    )
    delays = []

    with pytest.raises(VerificationError, match="Bad credentials"):
        verify_release(
            TAG, root=tagged_release, repository=REPOSITORY,
            runner=runner, sleeper=delays.append,
        )

    assert calls == [endpoint]
    assert delays == []


def test_network_timeout_is_retried(tagged_release: Path) -> None:
    payloads = _valid_payloads()
    endpoint = f"repos/{REPOSITORY}/git/ref/tags/{TAG}"
    timeout = subprocess.TimeoutExpired(cmd=["gh", "api", endpoint], timeout=20)
    runner, calls = _fake_runner(payloads, failures={endpoint: [timeout]})
    delays = []

    verify_release(
        TAG,
        root=tagged_release,
        repository=REPOSITORY,
        runner=runner,
        sleeper=delays.append,
    )

    assert calls.count(endpoint) == 2
    assert delays == [2]


@pytest.mark.parametrize(
    ("endpoint", "payload", "message"),
    [
        (
            f"repos/{REPOSITORY}/git/ref/tags/{TAG}",
            {"ref": "refs/tags/v9.9.9", "object": {"sha": "a" * 40}},
            "reference does not match",
        ),
        (
            f"repos/{REPOSITORY}/git/ref/tags/{TAG}",
            {"ref": f"refs/tags/{TAG}", "object": {"type": "commit", "sha": "bad"}},
            "no object SHA",
        ),
        (
            f"repos/{REPOSITORY}/releases/tags/{TAG}",
            {
                "tag_name": "v9.9.9", "draft": False, "prerelease": False,
                "published_at": "2026-10-13T12:00:00Z", "body": EXPECTED_NOTES,
            },
            "does not match",
        ),
        (
            f"repos/{REPOSITORY}/releases/tags/{TAG}",
            {
                "tag_name": TAG, "draft": True, "prerelease": False,
                "published_at": "2026-10-13T12:00:00Z", "body": EXPECTED_NOTES,
            },
            "still a draft",
        ),
        (
            f"repos/{REPOSITORY}/releases/tags/{TAG}",
            {
                "tag_name": TAG, "draft": False, "prerelease": True,
                "published_at": "2026-10-13T12:00:00Z", "body": EXPECTED_NOTES,
            },
            "pre-release",
        ),
        (
            f"repos/{REPOSITORY}/releases/tags/{TAG}",
            {
                "tag_name": TAG, "draft": False, "prerelease": False,
                "published_at": "2026-10-13T12:00:00Z", "body": "Wrong notes",
            },
            "do not match",
        ),
        (
            f"repos/{REPOSITORY}/releases/tags/{TAG}",
            {
                "tag_name": TAG, "draft": False, "prerelease": False,
                "published_at": None, "body": EXPECTED_NOTES,
            },
            "no publication timestamp",
        ),
    ],
)
def test_rejects_inconsistent_release_data(
    tagged_release: Path, endpoint: str, payload: dict, message: str
) -> None:
    payloads = _valid_payloads()
    payloads[endpoint] = payload
    runner, _ = _fake_runner(payloads)

    with pytest.raises(VerificationError, match=message):
        verify_release(TAG, root=tagged_release, repository=REPOSITORY, runner=runner)


def test_api_invalid_json_fails_with_clear_error(tagged_release: Path) -> None:
    endpoint = f"repos/{REPOSITORY}/git/ref/tags/{TAG}"

    def runner(command, **kwargs):
        return SimpleNamespace(returncode=0, stdout="not-json", stderr="")

    with pytest.raises(VerificationError, match="invalid JSON"):
        verify_release(TAG, root=tagged_release, repository=REPOSITORY, runner=runner)


def test_retry_exhaustion_fails_after_bounded_attempts(tagged_release: Path) -> None:
    payloads = _valid_payloads()
    endpoint = f"repos/{REPOSITORY}/releases/tags/{TAG}"
    failures = {endpoint: [_response(error="HTTP 404: Not Found", code=1) for _ in range(5)]}
    runner, calls = _fake_runner(payloads, failures=failures)
    delays = []

    with pytest.raises(VerificationError, match="not verifiable after 5 attempts"):
        verify_release(
            TAG, root=tagged_release, repository=REPOSITORY,
            runner=runner, sleeper=delays.append,
        )

    assert len(calls) == 10
    assert delays == [2, 4, 8, 16]
