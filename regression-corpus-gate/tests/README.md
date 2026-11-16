# regression-corpus-gate test suite

## How to run

From the tool build working folder:

```
TMPDIR=~/.tmp python3 -m unittest discover -s tests
```

Standard library only. The suite runs the program as a subprocess through
its command line, at the staging program path
staging/regression-corpus-gate/regression_corpus_gate.py, or at the landed
path ~/workspace/tools/regression-corpus-gate/regression_corpus_gate.py
where the staging file does not stand.

## Group map

- test_t01.py: T1 usage and paths
- test_t02.py: T2 reading, limits, and fingerprints
- test_t03.py: T3 corpus parsing and integrity
- test_t04.py: T4 amendment and declaration syntax
- test_t05.py: T5 attestations, second attester, and triggers
- test_t06.py: T6 tripwire
- test_t07.py: T7 selection and readback
- test_t08.py: T8 self test, with selftest_driver.py as the seam driver
- test_t09.py: T9 worksheet and template
- test_t10.py: T10 barred runs
- test_t11.py: T11 verdicts parsing and binding
- test_t12.py: T12 flagged rows and panel discipline
- test_t13.py: T13 re-ruling verification
- test_t14.py: T14 arithmetic, counts, and precedence
- test_t15.py: T15 outcomes, exit statuses, and the output matrix
- test_t16.py: T16 report forms and JSON
- test_t17.py: T17 remaining form
- test_t18.py: T18 limits and never do rules
- test_t19.py: T19 examples and README
- test_mutations.py: the ten named mutations on the shipped example set
- test_transcription.py: transcription structure tests, which pass without
  the program
- rcg_common.py: shared helpers and the test side transcriptions
- fixtures/: copied real corpus and queue excerpts, with FIXTURE-NOTE.md

## Recorded results

The stage 13 run record stands in tests-stage13.md in the tool build working
folder.
