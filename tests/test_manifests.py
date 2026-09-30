"""The wiring `claude plugin validate` does not check: every manifest parses, and each hook and monitor
command runs a subcommand scripts/mailbox.py dispatches on."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "mailbox.py"
CALL = re.compile(r'"\$\{CLAUDE_PLUGIN_ROOT\}/(\S+?)" (\S+)')


def commands(node):
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "command":
                yield value
            else:
                yield from commands(value)
    elif isinstance(node, list):
        for value in node:
            yield from commands(value)


class Manifests(unittest.TestCase):
    def test_every_manifest_parses(self):
        found = [p for p in ROOT.rglob("*.json") if ".git" not in p.parts]
        self.assertGreaterEqual(len(found), 4)
        for path in found:
            with self.subTest(path=path.relative_to(ROOT)):
                json.loads(path.read_text(encoding="utf-8"))

    def test_hooks_and_monitors_run_subcommands_the_script_has(self):
        source = SCRIPT.read_text(encoding="utf-8")
        dispatched = set(re.findall(r'command == "([\w-]+)"', source))
        self.assertIn("session-start", dispatched)
        for manifest in ("hooks/hooks.json", "monitors/monitors.json"):
            for command in commands(json.loads((ROOT / manifest).read_text(encoding="utf-8"))):
                with self.subTest(manifest=manifest, command=command):
                    match = CALL.search(command)
                    self.assertIsNotNone(match, "runs no script from the plugin")
                    self.assertTrue((ROOT / match[1]).is_file(), match[1])
                    self.assertIn(match[2], dispatched)


if __name__ == "__main__":
    unittest.main()
