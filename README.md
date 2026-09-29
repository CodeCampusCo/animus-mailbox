# animus-mailbox

A Claude Code plugin that connects every session to [animus](https://github.com/CodeCampusCo/animus),
the voice assistant on your Mac. A session can tell animus news, a finished result or a question;
while it waits on you, it asks animus to speak up; and animus can send it your words. The file
format both sides share is animus's `docs/agent-mailbox.md`.

## Install

The repository is private for now, so installing needs read access to it.

```
/plugin marketplace add CodeCampusCo/animus-mailbox
/plugin install animus-mailbox@animus-mailbox
```

Choose user scope when asked, so every session on the machine is connected. It needs `python3` on
the `PATH`. The hooks and the inbox monitor start when a session starts or resumes; a session that was already
running picks them up once it is resumed (`/reload-plugins` does not rerun the start hook).

## Development

```sh
python3 -m unittest discover -s tests
```
