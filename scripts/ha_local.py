#!/usr/bin/env python3
"""Local HA lifecycle. State is data; no shell evaluation or global Docker cleanup."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

VIRTUAL = [f"cover.codex_ui_test_{key}" for key in ("alpha", "beta", "gamma")]
LABEL = "io.smart-shutter."
AGENT_RE = re.compile(r"[a-z0-9][a-z0-9_-]{0,47}\Z")


class LocalError(Exception):
    """An actionable error safe to show without credentials."""


class HAHttpError(LocalError):
    def __init__(self, endpoint, status):
        self.status = status
        super().__init__(f"HA request {endpoint} returned HTTP {status}")


def run(args, **kwargs):
    try:
        return subprocess.run(args, check=True, text=True, **kwargs)
    except FileNotFoundError as exc:
        raise LocalError(f"Required executable not found: {args[0]}") from exc
    except subprocess.CalledProcessError as exc:
        raise LocalError(f"Command failed ({exc.returncode}): {args[0]}") from exc


def digest(value):
    return hashlib.sha256(str(value).encode()).hexdigest()[:12]


def safe_path(path):
    """Reject symlink ancestors before any read/write/delete of managed state."""
    path = Path(os.path.abspath(path))
    for item in (path, *path.parents):
        if item.is_symlink():
            raise LocalError(f"Symlink in managed path: {item}")
    return path


def read_json(path):
    safe_path(path)
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise LocalError(f"Invalid or missing state: {path}") from exc


def write_json(path, value):
    safe_path(path)
    temporary = path.with_name(path.name + ".tmp")
    safe_path(temporary)
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as file:
        json.dump(value, file, indent=2)
        file.write("\n")
    os.chmod(temporary, 0o600)
    temporary.replace(path)


def settings(root):
    result = {"HA_VERSION": "2026.9.4", "TZ": "Europe/Berlin",
              "TEST_PORT": "8123", "HA_WAIT_TIMEOUT": "300"}
    path = root / ".env"
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, sep, value = line.partition("=")
            if not sep or key not in result:
                raise LocalError(f"Unsupported .env setting: {key}")
            result[key] = value.strip().strip("\"'")
    for key in result:
        if key in os.environ:
            result[key] = os.environ[key]
    if not re.fullmatch(r"\d{4}\.\d+\.\d+", result["HA_VERSION"]):
        raise LocalError("HA_VERSION must be an explicit release, e.g. 2026.9.4")
    for key in ("TEST_PORT", "HA_WAIT_TIMEOUT"):
        if not result[key].isdigit() or int(result[key]) < 1:
            raise LocalError(f"{key} must be a positive integer")
    if int(result["TEST_PORT"]) > 65535:
        raise LocalError("TEST_PORT must be <= 65535")
    return result


class Environment:
    def __init__(self, root, primary, mode, agent=None):
        self.root = Path(root).resolve()
        self.primary = Path(primary).resolve()
        self.mode, self.agent = mode, agent
        if mode not in ("dev", "test"):
            raise LocalError("Mode must be dev or test")
        if mode == "dev" and (not agent or not AGENT_RE.fullmatch(agent)):
            raise LocalError("AGENT is required: 1-48 lowercase letters, digits, _ or -; start with a letter or digit")
        self.repo_id = digest(self.primary)
        self.instance_id = "test" if mode == "test" else f"{agent}-{digest(self.root)}"
        self.project = "ha-test" if mode == "test" else f"ha-dev-{self.instance_id}"
        self.base = (self.primary if mode == "test" else self.root) / ".runtime"
        self.path = self.base / "test" if mode == "test" else self.base / "dev" / agent
        self.state_file = self.path / "state.json"
        self.compose_file = self.path / "compose.json"
        self.config = self.path / "config"
        self.defaults = settings(self.root)
        self.state = None
        safe_path(self.path)

    def identity(self):
        return {"schema": 1, "repository": self.repo_id, "instance": self.instance_id,
                "project": self.project, "mode": self.mode, "agent": self.agent,
                "runtime": str(self.path)}

    def load(self, required=True):
        if not self.state_file.exists():
            if required:
                raise LocalError(f"Environment does not exist; run {self.mode}-up first")
            if self.path.exists():
                raise LocalError(f"Unmanaged runtime directory; refusing to adopt: {self.path}")
            return False
        state = read_json(self.state_file)
        if any(state.get(key) != value for key, value in self.identity().items()):
            raise LocalError("Runtime identity mismatch; refusing to modify it")
        self.state = state
        return True

    @contextmanager
    def lock(self):
        lock_dir = safe_path(self.base / "locks")
        lock_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        path = safe_path(lock_dir / f"{self.project}.lock")
        with path.open("a") as file:
            try:
                fcntl.flock(file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise LocalError("Environment is busy in another process; retry later") from exc
            yield

    def docker_audit(self):
        """Only containers/networks labelled with this exact project may be touched."""
        for kind, command in (("container", "ps"), ("network", "network")):
            args = (["docker", "ps", "-aq"] if command == "ps" else
                    ["docker", "network", "ls", "-q"])
            args += ["--filter", f"label=com.docker.compose.project={self.project}"]
            ids = run(args, capture_output=True).stdout.split()
            if not ids:
                continue
            objects = json.loads(run(["docker", kind, "inspect", *ids], capture_output=True).stdout)
            for obj in objects:
                labels = obj.get("Labels", {}) if kind == "network" else obj["Config"].get("Labels", {})
                # Compose networks have only Compose labels; their project must have our identity.
                if kind == "container" and any(labels.get(LABEL + key) != value for key, value in
                        (("local", "1"), ("repository", self.repo_id),
                         ("instance", self.instance_id), ("mode", self.mode))):
                    raise LocalError(f"Foreign Docker project {self.project}; refusing to modify it")
                if kind == "network" and labels.get(LABEL + "repository") != self.repo_id:
                    raise LocalError(f"Foreign Docker network in project {self.project}")

    def compose(self, *args, capture=False):
        safe_path(self.compose_file)
        return run(["docker", "compose", "-p", self.project, "-f", str(self.compose_file), *args],
                   cwd=self.root, capture_output=capture)

    def render(self):
        env = os.environ.copy()
        env.update(self.defaults)
        env.update({"HA_CONFIG_DIR": str(self.config), "HA_SOURCE_DIR": str(self.root / "custom_components/smart_shutter"),
                    "HA_FIXTURE_DIR": str(self.root / "docker/fixtures/codex_ui_test"),
                    "HA_REPOSITORY_ID": self.repo_id, "HA_INSTANCE_ID": self.instance_id,
                    "HA_MODE": self.mode})
        output = run(["docker", "compose", "--env-file", "/dev/null", "-p", self.project,
                      "-f", str(self.root / "compose.yml"), "-f", str(self.root / f"compose.{self.mode}.yml"),
                      "config", "--format", "json"], env=env, capture_output=True, cwd=self.root).stdout
        document = json.loads(output)
        document.setdefault("networks", {}).setdefault("default", {})["labels"] = {
            LABEL + "repository": self.repo_id, LABEL + "local": "1"}
        write_json(self.compose_file, document)

    def source_files(self):
        mappings = [(self.root / "config", Path())]
        if self.mode == "test":
            mappings += [(self.root / "custom_components/smart_shutter", Path("custom_components/smart_shutter")),
                         (self.root / "docker/fixtures/codex_ui_test", Path("custom_components/codex_ui_test"))]
        result = {}
        for source, prefix in mappings:
            safe_path(source)
            if not source.is_dir():
                raise LocalError(f"Source directory is missing: {source}")
            for file in sorted(source.rglob("*")):
                if file.is_symlink():
                    raise LocalError(f"Source symlinks are unsupported: {file}")
                relative = file.relative_to(source)
                if any(part in (".storage", "__pycache__", ".git") for part in relative.parts):
                    continue
                if file.is_file() and file.name not in (".DS_Store", ".gitkeep") and not file.name.endswith((".pyc", ".db", ".log")):
                    self.managed_file(str(prefix / relative))
                    result[str(prefix / relative)] = file
        return result

    def source_hash(self):
        h = hashlib.sha256()
        # Both modes hash the same complete source set, including the read-only Dev mounts.
        candidate = Environment(self.root, self.primary, "test")
        for relative, source in sorted(candidate.source_files().items()):
            h.update(relative.encode() + b"\0" + source.read_bytes() + b"\0")
        h.update(self.defaults["HA_VERSION"].encode())
        return h.hexdigest()

    def sync_files(self):
        files = self.source_files()
        old = self.state.get("source_files", [])
        for relative in old:
            if relative not in files:
                target = self.managed_file(relative)
                if target.is_file():
                    target.unlink()
        for relative, source in files.items():
            target = self.managed_file(relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        (self.config / "packages").mkdir(exist_ok=True)
        (self.config / "custom_components").mkdir(exist_ok=True)
        self.state.update(source_files=sorted(files), source_root=str(self.root),
                          source_hash=self.source_hash(), defaults=self.defaults)
        write_json(self.state_file, self.state)

    def managed_file(self, relative):
        rel = Path(relative)
        if rel.is_absolute() or not rel.parts or any(part.startswith(".") for part in rel.parts):
            raise LocalError("Invalid source manifest path")
        if rel.parts[0] == "custom_components":
            if self.mode != "test" or len(rel.parts) < 3 or rel.parts[1] not in ("smart_shutter", "codex_ui_test"):
                raise LocalError("Source manifest cannot address unrelated components or Dev mounts")
        elif rel.parts[0] in ("deps", "tts", "backups") or rel.suffix not in (".yaml", ".yml", ".json"):
            raise LocalError("Source manifest cannot address Home Assistant runtime files")
        return safe_path(self.config / rel)

    def validate_sync(self):
        self.source_files()
        for relative in self.state.get("source_files", []):
            self.managed_file(relative)
        for item in self.config.rglob("*"):
            if item.is_symlink():
                raise LocalError(f"Cannot snapshot a symlinked runtime: {item}")

    def restore_transaction(self):
        journal = self.path / "transaction.json"
        data = read_json(journal)
        if not re.fullmatch(r"[0-9]+", str(data.get("backup", ""))):
            raise LocalError("Invalid sync recovery journal")
        backup = safe_path(self.path / "backups" / data["backup"])
        previous = read_json(backup / "state.json")
        if any(previous.get(key) != value for key, value in self.identity().items()):
            raise LocalError("Backup identity mismatch")
        read_json(backup / "compose.json")
        backup_config = safe_path(backup / "config")
        if not backup_config.is_dir():
            raise LocalError("Backup configuration is missing; current runtime retained")
        for item in backup_config.rglob("*"):
            if item.is_symlink():
                raise LocalError("Backup contains a symlink; current runtime retained")
        self.compose("stop")
        safe_path(self.config)
        if self.config.exists():
            shutil.rmtree(self.config)
        shutil.copytree(backup_config, self.config)
        shutil.copyfile(backup / "state.json", self.state_file)
        shutil.copyfile(backup / "compose.json", self.compose_file)
        self.state = read_json(self.state_file)
        journal.unlink()
        self.compose("up", "-d")

    def sync_transaction(self):
        self.validate_sync()
        backup = safe_path(self.path / "backups" / str(time.time_ns()))
        backup.mkdir(parents=True)
        self.compose("stop")
        try:
            shutil.copytree(self.config, backup / "config")
            shutil.copyfile(self.state_file, backup / "state.json")
            shutil.copyfile(self.compose_file, backup / "compose.json")
            write_json(self.path / "transaction.json", {"backup": backup.name})
            self.sync_files()
            self.render()
            self.compose("up", "-d")
            self.compose("restart")
            self.wait(bootstrap=True)
        except BaseException:
            if (self.path / "transaction.json").exists():
                self.restore_transaction()
            else:
                self.compose("up", "-d")
            raise
        (self.path / "transaction.json").unlink()
        print(f"Previous stand backed up at {backup}")

    def initialize(self):
        self.path.mkdir(parents=True, mode=0o700)
        os.chmod(self.path, 0o700)
        self.config.mkdir(mode=0o700)
        self.state = self.identity()
        write_json(self.state_file, self.state)
        self.sync_files()
        self.render()

    def url(self):
        result = self.compose("ps", "--format", "json", capture=True).stdout.strip()
        if not result:
            return None
        objects = json.loads(result) if result.startswith("[") else [json.loads(line) for line in result.splitlines()]
        if not any(obj.get("State") == "running" for obj in objects):
            return None
        mapping = self.compose("port", "homeassistant", "8123", capture=True).stdout.strip()
        if not mapping:
            return None
        return "http://localhost:" + mapping.rsplit(":", 1)[1]

    def request(self, endpoint, body=None, token=None, form=False):
        base = self.state.get("url")
        if not base:
            raise LocalError("Environment is not running")
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        data = None
        if body is not None:
            headers["Content-Type"] = "application/x-www-form-urlencoded" if form else "application/json"
            data = (urllib.parse.urlencode(body) if form else json.dumps(body)).encode()
        request = urllib.request.Request(base + endpoint, data=data, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                content = response.read()
                return json.loads(content) if content else None
        except urllib.error.HTTPError as exc:
            raise HAHttpError(endpoint, exc.code) from exc
        except (OSError, ValueError) as exc:
            raise LocalError(f"HA request failed: {endpoint}") from exc

    def credentials(self):
        path = self.path / "credentials.json"
        if path.exists():
            return read_json(path)
        creds = {"username": "developer", "password": secrets.token_urlsafe(24),
                 "client_id": "http://localhost/"}
        write_json(path, creds)
        return creds

    def save_credentials(self, creds):
        write_json(self.path / "credentials.json", creds)

    def token(self):
        creds = self.credentials()
        if not creds.get("refresh_token"):
            # Recover an interrupted token exchange using the already-created local user.
            flow = self.request("/auth/login_flow", {"client_id": creds["client_id"],
                "handler": ["homeassistant", None], "redirect_uri": creds["client_id"]})
            flow = self.request("/auth/login_flow/" + flow["flow_id"],
                                {"client_id": creds["client_id"], "username": creds["username"], "password": creds["password"]})
            if flow.get("type") != "create_entry":
                raise LocalError("Local login failed; inspect this instance's credentials without resetting unrelated data")
            response = self.request("/auth/token", {"grant_type": "authorization_code", "code": flow["result"],
                "client_id": creds["client_id"]}, form=True)
        else:
            response = self.request("/auth/token", {"grant_type": "refresh_token", "refresh_token": creds["refresh_token"],
                "client_id": creds["client_id"]}, form=True)
        creds.update({key: response[key] for key in ("access_token", "refresh_token") if key in response})
        self.save_credentials(creds)
        return creds["access_token"]

    def bootstrap(self):
        creds = self.credentials()
        try:
            steps = self.request("/api/onboarding")
        except HAHttpError as exc:
            # After a completed installation restarts, HA no longer registers
            # onboarding views. Only accept this with our existing credentials;
            # authenticated token/config checks below still must succeed.
            if exc.status != 404 or not creds.get("refresh_token"):
                raise
            steps = []
        pending = {step["step"] for step in steps if not step["done"]}
        if "user" in pending:
            response = self.request("/api/onboarding/users", {"name": "Local Developer", "username": creds["username"],
                "password": creds["password"], "client_id": creds["client_id"], "language": "de"})
            response = self.request("/auth/token", {"grant_type": "authorization_code", "code": response["auth_code"],
                "client_id": creds["client_id"]}, form=True)
            creds.update(access_token=response["access_token"], refresh_token=response["refresh_token"])
            self.save_credentials(creds)
        token = self.token()
        for step in ("core_config", "analytics", "integration"):
            if step in pending:
                self.request("/api/onboarding/" + step,
                    {"client_id": creds["client_id"], "redirect_uri": creds["client_id"]} if step == "integration" else {}, token)
        states = self.request("/api/states", token=token)
        cover_ids = {state["entity_id"] for state in states if state["entity_id"].startswith("cover.")}
        if cover_ids != set(VIRTUAL) or any(state["attributes"].get("ui_test_only") is not True
                for state in states if state["entity_id"] in VIRTUAL):
            raise LocalError("Expected only the three verified virtual covers; refusing setup or service calls")
        entries = self.request("/api/config/config_entries/entry?domain=smart_shutter", token=token)
        if not entries:
            self.state["needs_initial_switch_setup"] = True
            write_json(self.state_file, self.state)
            flow = self.request("/api/config/config_entries/flow", {"handler": "smart_shutter"}, token)
            if flow.get("step_id") != "user":
                raise LocalError("Unexpected Smart Shutter setup step")
            flow = self.request("/api/config/config_entries/flow/" + flow["flow_id"], {"cover_selection": VIRTUAL[:2]}, token)
            if flow.get("step_id") != "names":
                raise LocalError("Unexpected Smart Shutter naming step")
            flow = self.request("/api/config/config_entries/flow/" + flow["flow_id"],
                {VIRTUAL[0]: "Test Alpha", VIRTUAL[1]: "Test Beta"}, token)
            if flow.get("type") != "create_entry":
                raise LocalError("Smart Shutter setup did not complete")
        self.state["bootstrap_complete"] = True
        write_json(self.state_file, self.state)

    def wait(self, bootstrap=False):
        self.state["url"] = self.url()
        if not self.state["url"]:
            raise LocalError("Environment is stopped; run up first")
        write_json(self.state_file, self.state)
        deadline = time.monotonic() + int(self.defaults["HA_WAIT_TIMEOUT"])
        last = "Waiting for HTTP"
        completed_bootstrap = not bootstrap
        while time.monotonic() < deadline:
            try:
                if not completed_bootstrap:
                    self.bootstrap()
                    completed_bootstrap = True
                token = self.token()
                states = self.request("/api/states", token=token)
                config = self.request("/api/config", token=token)
                entries = self.request("/api/config/config_entries/entry?domain=smart_shutter", token=token)
                covers = [state for state in states if state["entity_id"].startswith("cover.")]
                if {state["entity_id"] for state in covers} != set(VIRTUAL) or any(
                        state["attributes"].get("ui_test_only") is not True for state in covers):
                    raise LocalError("Instance must contain only the verified virtual covers")
                if "smart_shutter" not in config["components"] or len(entries) != 1 or entries[0]["state"] != "loaded":
                    raise LocalError("Smart Shutter integration not ready")
                if self.state.get("needs_initial_switch_setup"):
                    registry_code = ('import json; from pathlib import Path; '
                        'print((Path("/config/.storage/core.entity_registry")).read_text())')
                    registry = json.loads(self.compose("exec", "-T", "homeassistant", "python", "-c", registry_code, capture=True).stdout)
                    switches = [s["entity_id"] for s in registry["data"]["entities"] if
                        s.get("config_entry_id") == entries[0]["entry_id"] and s.get("platform") == "smart_shutter" and
                        s["unique_id"].startswith("smart_shutter_global_") and
                        s["unique_id"].endswith(("_global_automation_open", "_global_automation_close"))]
                    if len(switches) != 2:
                        raise LocalError("Initial automation switches not ready")
                    self.request("/api/services/switch/turn_off", {"entity_id": switches}, token)
                    self.state.pop("needs_initial_switch_setup")
                self.verify_asset()
                write_json(self.state_file, self.state)
                print(f"Ready: {self.state['url']}/smart-shutter")
                return
            except LocalError as exc:
                last = str(exc)
                time.sleep(2)
        raise LocalError(f"Readiness timed out: {last}. Inspect {self.mode}-logs; state has been retained.")

    def verify_asset(self):
        expected = (self.config if self.mode == "test" else self.root) / "custom_components/smart_shutter/www/smart-shutter-card.js"
        try:
            with urllib.request.urlopen(self.state["url"] + "/smart_shutter_frontend/smart-shutter-card.js", timeout=10) as response:
                remote = response.read()
        except OSError as exc:
            raise LocalError("Smart Shutter frontend asset not ready") from exc
        if hashlib.sha256(remote).digest() != hashlib.sha256(expected.read_bytes()).digest():
            raise LocalError("Loaded frontend asset differs from the selected source")

    def show(self):
        url = self.url()
        print(json.dumps({"agent": self.agent, "project": self.project,
            "status": "running" if url else "stopped", "port": url.rsplit(":", 1)[1] if url else None,
            "url": url, "last_url": self.state.get("url"), "runtime": str(self.path),
            "source_hash": self.state.get("source_hash"), "review": self.state.get("review")}, indent=2))

    def assert_no_review(self):
        if self.mode == "test" and self.state and self.state.get("review"):
            raise LocalError("Test UI has a pending human review. Resolve it explicitly with test-review-clear before changing the test stand.")

    def confirm(self, yes, action):
        if yes:
            return
        if not sys.stdin.isatty():
            raise LocalError(f"{action} requires confirmation; use --yes (Make: CONFIRM=yes)")
        if input(f"{action} {self.project} at {self.path}? Type {self.project}: ") != self.project:
            raise LocalError("Cancelled")

    def clean(self, yes):
        if self.mode != "dev":
            raise LocalError("Cleanup and reset are Dev-only; test data cannot be removed by this command")
        self.confirm(yes, "Delete")
        self.compose("down", "--remove-orphans")
        safe_path(self.path)
        for item in self.path.rglob("*"):
            if item.is_symlink():
                raise LocalError(f"Refusing cleanup of runtime containing a symlink: {item}")
        shutil.rmtree(self.path)

    def action(self, action, yes=False):
        if action in ("status", "logs"):
            self.load()
            self.docker_audit()
            if action == "status":
                self.show()
            else:
                self.compose("logs", "--follow", "--tail", "100")
            return
        with self.lock():
            exists = self.load(required=action != "up")
            self.docker_audit()
            if exists and (self.path / "transaction.json").exists() and action in ("up", "sync", "restart", "wait"):
                self.assert_no_review()
                self.restore_transaction()
            if action == "up":
                if not exists:
                    self.initialize()
                elif not self.compose_file.exists():
                    # Resume initialization only before any Compose project was started.
                    self.assert_no_review()
                    self.config.mkdir(exist_ok=True)
                    self.sync_files()
                    self.render()
                elif self.mode == "dev" and (self.state.get("source_hash") != self.source_hash()
                        or self.state.get("defaults") != self.defaults):
                    self.sync_transaction()
                self.compose("up", "-d")
                self.wait(bootstrap=True)
                self.show()
            elif action == "down":
                self.compose("down", "--remove-orphans")
                print(f"Stopped {self.project}; data retained at {self.path}")
            elif action in ("restart", "sync"):
                self.assert_no_review()
                if action == "sync" or self.mode == "dev":
                    self.sync_transaction()
                else:
                    self.compose("restart")
                    self.wait(bootstrap=True)
            elif action == "wait":
                self.wait(bootstrap=True)
            elif action in ("clean", "reset"):
                self.clean(yes)
                if action == "reset":
                    self.initialize()
                    self.compose("up", "-d")
                    self.wait(bootstrap=True)
                    self.show()
            elif action == "review":
                if self.mode != "test":
                    raise LocalError("Human review is recorded on the stable Test instance")
                self.assert_no_review()
                if (self.path / "transaction.json").exists():
                    raise LocalError("Cannot begin review during an incomplete sync; recover with test-up first")
                self.wait()
                if self.state.get("source_hash") != self.source_hash():
                    raise LocalError("Test stand differs from this worktree; run test-sync before review")
                self.state["review"] = {"source_hash": self.state["source_hash"], "source_root": str(self.root),
                    "started_at": time.time(), "status": "awaiting_human"}
                write_json(self.state_file, self.state)
                self.show()
            elif action == "review-clear":
                self.confirm(yes, "Clear pending review for")
                self.state.pop("review", None)
                write_json(self.state_file, self.state)
            else:
                raise LocalError(f"Unsupported action: {action}")


def roots():
    root = Path(__file__).resolve().parent.parent
    common = Path(run(["git", "-C", str(root), "rev-parse", "--path-format=absolute", "--git-common-dir"],
                      capture_output=True).stdout.strip())
    if common.name != ".git":
        raise LocalError("Use a regular Git checkout or linked worktree; bare repositories are unsupported")
    return root, common.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("dev", "test"))
    parser.add_argument("action", choices=("up", "down", "restart", "sync", "wait", "status", "logs", "list", "clean", "reset", "review", "review-clear"))
    parser.add_argument("agent", nargs="?")
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    root, primary = roots()
    if args.action == "list" or args.all:
        if args.mode != "dev" or (args.all and args.action != "clean") or args.agent:
            raise LocalError("--all is only supported for dev-clean without an agent")
        directory = safe_path(root / ".runtime/dev")
        instances = sorted(directory.iterdir()) if directory.exists() else []
        if args.action == "list":
            print("AGENT\tSTATUS\tPORT\tURL")
        for path in instances:
            if not path.is_dir() or path.is_symlink():
                raise LocalError(f"Unexpected runtime entry: {path}")
            env = Environment(root, primary, "dev", path.name)
            if args.all:
                env.action("clean", args.yes)
            else:
                env.load()
                env.docker_audit()
                url = env.url()
                port = url.rsplit(":", 1)[1] if url else (env.state.get("url") or "-").rsplit(":", 1)[-1]
                print(f"{path.name}\t{'running' if url else 'stopped'}\t{port}{'' if url else ' (last)'}\t{url or '-'}")
        return
    if args.mode == "test" and args.agent:
        raise LocalError("Test commands do not accept AGENT")
    Environment(root, primary, args.mode, args.agent).action(args.action, args.yes)


if __name__ == "__main__":
    try:
        main()
    except (LocalError, OSError, KeyError, ValueError) as exc:
        # HA responses/credentials are never included in errors.
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(130)
