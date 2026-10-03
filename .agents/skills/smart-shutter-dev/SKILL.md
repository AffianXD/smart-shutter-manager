---
name: smart-shutter-dev
description: Manage isolated local Home Assistant instances for Smart Shutter Manager development, test virtual shutters, and prepare UI changes for independent agent and human review before commits.
---

# Smart Shutter development

Read [local HA operations](../../../docs/local-home-assistant.md) when using
the lifecycle tools. Run them from the current checkout/worktree; use a unique
agent name such as `codex-1`. The manager derives paths and validates ownership.

## Dev loop

- `make dev-up AGENT=codex-1` starts a private, automatically configured instance.
  `dev-status` provides its current URL. Ports can change after recreation.
- Dev mounts this worktree's Smart Shutter and virtual fixtures read-only. After
  Python/YAML edits, run `make dev-restart AGENT=codex-1`; verify frontend delivery
  and reload the browser after JS edits. State belongs to this instance alone.
- Dev instances share the `developer` login from the primary checkout's ignored
  `.env` (`HA_DEV_PASSWORD`). First `dev-up` generates it if empty. Existing Dev
  accounts are aligned on their next start; each instance still has its own token.
- Load `.runtime/dev/<agent>/credentials.json` only through local tools/in-memory
  browser setup. Never print its contents or the `.env` password, persist browser
  auth traces or reuse the old installation's token.
- Run relevant existing Python and card tests. For baseline real-HA UI checks,
  run `node scripts/ha_ui_check.cjs dev codex-1`; then inspect actual changed
  interactions, including desktop and mobile views. Baseline is read-only.
- Before interactive writes, verify that all cover entities belong to platform
  `codex_ui_test`, have `ui_test_only: true`, and are the three expected fixture
  IDs. Control only those IDs. Reject unknown/mixed targets, `all`, area/device
  targets and indirect actions that can reach nonvirtual entities.
- Never change another agent's instance or the existing `xenodochial_pike` HA.
  Do not import real HA runtime/auth/configuration or hardware integrations.

## Independent and human review

Follow repository `AGENTS.md`: own checks, second agent review of current
diff/evidence/affected UI flows, resolve findings, then `make test-sync` and Test
UI verification. Run `make test-review` to reserve the stand for human inspection.
Mutating Test commands queue across linked worktrees; read-only status/logs remain
available while another command holds the shared Test lock. A pending human review
still blocks Test replacement/restart until explicitly resolved.
Provide the Test URL, source hash and quick review steps. Await explicit user UI
approval before an authorized commit. Changes invalidate approval. Never clear
another pending review automatically. `test-review-clear CONFIRM=yes` releases
the reservation only after the user has resolved it; it is not an approval.

## Lifecycle boundaries

`dev-down` preserves data. `dev-clean` deletes only the named Dev instance;
`dev-reset` rebuilds it from current sources. Use `CONFIRM=yes` only when the
specific deletion/reset is authorized. `dev-clean --all` is confined to this
worktree. Test has no cleanup/reset command. Do not use global Docker prune,
volume deletion, host networking or production endpoints to fix a failed start.
