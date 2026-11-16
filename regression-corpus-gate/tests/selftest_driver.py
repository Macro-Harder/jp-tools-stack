"""Test driver for the self test fault injection seam of plan part 4.8.

This driver imports the program file as a module and calls its entry point
with one probe named as the forced failure. It is a test side artefact only.
The command line entry point always passes the value none for the seam, so no
run argument, input file, or environment variable can reach it.

Usage: python3 selftest_driver.py PROBE_NAME ARGUMENTS_FILE RESULTS_FILE
ARGUMENTS_FILE holds one command line argument per line, without the program
name. RESULTS_FILE receives the exit status on its first line.
"""

import importlib.util
import inspect
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
WORK_DIR = TESTS_DIR.parent
PROGRAM = WORK_DIR / "staging" / "regression-corpus-gate" / "regression_corpus_gate.py"
if not PROGRAM.exists():
    PROGRAM = Path.home() / "workspace" / "tools" / "regression-corpus-gate" / "regression_corpus_gate.py"


def main():
    probe = sys.argv[1]
    args = Path(sys.argv[2]).read_text().splitlines()
    spec = importlib.util.spec_from_file_location("regression_corpus_gate", PROGRAM)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    entry = getattr(module, "main", None) or getattr(module, "run", None)
    if entry is None:
        raise SystemExit("the program module exposes no entry point for the seam driver")
    parameters = inspect.signature(entry).parameters
    if "forced_failure" in parameters:
        status = entry(args, forced_failure=probe)
    elif any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in parameters.values()) or len(parameters) >= 2:
        status = entry(args, probe)
    else:
        raise SystemExit("the program entry point accepts no forced failure value for the seam driver")
    Path(sys.argv[3]).write_text("%s\n" % status)
    return 0


if __name__ == "__main__":
    sys.exit(main())
