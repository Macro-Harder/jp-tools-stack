#!/usr/bin/env python3
"""tq: a small serializing queue for heavy test suite runs.

Only one queued job runs at a time on this machine. Jobs wait as
ticket files in a state directory; the runner holds an flock for the
whole run, so a dead runner can never wedge the queue.

Standing rule (Captain JP, 2026-11-15): Citeline is the most
important build, and its testing always goes to the front of the
line. A waiting Citeline job dequeues before every waiting
non-Citeline job. A job already running is never preempted.
Within a class, order is first in, first out.

Usage:
  tq run [--project NAME] -- <command...>
  tq status
"""

import fcntl
import json
import os
import subprocess
import sys
import time

TOOL_HOME = os.path.dirname(os.path.abspath(__file__))
POLL_SECONDS = 0.1


def state_dir():
    return os.environ.get("TQ_STATE_DIR") or os.path.join(TOOL_HOME, "state")


def queue_dir(sd):
    return os.path.join(sd, "queue")


def ensure_dirs(sd):
    os.makedirs(queue_dir(sd), exist_ok=True)


def is_citeline(project):
    return "citeline" in (project or "").lower()


def sort_key(ticket):
    """Dequeue order: Citeline class first, then arrival sequence."""
    return (0 if ticket.get("citeline") else 1, ticket.get("seq", 0))


def pid_alive(pid):
    if not pid:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def next_seq(sd):
    """Hand out arrival numbers under a short flock on a counter file."""
    path = os.path.join(sd, "counter")
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        raw = os.read(fd, 64).decode("ascii", "ignore").strip()
        n = int(raw) if raw.isdigit() else 0
        n += 1
        os.lseek(fd, 0, os.SEEK_SET)
        os.ftruncate(fd, 0)
        os.write(fd, str(n).encode("ascii"))
        os.fsync(fd)
        return n
    finally:
        os.close(fd)


def write_json_atomic(path, data):
    tmp = "%s.tmp.%d" % (path, os.getpid())
    with open(tmp, "w") as f:
        json.dump(data, f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def read_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def list_tickets(sd):
    """Live waiting tickets, sorted in dequeue order.

    Tickets whose submitting process is gone are stale: they are
    removed and never counted.
    """
    tickets = []
    qd = queue_dir(sd)
    try:
        names = os.listdir(qd)
    except OSError:
        return tickets
    for name in names:
        if not name.endswith(".json"):
            continue
        path = os.path.join(qd, name)
        ticket = read_json(path)
        if ticket is None:
            continue
        if not pid_alive(ticket.get("pid")):
            try:
                os.unlink(path)
            except OSError:
                pass
            continue
        tickets.append(ticket)
    tickets.sort(key=sort_key)
    return tickets


def running_ticket(sd):
    ticket = read_json(os.path.join(sd, "running.json"))
    if ticket is None:
        return None
    if not pid_alive(ticket.get("pid")):
        return None
    return ticket


def describe(ticket):
    cmd = " ".join(ticket.get("command") or [])
    return "project=%s pid=%s command=%s" % (
        ticket.get("project") or "(unnamed)",
        ticket.get("pid"),
        cmd,
    )


def cmd_status(argv):
    sd = state_dir()
    ensure_dirs(sd)
    running = running_ticket(sd)
    if running is not None:
        print("Running: " + describe(running))
    else:
        print("Running: none")
    waiting = [t for t in list_tickets(sd)
               if running is None or t.get("id") != running.get("id")]
    if waiting:
        print("Waiting, in the order they will run:")
        for i, ticket in enumerate(waiting, 1):
            print("  %d. %s" % (i, describe(ticket)))
    else:
        print("Waiting: none")
    return 0


def cmd_run(project, command):
    sd = state_dir()
    ensure_dirs(sd)
    ticket_id = "%d-%d" % (int(time.time() * 1000), os.getpid())
    ticket = {
        "id": ticket_id,
        "seq": next_seq(sd),
        "pid": os.getpid(),
        "project": project or "",
        "citeline": is_citeline(project),
        "command": command,
        "submitted": time.time(),
    }
    ticket_path = os.path.join(queue_dir(sd), ticket_id + ".json")
    write_json_atomic(ticket_path, ticket)

    lock_path = os.path.join(sd, "runner.lock")
    running_path = os.path.join(sd, "running.json")
    try:
        while True:
            fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o644)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                os.close(fd)
                time.sleep(POLL_SECONDS)
                continue
            # We hold the runner lock. Only run if we are at the head
            # of the queue; otherwise hand the lock back and wait.
            tickets = list_tickets(sd)
            head = tickets[0] if tickets else None
            if head is not None and head.get("id") != ticket_id:
                fcntl.flock(fd, fcntl.LOCK_UN)
                os.close(fd)
                time.sleep(POLL_SECONDS)
                continue
            try:
                write_json_atomic(running_path, ticket)
                try:
                    os.unlink(ticket_path)
                except OSError:
                    pass
                rc = subprocess.run(command).returncode
            finally:
                try:
                    os.unlink(running_path)
                except OSError:
                    pass
                fcntl.flock(fd, fcntl.LOCK_UN)
                os.close(fd)
            if rc < 0:
                return 128 + (-rc)
            return rc
    finally:
        try:
            os.unlink(ticket_path)
        except OSError:
            pass


def parse_run_args(argv):
    """Split: [--project NAME] -- <command...>"""
    project = None
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--":
            return project, argv[i + 1:]
        if arg == "--project" and i + 1 < len(argv):
            project = argv[i + 1]
            i += 2
            continue
        if arg.startswith("--project="):
            project = arg.split("=", 1)[1]
            i += 1
            continue
        return project, argv[i:]
    return project, []


def main(argv):
    if len(argv) < 2:
        print(__doc__.strip())
        return 2
    if argv[1] == "status":
        return cmd_status(argv[2:])
    if argv[1] == "run":
        project, command = parse_run_args(argv[2:])
        if not command:
            print("tq run: no command given", file=sys.stderr)
            return 2
        return cmd_run(project, command)
    print("tq: unknown command %r (want: run, status)" % argv[1],
          file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
