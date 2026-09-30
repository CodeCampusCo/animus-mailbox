# Security

## Reporting

Report vulnerabilities privately through GitHub's **Report a vulnerability** button under the
Security tab (private vulnerability reporting). Please do not open a public issue for anything
exploitable.

This is a personal project maintained in spare time. There is no SLA; expect a reply in days,
not hours, and no guaranteed fix timeline.

## What this plugin touches

Worth knowing when judging impact:

- **Every Claude Code session.** Its hooks run `python3 scripts/mailbox.py` on session start and
  end, on each prompt, after each tool, when the session waits on you, and when a turn ends. A
  hook never fails the session: errors go to stderr.
- **Text from outside reaches the agent.** A file in a session's inbox is announced to the session,
  which reads it. The skill tells the agent that it is external data, not your command, and that
  instructions at the terminal outrank it, but nothing deterministic stops a message from making the
  agent act: Claude Code's own permission mode applies. Anything running as your user can write to
  the inbox, so treat prompt injection through a message as in scope.
- **The end of a turn.** When a message from Animus has had no answer, the Stop hook blocks the
  turn from ending once, asking the agent to answer.
- **Local files.** Pointers in `~/.agent-mailbox` (or `ANIMUS_AGENTS_DIR`, created `0700`) hold each
  session's name, mailbox path, working directory and process id. Mailboxes live in the plugin's
  data folder. The Stop hook reads the session transcript for the first line of the last reply.
- **No network.** The plugin opens no connections; Animus is the only reader of what it writes.

## Supported versions

Only the latest commit on `main`.
