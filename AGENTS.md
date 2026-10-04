# Smart Shutter Manager development

Use `.agents/skills/smart-shutter-dev/SKILL.md` for local HA development and UI validation.
Agents use their own Dev instance and worktree. Never operate another agent's
instance or the existing `xenodochial_pike` installation. Only verified virtual
`codex_ui_test` covers may be controlled; never control real covers.

## UI changes before a commit

1. Run relevant Python/card tests and inspect the changed flows in your Dev UI,
   including desktop and mobile views. Baseline screenshots alone do not validate
   changed interactions.
2. Have a second agent independently review the current diff and test evidence
   and inspect the affected UI flows. Resolve findings and repeat affected checks.
3. Promote the reviewed stand with `make test-sync`, recheck it in the stable Test
   UI, then mark it with `make test-review`. If a human review is already pending,
   do not clear or overwrite it without explicit user direction.
   After a successful `test-sync`, stop only this worktree's Dev instance with
   `make dev-down AGENT=<agent>`; keep its runtime while Test is under human
   review in case follow-up changes are requested.
4. Give the user the Test URL, a short change list and quick review steps. Wait
   for their explicit UI approval before an authorized commit. Approval applies
   only to the reviewed diff and source hash. Further UI changes or a different
   Test deployment require new review. `test-review-clear` only releases the
   pending-review lock; it does not grant approval or permission to commit.

Do not stage, commit or push without authorization. Do not put credentials in Git,
logs, screenshots, traces or messages. Do not claim unperformed browser/device
checks passed. Cleanup/reset are Dev-only. At feature completion, after review is
resolved and no follow-up work is pending, clean only this worktree's Dev instance
with `make dev-clean AGENT=<agent> CONFIRM=yes`; this lifecycle cleanup is
authorized. Reset still requires explicit confirmation. Never clean another
agent's instance or use `--all` as routine feature cleanup.
