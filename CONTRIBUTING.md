# Contributing

Issues and pull requests are welcome. Describe the Home Assistant version,
integration version, steps to reproduce, expected result, and actual result.
Remove tokens, addresses, and private entity names from logs before posting.

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
Run Hassfest and HACS validation before a release. Never claim browser or real
device behavior was tested unless that check was actually performed.
