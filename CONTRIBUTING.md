# Contributing

Issues and pull requests are welcome. Describe the Home Assistant version,
integration version, steps to reproduce, expected result, and actual result.
Remove tokens, addresses, and private entity names from logs before posting.

## Version and changelog

Before every push, increase the integration version in
`custom_components/smart_shutter/manifest.json` and add a matching `## vX.Y.Z`
section to the top of `CHANGELOG.md`, including for documentation, CI, and
refactoring changes. Use SemVer: breaking changes increase the major version,
new backward-compatible features increase the minor version, and other changes
increase the patch version. The version must be higher than the base commit.

The CI checks version and changelog changes on branch pushes and pull requests.
Pushing a matching `vX.Y.Z` tag publishes a GitHub Release automatically after
all CI jobs pass. Release tags must match the manifest version and be higher
than previous release tags.

## Local checks

Use Python 3.14 and Node.js 24. Install the dependencies from
`requirements-dev.txt` and `package-lock.json` in isolated environments.

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
