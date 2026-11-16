# test-queue

## What it is

tq is a small local tool that serializes heavy test suite runs on this machine. The VM has a 1.5 CPU share and tight memory, so two builds running their full suites at once mostly make each other slower. tq makes them take turns: only one queued job runs at a time, machine wide.

State lives in `state/` beside the tool (override with the `TQ_STATE_DIR` environment variable, which the tests use). Each waiting job is a ticket file in `state/queue/`, carrying an arrival number handed out under a short lock. The runner holds an `flock` on `state/runner.lock` for the whole run. The lock dies with the process, and tickets left behind by dead processes are recognised by pid and dropped, so a crashed build can never wedge the queue.

One standing rule is built into the queue. Standing rule from Captain JP (2026-11-15): Citeline is the most important build, and its testing always goes to the front of the line. Any waiting job whose project name contains "citeline" (case-insensitive) dequeues before every waiting non-Citeline job, no matter when it arrived. Within each class the order is first in, first out. A job that is already running is never preempted; the rule only reorders the wait.

The files: `tq.py` is the tool, Python standard library only. `tq` is a thin executable wrapper for `tq.py`. `test_tq.py` is the test suite, written before the tool. `PROOF.md` is a recorded live run showing the priority rule, the serialization, and exit code propagation.

## Example

Three jobs are submitted concurrently, in this order: other-a (project crucible) first, other-b (project metrics) second, citeline-job (project citeline) last. other-a is already running and is not preempted. Of the two waiting jobs, citeline-job runs before other-b even though other-b arrived first, because the Citeline rule reorders the wait. No two jobs overlap. other-b's command exits with code 5 on purpose, and tq exits 5 for other-b and 0 for the other two, so each submitter sees its own command's exit code. This run is recorded in full in `PROOF.md`.

## How to use it

Wrap the suite command:

```
~/workspace/tools/test-queue/tq run --project citeline -- python3 -m pytest
```

`tq run` submits the job, waits until its turn comes, runs the command, and exits with the command's own exit code, so scripts and coordinators can treat it exactly like running the suite directly. The `--project` name is what the priority rule reads; pass the build's own project name.

Check the line at any time:

```
~/workspace/tools/test-queue/tq status
```

It prints the running job, then the waiting jobs in the order they will run.

Run the tool's own test suite with `python3 -m unittest test_tq -v`.

## For agents

Agent use differs in one respect: an agent or coordinator does not run its suite directly, it wraps the suite command in `tq run` and passes its own build's project name, because that name is what the Citeline rule reads. The wrapped run then behaves exactly like a direct run, including the exit code. A Citeline coordinator's jobs carry a project name containing "citeline", so they dequeue ahead of every waiting job from other builds.

Example: a coordinator for the Crucible build runs `~/workspace/tools/test-queue/tq run --project crucible -- python3 -m pytest`. The job waits until the running job finishes and any waiting Citeline job has run, then the suite runs and the coordinator reads tq's exit code as the suite's own.
