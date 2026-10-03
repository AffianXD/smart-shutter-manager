#!/usr/bin/env python3
"""Exercise only registry-verified virtual covers in a managed local instance."""
import argparse
import json
import time

from ha_local import Environment, LocalError, VIRTUAL, roots


def validate_target(service, body):
    if service not in ("open_cover", "close_cover", "stop_cover", "set_cover_position"):
        raise LocalError("Unsupported virtual service")
    expected = {"entity_id", "position"} if service == "set_cover_position" else {"entity_id"}
    if set(body) != expected:
        raise LocalError("Only explicit virtual entity targets are allowed; no area/device/indirect targets")
    ids = body["entity_id"]
    ids = [ids] if isinstance(ids, str) else ids
    if not isinstance(ids, list) or not ids or any(not isinstance(entity, str) or entity not in VIRTUAL for entity in ids):
        raise LocalError("Unknown, mixed or all-cover targets are prohibited")
    if service == "set_cover_position" and (type(body["position"]) is not int or not 0 <= body["position"] <= 100):
        raise LocalError("Position must be an integer between 0 and 100")


def verified_states(env, token):
    code = 'from pathlib import Path; print(Path("/config/.storage/core.entity_registry").read_text())'
    registry = json.loads(env.compose("exec", "-T", "homeassistant", "python", "-c", code, capture=True).stdout)
    states = env.request("/api/states", token=token)
    covers = {s["entity_id"]: s for s in states if s["entity_id"].startswith("cover.")}
    entries = {s["entity_id"]: s for s in registry["data"]["entities"] if s["entity_id"] in VIRTUAL}
    if set(covers) != set(VIRTUAL) or set(entries) != set(VIRTUAL) or any(
            covers[entity]["attributes"].get("ui_test_only") is not True or
            entries[entity].get("platform") != "codex_ui_test" for entity in VIRTUAL):
        raise LocalError("All covers must be the three registry-verified virtual fixtures")
    return covers


def call(env, token, service, body):
    validate_target(service, body)  # Rejected payloads never reach the API.
    env.docker_audit()
    verified_states(env, token)
    return env.request("/api/services/cover/" + service, body, token)


def wait_for(env, token, entity, predicate, timeout=8):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        state = env.request("/api/states/" + entity, token=token)
        if predicate(state):
            return state
        time.sleep(0.1)
    raise LocalError("Virtual cover did not reach expected state")


def exercise(env):
    token = env.token()
    before = verified_states(env, token)
    entity = VIRTUAL[0]
    position = lambda state: state["attributes"]["current_position"]
    initial = position(before[entity])
    try:
        call(env, token, "set_cover_position", {"entity_id": entity, "position": 50})
        wait_for(env, token, entity, lambda s: position(s) == 50 and s["state"] == "open")
        call(env, token, "open_cover", {"entity_id": entity})
        wait_for(env, token, entity, lambda s: position(s) == 100 and s["state"] == "open")
        call(env, token, "close_cover", {"entity_id": entity})
        wait_for(env, token, entity, lambda s: 0 < position(s) < 100 and s["state"] == "closing")
        call(env, token, "stop_cover", {"entity_id": entity})
        stopped = env.request("/api/states/" + entity, token=token)
        time.sleep(0.4)
        assert position(env.request("/api/states/" + entity, token=token)) == position(stopped), "Stop holds position"
        assert stopped["state"] == "open", "Stopped partial cover is open"
        call(env, token, "close_cover", {"entity_id": entity})
        wait_for(env, token, entity, lambda s: position(s) == 0 and s["state"] == "closed")
        call(env, token, "open_cover", {"entity_id": entity})
        call(env, token, "set_cover_position", {"entity_id": entity, "position": 37})
        wait_for(env, token, entity, lambda s: position(s) == 37 and s["state"] == "open")
        print(json.dumps({"virtual_motion": "passed", "project": env.project,
                          "checks": ["position", "open", "close", "stop", "replacement command"]}))
    finally:
        call(env, token, "set_cover_position", {"entity_id": entity, "position": initial})
        wait_for(env, token, entity, lambda s: position(s) == initial and s["state"] not in ("opening", "closing"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("dev", "test"))
    parser.add_argument("agent", nargs="?")
    args = parser.parse_args()
    if args.mode == "test" and args.agent:
        raise LocalError("Test does not accept an agent")
    env = Environment(*roots(), args.mode, args.agent)
    with env.lock():
        env.load()
        env.assert_no_review()
        env.docker_audit()
        env.state["url"] = env.url()
        if not env.state["url"]:
            raise LocalError("Instance is stopped")
        exercise(env)


if __name__ == "__main__":
    try:
        main()
    except (LocalError, AssertionError) as exc:
        raise SystemExit(f"Error: {exc}")
