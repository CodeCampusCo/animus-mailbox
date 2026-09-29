"""Run: python3 -m unittest discover -s tests"""
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "mailbox.py"


class Mailbox(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.registry, self.data = self.tmp / "registry", self.tmp / "data"
        self.env = dict(os.environ, ANIMUS_AGENTS_DIR=str(self.registry))

    def run_hook(self, command, hook, *extra):
        out = subprocess.run([sys.executable, str(SCRIPT), command, str(self.data), *extra],
                             input=json.dumps(hook), capture_output=True, text=True, env=self.env)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stderr, "")
        return out.stdout

    def tool(self, *args, stdin=""):
        return subprocess.run([sys.executable, str(SCRIPT), *args], input=stdin, capture_output=True, text=True, env=self.env)

    def start(self, session="3fa9c1d2-aaaa", cwd="/work/animus"):
        out = self.run_hook("session-start", {"session_id": session, "cwd": cwd})
        return Path(self.data / "mailbox" / session), json.loads(out)

    def outbox(self, mailbox):
        return sorted(p.name for p in (mailbox / "outbox").iterdir() if not p.name.startswith("."))

    def header(self, mailbox, name):
        text = (mailbox / "outbox" / name).read_text()
        self.assertTrue(name.endswith(".md") and text.startswith("---\n"))
        head = text[4:].split("\n---\n", 1)[0]
        return dict(line.split(": ", 1) for line in head.splitlines())

    def test_start_names_the_session_and_points_animus_at_it(self):
        mailbox, out = self.start()
        pointer = json.loads((self.registry / "claude-animus-3f.json").read_text())
        self.assertEqual(pointer["mailbox"], str(mailbox))
        self.assertEqual((pointer["v"], pointer["agent"], pointer["session"], pointer["cwd"]), (1, "claude", "animus-3f", "/work/animus"))
        self.assertIsInstance(pointer["pid"], int)
        self.assertTrue((mailbox / "inbox").is_dir() and (mailbox / "outbox").is_dir())
        self.assertIn('knows this session as "animus-3f"', out["hookSpecificOutput"]["additionalContext"])
        self.assertEqual(oct(self.registry.stat().st_mode & 0o777), "0o700")

    def test_a_clash_takes_more_of_the_id(self):
        self.start("3fa9c1d2-aaaa")
        self.start("3fb00000-bbbb")
        self.assertTrue((self.registry / "claude-animus-3fb.json").exists())
        self.start("3fa9c1d2-aaaa")   # resume keeps its name
        self.assertEqual(json.loads((self.registry / "claude-animus-3f.json").read_text())["session"], "animus-3f")

    def test_waiting_is_held_once_and_taken_back_when_answered(self):
        mailbox, _ = self.start()
        hook = {"session_id": "3fa9c1d2-aaaa", "message": "Claude needs your permission to use Bash"}
        self.run_hook("waiting", hook, "permission_prompt")
        self.run_hook("waiting", hook, "permission_prompt")
        [held] = self.outbox(mailbox)
        h = self.header(mailbox, held)
        self.assertEqual((h["kind"], h["urgency"]), ("tell", "urgent"))
        after = time.mktime(time.strptime(h["after"], "%Y-%m-%dT%H:%M:%SZ")) - time.timezone
        self.assertAlmostEqual(after - time.time(), 600, delta=5)
        self.run_hook("tool-done", {"session_id": "3fa9c1d2-aaaa"})
        [withdraw] = self.outbox(mailbox)
        self.assertEqual(self.header(mailbox, withdraw)["kind"], "withdraw")
        self.assertEqual(self.header(mailbox, withdraw)["re"], held.removesuffix(".md"))

    def test_a_turn_that_ends_means_the_prompt_was_answered(self):
        mailbox, _ = self.start()
        self.run_hook("prompt", {"session_id": "3fa9c1d2-aaaa"})
        self.run_hook("waiting", {"session_id": "3fa9c1d2-aaaa"}, "permission_prompt")
        self.run_hook("stop", {"session_id": "3fa9c1d2-aaaa"})
        self.assertEqual([self.header(mailbox, n)["kind"] for n in self.outbox(mailbox)], ["withdraw"])

    def test_a_long_turn_that_finishes_leaves_a_normal_message(self):
        mailbox, _ = self.start()
        state = json.loads((mailbox / "state.json").read_text())
        state["turn_start"] = time.time() - 700
        (mailbox / "state.json").write_text(json.dumps(state))
        transcript = self.tmp / "t.jsonl"
        transcript.write_text(json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "Tests pass.\nDetails."}]}}) + "\n")
        self.run_hook("stop", {"session_id": "3fa9c1d2-aaaa", "transcript_path": str(transcript)})
        [done] = self.outbox(mailbox)
        self.assertEqual((self.header(mailbox, done)["kind"], self.header(mailbox, done)["urgency"]), ("tell", "normal"))
        self.assertIn("animus-3f finished: Tests pass.", (mailbox / "outbox" / done).read_text())

    def test_a_short_turn_says_nothing(self):
        mailbox, _ = self.start()
        self.run_hook("prompt", {"session_id": "3fa9c1d2-aaaa"})
        self.run_hook("stop", {"session_id": "3fa9c1d2-aaaa"})
        self.assertEqual(self.outbox(mailbox), [])

    def test_the_wait_is_per_session(self):
        mailbox, _ = self.start()
        self.assertEqual(self.tool("wait", str(mailbox), "20").returncode, 0)
        self.run_hook("waiting", {"session_id": "3fa9c1d2-aaaa"}, "ask")
        h = self.header(mailbox, self.outbox(mailbox)[0])
        after = time.mktime(time.strptime(h["after"], "%Y-%m-%dT%H:%M:%SZ")) - time.timezone
        self.assertAlmostEqual(after - time.time(), 1200, delta=5)

    def test_send_and_rename(self):
        mailbox, _ = self.start()
        sent = self.tool("send", str(mailbox), "normal", "PR #18 is clean").stdout.strip()
        h = self.header(mailbox, f"{sent}.md")
        self.assertEqual((h["kind"], h["urgency"]), ("tell", "normal"))
        self.assertNotIn("re", h)
        self.assertTrue((mailbox / "outbox" / f"{sent}.md").read_text().endswith("\n\nPR #18 is clean\n"))
        self.assertEqual(self.tool("rename", str(mailbox), "API").returncode, 0)
        self.assertTrue((self.registry / "claude-api.json").exists())
        self.assertFalse((self.registry / "claude-animus-3f.json").exists())

    def test_end_and_sweep_clean_up(self):
        mailbox, _ = self.start()
        self.run_hook("session-end", {"session_id": "3fa9c1d2-aaaa"})
        self.assertFalse(mailbox.exists())
        self.assertFalse((self.registry / "claude-animus-3f.json").exists())
        dead, _ = self.start("deadbeef-0000")
        state = json.loads((dead / "state.json").read_text())
        state["pid"] = 999999
        (dead / "state.json").write_text(json.dumps(state))
        self.start("3fa9c1d2-aaaa")
        self.assertFalse(dead.exists())
        self.assertFalse((self.registry / "claude-animus-de.json").exists())

    def watch(self, session, owner):
        env = dict(self.env, CLAUDE_CODE_SESSION_ID=session, CLAUDE_PID=str(owner.pid))
        proc = subprocess.Popen([sys.executable, str(SCRIPT), "watch", str(self.data)], stdout=subprocess.PIPE, text=True, env=env)
        self.addCleanup(proc.kill)
        return proc

    def deliver(self, mailbox, name):
        (mailbox / "inbox" / ".tmp").write_text("---\nv: 1\nkind: tell\n---\n\nhello\n")
        (mailbox / "inbox" / ".tmp").rename(mailbox / "inbox" / f"{name}.md")


    def announced(self, proc):
        """What the monitor printed for one message: everything up to the answer's heredoc terminator."""
        lines = []
        while not lines or lines[-1] != "EOF\n":
            lines.append(proc.stdout.readline())
            self.assertNotEqual(lines[-1], "", "the monitor stopped")
        return "".join(lines)

    def until(self, done, seconds=5):
        end = time.time() + seconds
        while not done() and time.time() < end:
            time.sleep(0.05)
        self.assertTrue(done())

    def arrive(self, mailbox, session="3fa9c1d2-aaaa", name="01J8ZQ4Y7KX2V9N3B5C6D7E8F9"):
        """One message the monitor announces and marks seen; the monitor then stops. Returns what it printed."""
        owner = subprocess.Popen(["sleep", "60"])
        self.addCleanup(owner.kill)
        proc = self.watch(session, owner)
        self.deliver(mailbox, name)
        text = self.announced(proc)
        self.until(lambda: (mailbox / "inbox" / f"{name}.seen.md").exists())
        proc.kill()
        proc.wait()
        return text

    def test_the_monitor_announces_each_message_file_once_and_marks_it_seen(self):
        mailbox, _ = self.start()
        owner = subprocess.Popen(["sleep", "60"])
        self.addCleanup(owner.kill)
        proc = self.watch("3fa9c1d2-aaaa", owner)
        inbox, first, second = mailbox / "inbox", "01J8ZQ4Y7KX2V9N3B5C6D7E8F9", "01J8ZQ4Y7KX2V9N3B5C6D7E8FA"
        self.deliver(mailbox, first)
        text = self.announced(proc)
        self.assertIn(str(inbox / f"{first}.seen.md"), text)
        self.assertNotIn("hello", text)
        self.assertIn("waiting for your answer", text)
        self.assertTrue(text.endswith(f"python3 {SCRIPT} send {mailbox} urgent <<'EOF'\n<your answer>\nEOF\n"))
        self.assertEqual((inbox / f"{first}.seen.md").read_text(), "---\nv: 1\nkind: tell\n---\n\nhello\n")
        (inbox / "note.txt").write_text("not a message")
        (inbox / "01J8ZQ4Y7KX2V9N3B5C6D7E8FB").write_text("no extension, not a message")
        self.deliver(mailbox, second)
        self.assertIn(str(inbox / f"{second}.seen.md"), self.announced(proc))
        self.assertEqual(sorted(os.listdir(inbox)), ["01J8ZQ4Y7KX2V9N3B5C6D7E8F9.seen.md", "01J8ZQ4Y7KX2V9N3B5C6D7E8FA.seen.md",
                                                     "01J8ZQ4Y7KX2V9N3B5C6D7E8FB", "note.txt"])
        owner.kill(); owner.wait()
        self.assertEqual(proc.wait(timeout=10), 0)
        self.assertEqual(proc.stdout.read(), "")

    def test_a_message_that_cannot_be_marked_does_not_stop_the_monitor(self):
        mailbox, _ = self.start()
        owner = subprocess.Popen(["sleep", "60"])
        self.addCleanup(owner.kill)
        (mailbox / "inbox" / "01J8ZQ4Y7KX2V9N3B5C6D7E8F0.seen.md").mkdir()
        (mailbox / "inbox" / "01J8ZQ4Y7KX2V9N3B5C6D7E8F0.seen.md" / "x").write_text("in the way")
        self.deliver(mailbox, "01J8ZQ4Y7KX2V9N3B5C6D7E8F0")
        proc = self.watch("3fa9c1d2-aaaa", owner)
        self.deliver(mailbox, "01J8ZQ4Y7KX2V9N3B5C6D7E8F9")
        self.assertIn("01J8ZQ4Y7KX2V9N3B5C6D7E8F9.seen.md", self.announced(proc))

    def test_after_a_clear_it_follows_the_mailbox_its_process_owns(self):
        mailbox, _ = self.start("9e000000-cccc")
        owner = subprocess.Popen(["sleep", "60"])
        self.addCleanup(owner.kill)
        state = json.loads((mailbox / "state.json").read_text())
        (mailbox / "state.json").write_text(json.dumps(dict(state, pid=owner.pid)))
        proc = self.watch("3fa9c1d2-aaaa", owner)
        self.deliver(mailbox, "01J8ZQ4Y7KX2V9N3B5C6D7E8F9")
        self.assertIn(f"send {mailbox} urgent", self.announced(proc))

    def test_a_dead_process_leaves_no_markers(self):
        dead, _ = self.start("deadbeef-0000")
        state = json.loads((dead / "state.json").read_text())
        (dead / "state.json").write_text(json.dumps(dict(state, pid=999999)))
        self.arrive(dead, session="deadbeef-0000")
        self.assertTrue((self.data / "marks" / "999999").exists())
        self.start()
        self.assertFalse((self.data / "marks" / "999999").exists())

    def test_send_keeps_its_urgency(self):
        mailbox, _ = self.start()
        self.deliver(mailbox, "01J8ZQ4Y7KX2V9N3B5C6D7E8F9")
        news = self.tool("send", str(mailbox), "normal", stdin="It is green.\n").stdout.strip()
        self.assertEqual(self.header(mailbox, f"{news}.md")["urgency"], "normal")

    def test_a_turn_that_would_leave_animus_unanswered_is_held_once(self):
        mailbox, _ = self.start()
        stop = {"session_id": "3fa9c1d2-aaaa", "stop_hook_active": False}
        self.assertEqual(self.run_hook("stop", stop), "")   # never got a message: never held
        self.run_hook("prompt", {"session_id": "3fa9c1d2-aaaa", "prompt": "earlier"})
        self.arrive(mailbox)
        self.run_hook("prompt", {"session_id": "3fa9c1d2-aaaa", "prompt": "<task-notification>animus</task-notification>"})
        self.run_hook("prompt", {"session_id": "3fa9c1d2-aaaa", "prompt": "<cross-session-message>hi"})
        state = json.loads((mailbox / "state.json").read_text())
        (mailbox / "state.json").write_text(json.dumps(dict(state, turn_start=time.time() - 700)))
        held = json.loads(self.run_hook("stop", stop))
        self.assertEqual(held["decision"], "block")
        self.assertIn("waiting for your answer", held["reason"])
        self.assertIn(f"python3 {SCRIPT} send {mailbox} urgent <<'EOF'", held["reason"])
        self.assertFalse(any("finished" in (mailbox / "outbox" / n).read_text() for n in self.outbox(mailbox)))
        self.assertEqual(self.run_hook("stop", dict(stop, stop_hook_active=True)), "")
        self.tool("send", str(mailbox), "urgent", stdin="It is green.\n")
        self.assertEqual(self.run_hook("stop", stop), "")
        self.arrive(mailbox, name="01J8ZQ4Y7KX2V9N3B5C6D7E8FA")
        self.run_hook("prompt", {"session_id": "3fa9c1d2-aaaa", "prompt": "leave it, I will look myself"})
        self.assertEqual(self.run_hook("stop", stop), "")   # the owner is at the terminal and decides

    def test_the_hooks_keep_a_one_word_status_for_animus(self):
        mailbox, _ = self.start()
        session = {"session_id": "3fa9c1d2-aaaa"}
        status = lambda: (mailbox / "status").read_text()
        self.assertEqual(status(), "idle")
        self.run_hook("prompt", dict(session, prompt="run the tests"))
        self.assertEqual(status(), "working")
        state = json.loads((mailbox / "state.json").read_text())   # a held "finished" message keeps waiting() from opening an episode
        (mailbox / "state.json").write_text(json.dumps(dict(state, episode="01J8ZQ4Y7KX2V9N3B5C6D7E8F0", episode_kind="finished")))
        self.run_hook("waiting", session, "permission_prompt")
        self.assertEqual(status(), "waiting")
        self.run_hook("tool-done", session)
        self.assertEqual(status(), "working")
        self.arrive(mailbox)
        self.run_hook("stop", session)   # held: animus has no answer yet, so the turn goes on
        self.assertEqual(status(), "working")
        self.run_hook("stop", dict(session, stop_hook_active=True))
        self.assertEqual(status(), "idle")

    def test_writers_of_one_file_at_once_all_succeed(self):
        sys.path.insert(0, str(SCRIPT.parent))
        import mailbox
        path, errors = self.tmp / "status", []

        def write():
            try:
                for _ in range(200):
                    mailbox.write_atomic(path, "working")
            except OSError as e:
                errors.append(e)
        threads = [threading.Thread(target=write) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        self.assertEqual(path.read_text(), "working")

    def test_the_wait_takes_only_a_sensible_number_of_minutes(self):
        mailbox, _ = self.start()
        for bad in ["inf", "nan", "1e308", "0", "0.5", "-5", "1441"]:
            self.assertNotEqual(self.tool("wait", str(mailbox), bad).returncode, 0, bad)
        self.assertEqual(self.tool("wait", str(mailbox), "1440").returncode, 0)
        self.run_hook("waiting", {"session_id": "3fa9c1d2-aaaa"}, "permission_prompt")
        self.assertIn("after", self.header(mailbox, self.outbox(mailbox)[0]))


if __name__ == "__main__":
    unittest.main()
