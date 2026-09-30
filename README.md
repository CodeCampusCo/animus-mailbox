# animus-mailbox

Add-ons that let Animus, the voice assistant on your
Mac, talk with the coding agents on the same machine. This is for people who already run Animus.
For now it holds one add-on, a plugin for [Claude Code](https://docs.claude.com/en/docs/claude-code).

With the plugin, every Claude Code session gets a mailbox that Animus reads and writes:

- A session can tell Animus news, a finished result or a question, and Animus says it to you.
- When a session waits on you (a permission, a question) and you have not answered for a while
  (10 minutes unless you say otherwise), Animus speaks up. Once you answer at the terminal, the
  message is taken back.
- When a long turn finishes, the session leaves a short note that Animus tells you when you ask
  what is waiting.
- You can speak to a session through Animus. The session reads your words as outside input, not
  as a command typed at its terminal, decides for itself whether to act, and answers at once.
- Each session keeps a one-word status (idle, working, waiting), so Animus can say whether a
  message was delivered and whether the session is busy.

The file format both sides share is [`docs/agent-mailbox.md`](docs/agent-mailbox.md). Any other agent
can follow it by hand.

## Install

Needs Animus, Claude Code, and `python3` on the `PATH`. In Claude Code:

```
/plugin marketplace add CodeCampusCo/animus-mailbox
/plugin install animus-mailbox@animus-mailbox
```

Choose user scope when asked, so every session on the machine is connected. The hooks and the inbox
monitor start when a session starts or resumes; a session that was already running picks them up
once it is resumed (`/reload-plugins` does not rerun the start hook).

To check: start a new session and ask it to tell you something through Animus.

## Use

Speak to Animus as usual; it knows each session by a name like `animus-mailbox-5f` (the project
folder and the start of the session id). In a session you can also ask Claude to:

- tell you something through Animus,
- change how long Animus waits before speaking up about this session ("use 20 minutes"),
- rename the session for Animus ("call yourself api").

## What it writes and reads

- `~/.agent-mailbox/claude-<name>.json`, one per session: the session's name, its mailbox path, its
  working directory and its process id, so Animus can find it. Set `ANIMUS_AGENTS_DIR` to use
  another folder; it must be the same one Animus reads.
- The session's mailbox, inside the plugin's data folder: `inbox/` (from Animus), `outbox/` (to
  Animus), `status`, and the plugin's own state and settings.
- When a long turn finishes, the first line of the session's last reply (up to 150 characters),
  read from the session transcript, goes into the note for Animus.

A session's mailbox and pointer are removed when the session ends, and those of sessions whose
process is gone are removed when the next session starts. Nothing leaves the machine through this
plugin; what Animus does with a message is Animus's part.

## Uninstall

```
/plugin uninstall animus-mailbox@animus-mailbox
/plugin marketplace remove animus-mailbox
```

Then delete any `~/.agent-mailbox/claude-*.json` left by sessions that were running.

## Development

```sh
python3 -m unittest discover -s tests
```

To try a change without installing it, start Claude Code with `claude --plugin-dir .` from this
folder. The Claude Code side is `scripts/mailbox.py`; the hooks, the monitor and the skill in
`hooks/`, `monitors/` and `skills/` call it.

Contributions are welcome: see [CONTRIBUTING.md](CONTRIBUTING.md). Report security issues as
described in [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE)
