"""Infrastructure behavior tests: no Docker daemon or network required."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("ha_local", Path(__file__).resolve().parents[2] / "scripts/ha_local.py")
ha = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ha)


class EnvironmentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "main"
        self.other = Path(self.tmp.name) / "worktree"
        for root in (self.root, self.other):
            for name in ("config", "custom_components/smart_shutter/www", "docker/fixtures/codex_ui_test"):
                (root / name).mkdir(parents=True)
            (root / "config/configuration.yaml").write_text("homeassistant:\n")
            (root / "custom_components/smart_shutter/www/smart-shutter-card.js").write_text("// card")
            (root / "docker/fixtures/codex_ui_test/cover.py").write_text("# virtual")

    def env(self, mode="dev", root=None, agent="agent-a"):
        return ha.Environment(root or self.root, self.root, mode, agent if mode == "dev" else None)

    def init(self, env):
        with patch.object(env, "render", lambda: ha.write_json(env.compose_file, {"services": {}})):
            env.initialize()

    def test_worktree_isolation_and_shared_test(self):
        first, second = self.env(), self.env(root=self.other)
        self.assertNotEqual(first.project, second.project)
        self.assertNotEqual(first.path, second.path)
        self.assertEqual(first.repo_id, second.repo_id)
        a, b = self.env("test"), self.env("test", self.other)
        self.assertEqual(a.path, b.path)
        self.assertEqual(a.project, "ha-test")
        self.assertEqual(a.identity(), b.identity())

    def test_invalid_names_fail_before_runtime(self):
        for name in (None, "", "../test", "UPPER", "a;b", "$(touch x)", "a b", "-all", "a" * 49):
            with self.subTest(name=name), self.assertRaises(ha.LocalError):
                self.env(agent=name)
        self.assertFalse((self.root / ".runtime").exists())

    def test_symlinked_runtime_is_refused(self):
        (self.root / ".runtime").symlink_to(self.other, target_is_directory=True)
        with self.assertRaises(ha.LocalError):
            self.env()

    def test_source_root_symlink_is_refused(self):
        env = self.env()
        (self.root / "config/configuration.yaml").unlink()
        (self.root / "config").rmdir()
        (self.root / "config").symlink_to(self.other / "config", target_is_directory=True)
        with self.assertRaises(ha.LocalError):
            env.source_files()

    def test_sync_preserves_runtime_and_deletes_only_obsolete_sources(self):
        env = self.env()
        (self.root / "config/obsolete.yaml").write_text("[]")
        self.init(env)
        storage = env.config / ".storage"
        storage.mkdir()
        (storage / "auth").write_text("sentinel")
        (env.config / "home-assistant_v2.db").write_text("database")
        (self.root / "config/obsolete.yaml").unlink()
        (self.root / "config/configuration.yaml").write_text("homeassistant:\n  name: updated\n")
        env.sync_files()
        self.assertFalse((env.config / "obsolete.yaml").exists())
        self.assertEqual((storage / "auth").read_text(), "sentinel")
        self.assertEqual((env.config / "home-assistant_v2.db").read_text(), "database")

    def test_manifest_cannot_delete_runtime_or_traverse(self):
        for mode in ("dev", "test"):
            env = self.env(mode)
            for path in ("../test/state.json", "/etc/passwd", ".storage/auth", ".HA_VERSION",
                         "home-assistant_v2.db", "home-assistant_v2.db-wal", "home-assistant.log.1",
                         "deps/code.json", "custom_components/unrelated/manifest.json"):
                with self.subTest(mode=mode, path=path), self.assertRaises(ha.LocalError):
                    env.managed_file(path)

    def test_test_snapshot_stays_stable_until_sync(self):
        env = self.env("test")
        self.init(env)
        source = self.root / "custom_components/smart_shutter/www/smart-shutter-card.js"
        source.write_text("// updated")
        self.assertEqual((env.config / "custom_components/smart_shutter/www/smart-shutter-card.js").read_text(), "// card")
        env.sync_files()
        self.assertEqual((env.config / "custom_components/smart_shutter/www/smart-shutter-card.js").read_text(), "// updated")

    def test_identity_corruption_refused(self):
        env = self.env()
        self.init(env)
        state = ha.read_json(env.state_file)
        state["project"] = "ha-test"
        ha.write_json(env.state_file, state)
        with self.assertRaises(ha.LocalError):
            env.load()

    def test_foreign_docker_project_refused(self):
        env = self.env()
        responses = [subprocess.CompletedProcess([], 0, "container-id"),
                     subprocess.CompletedProcess([], 0, json.dumps([{"Config": {"Labels": {}}}]))]
        with patch.object(ha, "run", side_effect=responses), self.assertRaises(ha.LocalError):
            env.docker_audit()

    def test_test_cannot_be_cleaned_or_reset(self):
        env = self.env("test")
        self.init(env)
        with patch.object(env, "compose") as compose, self.assertRaises(ha.LocalError):
            env.clean(True)
        compose.assert_not_called()
        self.assertTrue(env.config.exists())

    def test_cleanup_requires_confirmation_and_preserves_neighbors(self):
        env, neighbor = self.env(), self.env(agent="agent-b")
        test = self.env("test")
        for candidate in (env, neighbor, test):
            self.init(candidate)
        with patch("sys.stdin.isatty", return_value=False), patch.object(env, "compose") as compose:
            with self.assertRaises(ha.LocalError):
                env.clean(False)
            compose.assert_not_called()
            env.clean(True)
        self.assertFalse(env.path.exists())
        self.assertTrue(neighbor.path.exists())
        self.assertTrue(test.path.exists())

    def test_review_blocks_replacement_and_sync(self):
        env = self.env("test")
        self.init(env)
        env.state["review"] = {"source_hash": env.state["source_hash"]}
        ha.write_json(env.state_file, env.state)
        for action in ("review", "sync", "restart"):
            with patch.object(env, "docker_audit"), patch.object(env, "wait") as wait:
                with self.subTest(action=action), self.assertRaises(ha.LocalError):
                    env.action(action)
                wait.assert_not_called()

    def test_failed_render_restores_previous_stand(self):
        env = self.env("test")
        self.init(env)
        (env.config / ".storage").mkdir()
        (env.config / ".storage/auth").write_text("old auth")
        (self.root / "config/configuration.yaml").write_text("changed:\n")
        with patch.object(env, "compose"), patch.object(env, "render", side_effect=ha.LocalError("bad compose")):
            with self.assertRaises(ha.LocalError):
                env.sync_transaction()
        self.assertEqual((env.config / "configuration.yaml").read_text(), "homeassistant:\n")
        self.assertEqual((env.config / ".storage/auth").read_text(), "old auth")
        self.assertFalse((env.path / "transaction.json").exists())

    def test_incomplete_initialization_resumes(self):
        env = self.env("test")
        env.path.mkdir(parents=True)
        ha.write_json(env.state_file, env.identity())
        with patch.object(env, "docker_audit"), patch.object(env, "compose"), patch.object(env, "wait"), patch.object(env, "show"), \
                patch.object(env, "render", lambda: ha.write_json(env.compose_file, {"services": {}})):
            env.action("up")
        self.assertTrue(env.compose_file.exists())
        self.assertTrue((env.config / "configuration.yaml").exists())

    def test_restore_resumes_when_config_was_already_removed(self):
        env = self.env("test")
        self.init(env)
        backup = env.path / "backups/123"
        backup.mkdir(parents=True)
        import shutil
        shutil.copytree(env.config, backup / "config")
        shutil.copyfile(env.state_file, backup / "state.json")
        shutil.copyfile(env.compose_file, backup / "compose.json")
        ha.write_json(env.path / "transaction.json", {"backup": "123"})
        shutil.rmtree(env.config)
        with patch.object(env, "compose"):
            env.restore_transaction()
        self.assertEqual((env.config / "configuration.yaml").read_text(), "homeassistant:\n")
        self.assertFalse((env.path / "transaction.json").exists())

    def test_review_cannot_reserve_partial_sync(self):
        env = self.env("test")
        self.init(env)
        ha.write_json(env.path / "transaction.json", {"backup": "123"})
        with patch.object(env, "docker_audit"), patch.object(env, "wait") as wait, self.assertRaises(ha.LocalError):
            env.action("review")
        wait.assert_not_called()

    def test_recovery_cannot_overwrite_pending_review(self):
        env = self.env("test")
        self.init(env)
        env.state["review"] = {"source_hash": "reserved"}
        ha.write_json(env.state_file, env.state)
        ha.write_json(env.path / "transaction.json", {"backup": "123"})
        with patch.object(env, "docker_audit"), patch.object(env, "restore_transaction") as restore, self.assertRaises(ha.LocalError):
            env.action("up")
        restore.assert_not_called()

    def test_repeated_dev_up_does_not_stop_unchanged_instance(self):
        env = self.env()
        self.init(env)
        with patch.object(env, "docker_audit"), patch.object(env, "compose") as compose, patch.object(env, "wait"), patch.object(env, "show"):
            env.action("up")
        self.assertEqual(compose.call_args_list[0].args, ("up", "-d"))

    def test_concurrent_mutation_is_rejected(self):
        first, second = self.env(), self.env()
        with first.lock(), self.assertRaises(ha.LocalError):
            with second.lock():
                pass

    def test_completed_onboarding_after_restart_uses_existing_auth(self):
        env = self.env("test")
        self.init(env)
        requests = []

        def request(endpoint, body=None, token=None):
            requests.append(endpoint)
            if endpoint == "/api/onboarding":
                raise ha.HAHttpError(endpoint, 404)
            if endpoint == "/api/states":
                self.assertEqual(token, "local-token")
                return [{"entity_id": entity, "attributes": {"ui_test_only": True}} for entity in ha.VIRTUAL]
            if endpoint == "/api/config/config_entries/entry?domain=smart_shutter":
                return [{"entry_id": "existing"}]
            self.fail(f"Unexpected setup mutation after restart: {endpoint}")

        with patch.object(env, "credentials", return_value={"refresh_token": "existing"}), \
                patch.object(env, "token", return_value="local-token") as token, patch.object(env, "request", side_effect=request):
            env.bootstrap()
        token.assert_called_once()
        self.assertTrue(env.state["bootstrap_complete"])
        self.assertEqual(len(requests), 3)

    def test_missing_onboarding_without_existing_credentials_is_not_adopted(self):
        env = self.env("test")
        self.init(env)
        with patch.object(env, "credentials", return_value={}), patch.object(env, "token") as token, \
                patch.object(env, "request", side_effect=ha.HAHttpError("/api/onboarding", 404)):
            with self.assertRaises(ha.HAHttpError):
                env.bootstrap()
        token.assert_not_called()


if __name__ == "__main__":
    unittest.main()
