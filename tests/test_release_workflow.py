"""Exercise the actual publication shell without Git metadata or network access."""

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
import yaml


WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/validate.yml"
REPOSITORY = "AffianXD/smart-shutter-manager"
TARGET = "2f0f5e8ba93ce01594229d284149d3fe3731a6c0"


@pytest.fixture
def publication(tmp_path):
    workflow = yaml.safe_load(WORKFLOW.read_text())
    step = next(step for step in workflow["jobs"]["publish-release"]["steps"]
                if step.get("name") == "Create GitHub release")
    (tmp_path / "python").symlink_to(sys.executable)
    cli = tmp_path / "gh"
    cli.write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        "args = sys.argv[1:]\n"
        "with open(os.environ['CALL_LOG'], 'a') as log:\n"
        "    log.write(json.dumps(args) + '\\n')\n"
        "if args[:2] in (['release', 'view'], ['release', 'create']):\n"
        "    if '--repo' not in args:\n"
        "        print('failed to run git: fatal: not a git repository', file=sys.stderr)\n"
        "        sys.exit(1)\n"
        "if args[0] == 'api':\n"
        "    print(os.environ['RELEASES'])\n"
        "    if os.environ['QUERY_ERROR']:\n"
        "        print(os.environ['QUERY_ERROR'], file=sys.stderr)\n"
        "        sys.exit(1)\n"
        "elif args[:2] == ['release', 'create']:\n"
        "    sys.exit(int(os.environ['CREATE_STATUS']))\n"
        "else:\n"
        "    sys.exit('Unexpected gh command')\n"
    )
    cli.chmod(0o755)

    def run(releases="", query_error="", create_status=0, release_tag="v0.29.0"):
        log = tmp_path / "calls.jsonl"
        env = {
            **os.environ,
            "PATH": f"{tmp_path}:{os.environ['PATH']}",
            "GITHUB_REPOSITORY": REPOSITORY,
            "RELEASE_TAG": release_tag,
            "RELEASE_TARGET": TARGET,
            "CALL_LOG": str(log),
            "RELEASES": releases,
            "QUERY_ERROR": query_error,
            "CREATE_STATUS": str(create_status),
            "GIT_CEILING_DIRECTORIES": str(tmp_path.parent),
            "PYTHONPATH": str(WORKFLOW.parents[2]),
            "RUNNER_TEMP": str(tmp_path),
        }
        result = subprocess.run(
            ["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", step["run"]],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
        )
        calls = [json.loads(line) for line in log.read_text().splitlines()]
        return result, calls

    return run


@pytest.mark.parametrize("releases", ["", "v0.28.2", "v0.29.00\nv0.28.2"])
def test_missing_release_created_in_explicit_repo_at_original_commit(publication, releases):
    result, calls = publication(releases)
    assert result.returncode == 0, result.stderr
    assert calls[0] == [
        "api", "--paginate", f"repos/{REPOSITORY}/releases", "--jq", ".[].tag_name",
    ]
    assert len(calls) == 2
    assert calls[1][:-1] == [
        "release", "create", "v0.29.0", "--repo", REPOSITORY,
        "--target", TARGET, "--title", "v0.29.0", "--notes-file",
    ]
    notes = Path(calls[1][-1]).read_text()
    assert notes.startswith("## v0.29.0\n")
    assert "Configure scheduled pre-close warnings per shutter" in notes
    assert "## v0.28.2" not in notes


def test_existing_release_on_later_page_left_unchanged(publication):
    result, calls = publication("v0.30.0\nv0.29.1\nv0.29.0\nv0.28.2")
    assert result.returncode == 0, result.stderr
    assert "already exists; leaving it unchanged" in result.stdout
    assert len(calls) == 1
    assert "--paginate" in calls[0]


@pytest.mark.parametrize("error", [
    "HTTP 401: Bad credentials", "HTTP 403: API rate limit exceeded",
    "HTTP 404: Not Found", "HTTP 500: Server Error", "connection timed out",
])
@pytest.mark.parametrize("partial_output", ["", "v0.28.2"])
def test_query_failure_never_creates_release(publication, error, partial_output):
    result, calls = publication(partial_output, query_error=error)
    assert result.returncode != 0
    assert error in result.stderr
    assert len(calls) == 1


def test_create_failure_fails_job(publication):
    result, calls = publication(create_status=1)
    assert result.returncode != 0
    assert len(calls) == 2


def test_missing_changelog_section_never_creates_release(publication):
    result, calls = publication(release_tag="v9.99.0")
    assert result.returncode != 0
    assert "no non-empty section" in result.stderr
    assert len(calls) == 1


def test_publication_still_requires_all_validation_jobs_and_candidate():
    jobs = yaml.safe_load(WORKFLOW.read_text())["jobs"]
    publish = jobs["publish-release"]
    assert set(publish["needs"]) == {
        "backend", "home-assistant-compatibility", "card", "hassfest",
        "hacs", "version-policy", "release-candidate",
    }
    assert "always()" not in publish["if"]
    assert "github.event_name == 'push'" in publish["if"]
    assert "github.event.deleted != true" in publish["if"]
    assert "needs.release-candidate.outputs.tag != ''" in publish["if"]
    checkout = publish["steps"][0]
    assert checkout["uses"].startswith("actions/checkout@")
    assert checkout["with"]["ref"] == "${{ github.sha }}"
    assert checkout["with"]["persist-credentials"] is False
    step = next(step for step in publish["steps"]
                if step.get("name") == "Create GitHub release")
    assert step["env"]["RELEASE_TARGET"] == "${{ github.sha }}"
    assert step["env"]["RELEASE_TAG"] == "${{ needs.release-candidate.outputs.tag }}"
    candidate = jobs["release-candidate"]["steps"][-1]["run"]
    assert 'python scripts/check_release_tag.py "$RELEASE_TAG"' in candidate
    assert 'if [[ "$TAG_SHA" != "$HEAD_SHA" ]]' in candidate
