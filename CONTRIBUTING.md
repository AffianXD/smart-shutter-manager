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

CI checks version and changelog changes on branch pushes and pull requests.
Pushing a matching `vX.Y.Z` tag publishes a GitHub Release after all validation
jobs pass. Release tags must match the manifest version and be higher than
previous release tags.

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
