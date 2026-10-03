"""Reject dangerous requests before network access, independent of fixture motion."""
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
SPEC = importlib.util.spec_from_file_location("ha_virtual_check", Path(__file__).resolve().parents[2] / "scripts/ha_virtual_check.py")
check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check)


class GuardTests(unittest.TestCase):
    def test_unknown_mixed_and_indirect_targets_never_reach_network(self):
        bad = [{"entity_id": "all"}, {"entity_id": "cover.real"},
               {"entity_id": [check.VIRTUAL[0], "cover.real"]}, {"entity_id": []},
               {"entity_id": check.VIRTUAL[0], "area_id": "living"},
               {"device_id": "device"}, {"entity_id": check.VIRTUAL[0], "target": "all"}]
        for body in bad:
            env = Mock()
            with self.subTest(body=body), self.assertRaises(check.LocalError):
                check.call(env, "unused", "open_cover", body)
            env.request.assert_not_called()
            env.compose.assert_not_called()

    def test_positions_and_service_names_are_restricted(self):
        for value in (-1, 101, "50", True):
            with self.subTest(value=value), self.assertRaises(check.LocalError):
                check.validate_target("set_cover_position", {"entity_id": check.VIRTUAL[0], "position": value})
        with self.assertRaises(check.LocalError):
            check.validate_target("toggle", {"entity_id": check.VIRTUAL[0]})
        check.validate_target("set_cover_position", {"entity_id": check.VIRTUAL[0], "position": 50})


if __name__ == "__main__":
    unittest.main()
