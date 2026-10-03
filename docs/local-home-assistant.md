# Local Home Assistant

Requires Docker with Compose v2 or newer, Bash, Git, and Python 3 on macOS/Linux.
Browser checks additionally use this repository's Node/Playwright dependencies.
No Kubernetes, privileged mode, hardware mounts or host networking are needed.
Install test dependencies as described in `CONTRIBUTING.md`. To keep browsers
inside the checkout, use
`PLAYWRIGHT_BROWSERS_PATH="$PWD/.playwright-browsers" npx playwright install chromium`.
The Make targets and UI checker detect that local browser directory automatically.

## Test

```bash
make test-up
make test-status
make test-logs
make test-down
```

There is one stable project `ha-test`, normally at **http://localhost:8123**.
All linked worktrees share its runtime in the primary checkout's `.runtime/test/`.
Starting an existing Test does not replace its source snapshot. An occupied port
or a foreign project causes an error; no existing container is stopped.

Copy `.env.example` to `.env` to change defaults. `HA_VERSION` is an explicit
release (initially `2026.9.4`, matching the repository CI); `TZ`, `TEST_PORT`,
and `HA_WAIT_TIMEOUT` are supported. Environment variables override the file.
An existing Test keeps its rendered image/port settings until `test-sync`.
Bare Git repositories are unsupported; ordinary checkouts and linked worktrees work.
HTTP settings are managed under **Settings → System → Network**. The source
configuration intentionally has no `http:` YAML block; migrated HTTP settings
would ignore that block and raise a repair warning.

## Dev and multiple agents

```bash
make dev-up AGENT=codex-1
make dev-up AGENT=codex-2
make dev-up AGENT=claude-1
make dev-list
make dev-status AGENT=codex-1
make dev-logs AGENT=codex-1
make dev-down AGENT=codex-1
```

Equivalent scripts are executable directly: `./scripts/dev-up.sh codex-1`.
Identifiers contain 1–48 lowercase letters, digits, `_` or `-` and start with a
letter/digit. Missing/invalid names fail without starting Docker resources.

Docker chooses a free port on `127.0.0.1`. Start/status output gives the current
URL; `dev-list` distinguishes live ports from last-used stopped ports. Ports may
change after `down`/`up` or recreation. Each Compose project is
`ha-dev-<agent>-<hash-of-worktree-path>`, with its own bridge network and container.
Running the same agent identifier from two worktrees therefore stays isolated.

Scripts resolve the checkout containing the script rather than the shell's cwd:

```bash
git worktree add ../worktrees/agent-a feature/a
git worktree add ../worktrees/agent-b feature/b
cd ../worktrees/agent-a
make dev-up AGENT=codex-1
# Run make dev-up AGENT=codex-1 in agent-b independently.
```

Dev data, credentials, logs and review screenshots belong to
`.runtime/dev/<agent>/`. The writable `config/` contains this instance's `.storage`,
database and YAML working copy. Source YAML is maintained in repository `config/`,
including `packages/` and automations. A source manifest limits synchronization
and deletion to previously managed files; it never synchronizes `.storage`.

Dev mounts this worktree's `custom_components/smart_shutter` and
`docker/fixtures/codex_ui_test` read-only into its config. It does not mount a shared
writable config directory. `make dev-sync AGENT=codex-1` copies current source YAML
and restarts HA; `dev-restart` does the same. JS is served from the source mount;
reload the browser and verify delivery. Python changes need a restart.
Test instead uses complete source copies, updated only with `make test-sync`.
Sync backs up the previous config/state/Compose definition and restores it if
startup fails. Backups remain in the instance's `backups/` for manual inspection.

## Onboarding and virtual shutters

`up` and reset automatically create a local developer account, finish onboarding,
load three virtual shutters and configure Smart Shutter with Alpha and Beta.
Gamma is available for add/remove tests. Open, close, position and stop animate
only local in-memory state; no fixture reaches hardware. Schedules start disabled.
Bootstrap does not overwrite an existing user's choices on subsequent starts.

Per-instance `credentials.json` contains the local username/password and refresh
token, with file mode `0600` inside a restricted Runtime directory. Read that file
locally for a manual browser login; do not paste credentials into chat or logs.
The browser-check script handles authentication without printing credentials.
The old `xenodochial_pike` URL/token are not used by these environments.

Bridge networking intentionally limits multicast discovery. Avoid adding real
hardware integrations. These are virtual-only test environments. A shared Docker
daemon is not a security boundary against malicious agents; ownership labels,
runtime validation and the skill prevent accidental cross-instance operations.

## Cleanup and reset

```bash
make dev-clean AGENT=codex-1         # interactive confirmation
make dev-reset AGENT=codex-1        # interactive confirmation, then fresh onboarding
make dev-clean AGENT=codex-1 CONFIRM=yes
./scripts/dev-clean.sh --all --yes  # ONLY this worktree's managed Dev instances
```

`down` retains state; `clean` removes this instance's Compose resources and runtime;
reset does clean followed by initialization from current sources. No Test cleanup
or reset exists. No global Docker/volume prune is used. Locks serialize mutations
and labels prevent adopting foreign projects. Symlinked runtime paths are refused.
Disk/mount permission failures retain state and produce a nonzero exit code.

## Checks and UI approval

```bash
make test-wait
make test-run                      # existing Python/card suites plus real HA UI baseline
node scripts/ha_ui_check.cjs dev codex-1
python3 scripts/ha_virtual_check.py dev codex-1  # only verified fixture IDs; restores position
make test-sync                     # explicitly promote this worktree
node scripts/ha_ui_check.cjs test
make test-review                   # reserve this stand for human inspection
make test-status
```

Readiness is bounded by `HA_WAIT_TIMEOUT` and checks auth, virtual covers, loaded
Smart Shutter and the frontend content hash. Infrastructure unit tests run with
`python3 -m unittest discover -s tests/local_ha -v`; release tests retain their
existing discovery settings. `test-run` assumes `.venv` and npm dependencies exist.

For UI changes: test the changed interactions yourself in Dev, get an independent
second agent review, resolve findings, promote to Test and recheck. `test-review`
records the source hash and blocks further sync/restart while the human review is
pending. Give the user the Test URL, short changes and quick review steps. Wait
for explicit UI approval before an authorized commit. Any further change invalidates
approval. `make test-review-clear CONFIRM=yes` releases the reservation after the
user resolves it; the command itself does not approve or authorize a commit.

Baseline browser checks are read-only. They produce desktop/mobile screenshots and
a sanitized report under the instance's `review-artifacts/`. They do not replace
interaction checks for the feature being changed. Do not persist browser traces
containing authentication or claim hardware behavior was tested.

## Versioned versus local files

Compose files, `.env.example`, Makefile, scripts, source config, virtual fixtures,
this document, `AGENTS.md` and the project skill are versioned. `.env`, `.env.local`
and all `.runtime/` contents are ignored. No real-installation secrets/state are
copied. Runtime `state.json` and rendered `compose.json` are data, never sourced
as shell programs. `.env.local` is reserved/ignored but is not automatically read.

Validate both definitions without starting a container:

```bash
docker compose -f compose.yml -f compose.dev.yml config
docker compose -f compose.yml -f compose.test.yml config
```

Runtime commands render these merges to an instance-local `compose.json`; saved
definitions keep stop/cleanup independent of later edits to shared defaults.
No `container_name`, global network name, named-volume state or host network is used.

## Files added or changed for this setup

Only `.gitignore` was modified; the following other files were added. Runtime
reports and credentials under `.runtime/` are excluded.

- `.gitignore`
- `.agents/skills/smart-shutter-dev/SKILL.md`
- `.agents/skills/smart-shutter-dev/agents/openai.yaml`
- `.env.example`
- `AGENTS.md`
- `Makefile`
- `compose.dev.yml`
- `compose.test.yml`
- `compose.yml`
- `config/automations.yaml`
- `config/configuration.yaml`
- `config/packages/.gitkeep`
- `config/scenes.yaml`
- `config/scripts.yaml`
- `docker/fixtures/codex_ui_test/__init__.py`
- `docker/fixtures/codex_ui_test/cover.py`
- `docker/fixtures/codex_ui_test/manifest.json`
- `docs/local-home-assistant.md`
- `scripts/dev-clean.sh`
- `scripts/dev-down.sh`
- `scripts/dev-list.sh`
- `scripts/dev-logs.sh`
- `scripts/dev-reset.sh`
- `scripts/dev-restart.sh`
- `scripts/dev-status.sh`
- `scripts/dev-sync.sh`
- `scripts/dev-up.sh`
- `scripts/dev-wait.sh`
- `scripts/ha_local.py`
- `scripts/ha_ui_check.cjs`
- `scripts/ha_virtual_check.py`
- `scripts/test-down.sh`
- `scripts/test-logs.sh`
- `scripts/test-restart.sh`
- `scripts/test-review-clear.sh`
- `scripts/test-review.sh`
- `scripts/test-status.sh`
- `scripts/test-sync.sh`
- `scripts/test-up.sh`
- `scripts/test-wait.sh`
- `tests/local_ha/test_manager.py`
- `tests/local_ha/test_virtual_guard.py`
