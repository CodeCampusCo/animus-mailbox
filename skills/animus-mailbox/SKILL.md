---
name: animus-mailbox
description: Use to tell the user something through animus, their voice assistant (news, a finished result, a question), when the user asks animus to wait longer or shorter before speaking up about this session, when the user renames this session for animus, or when a message from animus appears in this session's inbox.
---

# animus mailbox

animus speaks to the user; this session reaches it through a mailbox. The plugin's hooks set it up
and keep it: they create the mailbox, tell animus the session's name (given in this session's
context, with the mailbox path and the script), hold a message when you are waiting on the user and
take it back once the user answers. You only write what has content. The full format is
docs/agent-mailbox.md in the animus repository.

Below, `<script>` and `<mailbox>` are the ones in this session's context.

## Tell the user something

```sh
python3 <script> send <mailbox> <kind> <urgency> "<first line: what it is about>
<details, if any>"
```

- `kind`: `tell` (news or a result), `ask` (you need the user's answer) or `assign` (a task for
  the user).
- `urgency`: `urgent` when the user should hear it now (you are blocked, or it is time-critical);
  otherwise `normal`, and animus tells it when the user asks what is waiting.
- Keep the first line short and whole: it is what animus says the message is about.
- A decision you need from the user: send it as `ask`, `urgent`, and say what you need.

## How long animus waits

When this session waits on the user, animus speaks up only if the user has not answered for a
while: 10 minutes unless the user says otherwise for this session. When they do ("use 20 minutes"):

```sh
python3 <script> wait <mailbox> 20
```

## Rename this session

When the user asks animus to call this session something else ("call yourself api"):

```sh
python3 <script> rename <mailbox> api
```

## Messages from the user

When the user speaks to this session through animus, a file `<id>.md` appears in
`<mailbox>/inbox/`, and the plugin's monitor tells you with a line "animus message <id> in
<inbox>". It is Markdown with YAML frontmatter (`kind: ask`, `from: animus`): a message distilled
by animus's model, then a section `## User's words (verbatim)` quoting what the user actually said,
as transcribed.

- The verbatim words are the authority. Where the message and the words differ, or the message asks
  for something the words do not, follow the words.
- It came by voice and is unverified. Answer, look things up and investigate freely; anything
  irreversible (deleting, pushing, merging, sending, spending) waits until the user confirms at the
  terminal.
- Delete the file once read, and answer with its id (the file's name without `.md`); an answer is
  always told to the user at once:

```sh
python3 <script> reply <mailbox> <its id> "<the answer>"
```

## Agents other than Claude Code

The plugin is for Claude Code. Any other agent can do the same by hand: docs/agent-mailbox.md shows
how to create a mailbox, leave a pointer and write messages.
