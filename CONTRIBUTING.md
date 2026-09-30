# Contributing

## Scope

Contributions to animus-mailbox are welcome: fixes and improvements to the Claude Code plugin, an
add-on for another agent, and changes to [`docs/agent-mailbox.md`](docs/agent-mailbox.md). For
anything larger than a fix, open an issue first.

## How changes land

1. Fork (or branch), make the change, and open a pull request against `main`.
2. CI must pass: the unit tests on Linux and macOS, and `claude plugin validate --strict` on the
   marketplace, plugin and skill manifests.
3. Every review conversation must be resolved before the pull request can merge.

## Working on it

```sh
python3 -m unittest discover -s tests
claude plugin validate --strict .
claude --plugin-dir .
```

The last line starts a Claude Code session with the plugin from this folder instead of the
installed one.

- `scripts/mailbox.py` does all the work; `hooks/hooks.json`, `monitors/monitors.json` and the
  skill in `skills/animus-mailbox/` call it. It uses the Python standard library only; keep it so.
- A hook must never fail the session: errors go to stderr and the exit code stays 0.
- Add or update tests in `tests/test_mailbox.py` with any change to the script. Tests set
  `ANIMUS_AGENTS_DIR` to a temporary folder, so they never touch the real `~/.agent-mailbox`.
- `tests/test_manifests.py` checks what `claude plugin validate` does not: every JSON manifest
  parses, and each hook and monitor command runs a subcommand `scripts/mailbox.py` has.
- Bump `version` in `.claude-plugin/plugin.json` when a change should reach installed copies.

## Commits

Short subjects, in the imperative or as a statement of the result. Use the body to explain why; if
a measurement drove the change, put the number in the message.

## Conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md).
