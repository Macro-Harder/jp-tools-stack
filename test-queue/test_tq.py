#!/usr/bin/env python3
"""Tests for tq, the serializing test queue.

Run with: python3 -m unittest test_tq -v
Integration tests use a throwaway state directory via TQ_STATE_DIR so
they never touch the real queue.
"""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TQ_PY = os.path.join(HERE, "tq.py")

spec = importlib.util.spec_from_file_location("tq", TQ_PY)
tq = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tq)


def run_tq(state_dir, argv, **kwargs):
    env = dict(os.environ)
    env["TQ_STATE_DIR"] = state_dir
    return subprocess.run(
        [sys.executable, TQ_PY] + argv,
        env=env,
        capture_output=True,
        text=True,
        **kwargs,
    )


def spawn_tq(state_dir, argv):
    env = dict(os.environ)
    env["TQ_STATE_DIR"] = state_dir
    return subprocess.Popen(
        [sys.executable, TQ_PY] + argv,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


JOB_SCRIPT = """\
import sys, time
name, logfile, delay = sys.argv[1], sys.argv[2], float(sys.argv[3])
with open(logfile, "a") as f:
    f.write("%s start %.3f\\n" % (name, time.time()))
time.sleep(delay)
with open(logfile, "a") as f:
    f.write("%s end %.3f\\n" % (name, time.time()))
"""


class TestPriorityRules(unittest.TestCase):
    def test_citeline_detection(self):
        self.assertTrue(tq.is_citeline("citeline"))
        self.assertTrue(tq.is_citeline("Citeline"))
        self.assertTrue(tq.is_citeline("CITELINE-build"))
        self.assertTrue(tq.is_citeline("the citeline redo"))
        self.assertFalse(tq.is_citeline("crucible"))
        self.assertFalse(tq.is_citeline(""))
        self.assertFalse(tq.is_citeline(None))

    def test_dequeue_order_citeline_first_then_fifo(self):
        tickets = [
            {"id": "a", "seq": 1, "citeline": False},
            {"id": "b", "seq": 2, "citeline": False},
            {"id": "c", "seq": 3, "citeline": True},
            {"id": "d", "seq": 4, "citeline": True},
            {"id": "e", "seq": 5, "citeline": False},
        ]
        ordered = [t["id"] for t in sorted(tickets, key=tq.sort_key)]
        self.assertEqual(ordered, ["c", "d", "a", "b", "e"])


class TestExitCodes(unittest.TestCase):
    def test_exit_code_propagates(self):
        with tempfile.TemporaryDirectory() as td:
            state = os.path.join(td, "state")
            result = run_tq(
                state,
                ["run", "--project", "demo", "--",
                 sys.executable, "-c", "import sys; sys.exit(3)"],
            )
            self.assertEqual(result.returncode, 3)

    def test_zero_exit_code(self):
        with tempfile.TemporaryDirectory() as td:
            state = os.path.join(td, "state")
            result = run_tq(state, ["run", "--", "true"])
            self.assertEqual(result.returncode, 0)


class TestQueueBehaviour(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.state = os.path.join(self.td.name, "state")
        self.log = os.path.join(self.td.name, "jobs.log")
        self.job = os.path.join(self.td.name, "job.py")
        with open(self.job, "w") as f:
            f.write(JOB_SCRIPT)

    def tearDown(self):
        self.td.cleanup()

    def job_argv(self, project, name, delay):
        return ["run", "--project", project, "--",
                sys.executable, self.job, name, self.log, str(delay)]

    def wait_for_running(self, timeout=10.0):
        running = os.path.join(self.state, "running.json")
        deadline = time.time() + timeout
        while time.time() < deadline:
            if os.path.exists(running):
                return True
            time.sleep(0.05)
        return False

    def test_citeline_jumps_waiting_queue_and_nothing_overlaps(self):
        blocker = spawn_tq(self.state, self.job_argv("setup", "blocker", 2.0))
        self.assertTrue(self.wait_for_running(), "blocker never started")
        procs = []
        # Arrival order: other-a, other-b, then citeline last.
        for project, name in [("crucible", "other-a"),
                              ("metrics", "other-b"),
                              ("citeline", "citeline-job")]:
            procs.append(spawn_tq(self.state, self.job_argv(project, name, 0.3)))
            time.sleep(0.25)
        blocker.wait(timeout=30)
        for p in procs:
            p.wait(timeout=30)
            self.assertEqual(p.returncode, 0)

        events = []
        with open(self.log) as f:
            for line in f:
                name, kind, ts = line.split()
                events.append((name, kind, float(ts)))
        starts = [n for (n, k, _t) in events if k == "start"]
        self.assertEqual(
            starts,
            ["blocker", "citeline-job", "other-a", "other-b"],
            "run order was %s" % (starts,),
        )
        spans = {}
        for name, kind, ts in events:
            spans.setdefault(name, {})[kind] = ts
        ordered = sorted(spans.items(), key=lambda kv: kv[1]["start"])
        for (n1, s1), (n2, s2) in zip(ordered, ordered[1:]):
            self.assertLessEqual(
                s1["end"], s2["start"],
                "%s overlapped %s" % (n1, n2),
            )

    def test_status_lists_running_then_waiting_in_run_order(self):
        blocker = spawn_tq(self.state, self.job_argv("setup", "blocker", 2.0))
        self.assertTrue(self.wait_for_running(), "blocker never started")
        waiting = []
        for project, name in [("crucible", "other-a"),
                              ("citeline", "citeline-job")]:
            waiting.append(spawn_tq(self.state, self.job_argv(project, name, 0.1)))
            time.sleep(0.25)
        time.sleep(0.3)
        result = run_tq(self.state, ["status"])
        blocker.wait(timeout=30)
        for p in waiting:
            p.wait(timeout=30)
        out = result.stdout
        self.assertIn("blocker", out)
        self.assertLess(out.index("citeline-job"), out.index("other-a"),
                        "status did not list citeline ahead of other-a:\n%s" % out)

    def test_stale_ticket_from_dead_process_does_not_wedge_queue(self):
        os.makedirs(os.path.join(self.state, "queue"))
        dead = subprocess.Popen([sys.executable, "-c", "pass"])
        dead.wait()
        stale = {
            "id": "stale-1",
            "seq": 1,
            "pid": dead.pid,
            "project": "ghost",
            "citeline": False,
            "command": ["true"],
            "submitted": time.time(),
        }
        with open(os.path.join(self.state, "queue", "stale-1.json"), "w") as f:
            json.dump(stale, f)
        result = run_tq(
            self.state,
            ["run", "--project", "demo", "--", "true"],
            timeout=15,
        )
        self.assertEqual(result.returncode, 0)
        status = run_tq(self.state, ["status"])
        self.assertNotIn("ghost", status.stdout)


if __name__ == "__main__":
    unittest.main()
