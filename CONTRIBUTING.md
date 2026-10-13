# Contributing

Issues and pull requests are welcome. Describe the Home Assistant version,
integration version, steps to reproduce, expected result, and actual result.
Remove tokens, addresses, and private entity names from logs before posting.

## Version, changelog, and releases

Changes to the shipped integration package under
`custom_components/smart_shutter/` or its user-facing release documentation
must increase `custom_components/smart_shutter/manifest.json` and add a new,
non-empty `## vX.Y.Z` section at the top of `CHANGELOG.md`. Include at least one
change bullet. Use Semantic Versioning: breaking changes increase the major
number, backward-compatible features increase the minor number, and fixes
increase the patch number.

Changes limited to CI, developer scripts, agent guidance, tests, or other
repository tooling do not need an integration version bump. Historical
changelog backfills are also allowed when explicitly named: leave the current
manifest version unchanged, change only the historical changelog entry among
release-relevant files, and use a commit subject containing
`backfill vX.Y.Z`.

### Prepare and review a release

Fetch the release tags and run the preparation script once after making the
release's code changes:

```sh
git fetch origin --tags
python scripts/prepare_release.py patch  # or: minor / major
```

The script reads the installed integration version from `manifest.json`, finds
the latest stable local `vX.Y.Z` tag, and updates only `manifest.json` and the
top section of `CHANGELOG.md`. It does not create Git tags, commits, pushes, or
GitHub Releases. Existing edits to either output file are protected; keep code
changes in place and the script will mark their paths for manual changelog
review. Repository-only edits are ignored. If the manifest already contains
one SemVer step beyond the latest stable tag, a rerun reuses that draft instead
of incrementing it again. A larger unexplained gap is an error.

Conventional Commit subjects map `feat` to Added, `fix` to Fixed, `remove` to
Removed, `security` to Security, and `perf`, `refactor`, `docs`, `build`, `ci`,
`test`, `style`, and `chore` to Changed. `!` and `BREAKING CHANGE:` map to
Breaking Changes. The script reads local non-merge commit subjects and bodies;
PR titles are represented when the project uses squash merges or otherwise
keeps the PR title in the commit subject. Unknown commit messages, and current
uncommitted integration changes whose intent cannot be inferred, appear under
`Review Required`. Summarize those entries manually, remove review markers, and
check the wording and categories before committing. Existing entries are kept;
duplicate version headings, categories, source markers, and bullets stop
preparation with an error. The `prepare-release` HTML comments are source
markers and are removed from the published GitHub Release notes.

Run the local gate and relevant tests, then push a branch or open a pull
request. The existing `validate.yml` checks the version, matching changelog,
integration/card tests, Hassfest, and HACS. After an approved version change
reaches the default branch, that same workflow creates the `vX.Y.Z` GitHub
Release using the exact matching `CHANGELOG.md` section and verifies the
published Git tag, release status, version, and release notes through GitHub's
API with bounded retries. Re-running publication leaves an existing release
unchanged and verifies it instead of creating a duplicate. `release-version.yml`
continues to validate tag pushes and also verifies releases published outside
that workflow. This confirms the GitHub publication only; it does not confirm
that HACS has refreshed its own repository data.

HACS maintains repository metadata separately from the GitHub Release. It may
not display a new update until its next metadata refresh; use the repository's
**Update information** action in HACS to fetch the current GitHub data sooner.
An installation version comes from the installed integration manifest, while
the available version comes from the published release/tag.

CI checks version and changelog changes on branch pushes and pull requests.
When a higher integration version reaches the default branch, the workflow
creates its matching `vX.Y.Z` tag and GitHub Release after all validation jobs
pass. Pushing a matching `vX.Y.Z` tag manually also publishes a GitHub Release.
Release tags must match the manifest version and be higher than previous
release tags. GitHub publication verification does not imply that HACS has
updated its local repository metadata.

## Pre-commit review

Before committing, inspect the full diff and run the local gate with the
proposed commit subject. Compare against the last pushed branch ref; for a
branch's first push, use the default branch for both refs.

```sh
python -m scripts.pre_commit_gate \
  --base-ref origin/your-branch \
  --default-branch-ref origin/main \
  --subject "feat(card): describe the user-visible change"
```

For a historical changelog backfill, also pass `--backfill-version X.Y.Z` and
include `backfill vX.Y.Z` in the subject. Do not infer backfill intent only
from a branch name. The gate checks release policy when relevant paths change,
commit subject format and clarity, whitespace, and the affected Python or card
tests. Codex reviews the complete diff, SemVer choice, changelog accuracy, and
whether the subject makes the change easy to find later. Hassfest, HACS, and
the complete GitHub Actions matrix run in CI.

## Local checks

Use Python 3.14 and Node.js 24. Install dependencies from `requirements-dev.txt`
and `package-lock.json` in isolated environments.

```sh
python -m pytest -q
python ast_walker.py custom_components/smart_shutter
python method_ref_checker.py custom_components/smart_shutter/www/smart-shutter-card.js
node --check custom_components/smart_shutter/www/smart-shutter-card.js
npm ci
npx playwright install chromium
npm run test:card
```

Changes to scheduling, service actions, or access control need behavior tests.
Never claim browser or real device behavior was tested unless that check was
actually performed.
