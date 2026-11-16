# tq, the testing queue

A small local tool that serializes heavy test suite runs on this
machine. The VM has a 1.5 CPU share and tight memory, so two builds
running their full suites at once mostly make each other slower.
tq makes them take turns: only one queued job runs at a time,
machine wide.

## How a build uses it

Wrap the suite command:

```
~/workspace/tools/test-queue/tq run --project citeline -- python3 -m pytest
```

`tq run` submits the job, waits until its turn comes, runs the
command, and exits with the command's own exit code, so scripts and
coordinators can treat it exactly like running the suite directly.
The `--project` name is what the priority rule reads; pass the
build's own project name.

Check the line at any time:

```
~/workspace/tools/test-queue/tq status
```

It prints the running job, then the waiting jobs in the order they
will run.

## The Citeline rule

Standing rule from Captain JP (2026-11-15): Citeline is the most
important build, and its testing always goes to the front of the
line. Any waiting job whose project name contains "citeline"
(case-insensitive) dequeues before every waiting non-Citeline job,
no matter when it arrived. Within each class the order is first
in, first out. A job that is already running is never preempted;
the rule only reorders the wait.

## How it works

- State lives in `state/` beside the tool (override with the
  `TQ_STATE_DIR` environment variable, which the tests use).
- Each waiting job is a ticket file in `state/queue/`, carrying an
  arrival number handed out under a short lock.
- The runner holds an `flock` on `state/runner.lock` for the whole
  run. The lock dies with the process, and tickets left behind by
  dead processes are recognised by pid and dropped, so a crashed
  build can never wedge the queue.

## Files

- `tq.py`: the tool. Python standard library only.
- `tq`: a thin executable wrapper for `tq.py`.
- `test_tq.py`: the test suite, written before the tool.
  Run it with `python3 -m unittest test_tq -v`.
- `PROOF.md`: a recorded live run showing the priority rule,
  the serialization, and exit code propagation.
