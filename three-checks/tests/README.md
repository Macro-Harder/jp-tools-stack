# Tests for three-checks

Stage 13 test suite for the three-checks tool. Tests come first: this suite pins the behaviour the stage 14 build must meet. The program under test is three_checks.py in the parent folder, run as a subprocess. Python standard library only, unittest only.

## How to run

From the landing folder, ~/workspace/tools/three-checks:

- Full suite: python3 -m unittest discover -s tests -t tests
- One group: python3 -m unittest discover -s tests -t tests -k t15 (pattern form), or python3 -m unittest test_t15_chain -v with the tests folder as the working directory.
- Named subsets for stage 14 build steps, by the step scopes in plan part 5: step 1 runs test_t01_usage (minus the artifact path collision case); step 2 adds test_t02_reading_gates and the two surrogate cases of test_t03_scalar_kinds; step 3 adds the rest of test_t03_scalar_kinds, test_t04_field_validation, test_t05_duplicates (minus the two duplicated agent_id cases), test_t06_property_validation (validation aspect), and the T1 artifact collision case; step 4 adds the shape aspect of test_t07_absence and the malformed case of test_t08_conditional; step 5 adds test_t09_barred (barred outcomes), and the shape aspects of test_t10 to test_t14, with golden/authorisation_record.json; step 6 adds the shape aspects of test_t15_chain, test_t16_boundary, and test_t17_matching, with golden/matching.json; step 7 adds test_t18_artifacts and test_t19_ledger shape aspects and the check time aspect of the T6 unsupported case, with golden/completeness_result.json; step 8 adds test_t20_consequence_ordering, the form cases of test_t21_report_results, the closure cases of test_t22_closure_delivery, and every case deferred from steps 4 to 7; step 9 adds the delivery cases of test_t22_closure_delivery and the rest of test_t21_report_results except the examples regeneration test; step 10 adds test_mutations, test_t23_limits, and the examples regeneration test in test_t21_report_results.

## Module structure

One module per test group, plus shared and pure modules:

- helpers.py: the subprocess harness, the synthetic base bundle builder, and shared assertions. While three_checks.py is missing, every program exercising test fails cleanly through helpers.require_program with the line: missing program, followed by the program path, and the note that this is the expected failure at stage 13. A missing program never surfaces as a test error or a traceback from the harness itself.
- test_t01_usage.py: T1, argument and usage, including symlink and realpath cases.
- test_t02_reading_gates.py: T2, reading gates in gate order, including the depth 10000 object nesting case asserted only as the invalid JSON line form.
- test_t03_scalar_kinds.py: T3, JSON strictness and scalar kinds, including the two surrogate gate cases under R9-2.
- test_t04_field_validation.py: T4, closed sets, paths, allowed sets, ordering, and the claim stage_id mismatch case.
- test_t05_duplicates.py: T5, duplicate keys at every level, duplicate identifiers, and the two duplicated agent_id check cases.
- test_t06_property_validation.py: T6, per kind property field rules at validation.
- test_t07_absence.py: T7, absence matrix, generated per required section from the test side absence transcription, plus hand written combinations and the R9-5 and R9-6 cases.
- test_t08_conditional.py: T8, conditional sections and their triggers.
- test_t09_barred.py: T9, barred runs, precedence, fallbacks, and untouched files.
- test_t10_auth_binding.py: T10, authenticity binding and time anchor, including R8-6 and R12-2 cases.
- test_t11_roster.py: T11, roster authorisation and the R8-1 per step recorded selection.
- test_t12_repub_part.py: T12, republication and part assignment, including R8-2, R9-3, and R9-7 cases.
- test_t13_origin_push.py: T13, origin and push tests.
- test_t14_unparseable.py: T14, unparseable times per field, the express time form cases of C-8, and out of form digests.
- test_t15_chain.py: T15, chain joins, multiplicity, duplicated names, and the R9-4 overlap cases.
- test_t16_boundary.py: T16, boundary comparison and the R9-5 absence cases.
- test_t17_matching.py: T17, completeness matching and reconstruction, including R8-5.
- test_t18_artifacts.py: T18, line definition, standing tests, coverage, properties, and filesystem cases.
- test_t19_ledger.py: T19, ledger support.
- test_t20_consequence_ordering.py: T20, empty lists, consequence, ordering, and the OP-4 cure text and per code consequence asserted for one entry of each of the 19 codes against the transcriptions.
- test_t21_report_results.py: T21, report form, results form, translation table, version literal 1.0.0 asserted without importing the program, the hand written final newline pin, the examples pair regeneration test, and README content assertions.
- test_t22_closure_delivery.py: T22, closure record, write order, and delivery failures, with directory paths used for unwritable cases under C-5.
- test_t23_limits.py: T23, limits of the tool that carry test cases. The remaining brief section 9 rules are inspection only, as the plan marks them, and no test case is claimed for them.
- test_mutations.py: the named mutation list of plan part 4, ten cases, each one field changed on the hand authored examples pair bundle, each with its hand stated exit status and code, and each asserting no extra code appears.
- test_transcriptions.py: pure structure tests that pass without the program: transcription completeness, golden shape structure, fixture existence, and fixture note contents.
- test_stage19_coverage.py: stage 19 fix round coverage for the eight partial trace items U1 to U8: R17-2 rendering positions and trigger characters, gate_context propagation and the deleted key case, non string time values, the dual standing entry artifact case, results raw byte form, the OP-4 expected texts for the remaining 18 codes, a surrogate inside a discarded duplicate value, and README content beyond the code list and the five phrases.

## Transcriptions, held in transcriptions/

Test side transcriptions, written from the brief and the plan, independent of any program constants:

- absence_table.json: the brief section 7 absence table, one row per required section, read by the generated cases in test_t07_absence.py.
- consequence_table.json: the brief section 7 per code consequence table for all 19 codes, with the two conditional notes for AUTH-NO-SPAWN and AUTH-NO-ROSTER, read by test_t20_consequence_ordering.py.
- part_assignment_table.json: the plan part 2.6 per code part assignment table with its subject column, read by test_t20_consequence_ordering.py and test_transcriptions.py.
- oracle_literals.json: SHA-256 literals for fixed byte strings (empty, hello, 32 zero bytes, and the artifact one contents), computed outside the tool and recorded here, never produced by the code under test.
- time_pairs.json: a time pair table stating pair, expected relation, and expected parse success, covering fractional seconds and the rejection shapes of plan part 1.6.

## Golden shape files, held in golden/

Hand authored expected shapes, named in the step scopes of plan part 5: authorisation_record.json (step 5), matching.json (step 6), completeness_result.json (step 7). At stage 13 the pure tests assert their structure and required keys. Direct shape assertions against the program parts land with the stage 14 steps that build those parts, because the program is exercised here only as a subprocess.

Fields the golden files do not pin, recorded expressly. The golden files are subsets of the plan shapes they pin. For plan part 2.3, the authorisation record golden does not pin: the binding spawn record, the spawn created_at, the roster entries considered, the authorising entry, the governing republication, and the part assignment input. For plan part 2.4, the matching golden does not pin: the layout step object, the presented links, the reconstruction outcome per presented link, the matching links list itself (it pins a matching link count only), and the predicate mismatch links list itself (it pins a predicate mismatch count only). For plan part 2.5, the completeness golden does not pin: the export facts lists (the duplicated export identities, and the unbound unparseable creation facts), the authenticity result fields beyond the completeness shape (its origin outcomes, its full pass origin facts, and its stage level entry lists), the chain result fields (the join outcomes, the boundary outcome, and its entries), the completeness links subresult entries and anomaly entries, and the per artifact property outcomes in stated order (the golden example carries an empty property list). The completeness golden does pin the per claimed element ledger outcomes and the per artifact standing outcomes, as plan part 2.5 states. Carry forward condition: at stage 14 steps 5 to 7, where the direct shape tests land, those tests must assert the full field lists of plan parts 2.3 to 2.5, not only the golden subsets, or this deferral becomes a permanent weakening. The golden files are not expanded at stage 13.

## Fixture inventory and provenance

All fixtures live under fixtures/. The full fixture note for the copied real text fixtures is fixtures/FIXTURE_NOTE.md.

Bundle fixtures, fixtures/bundles/, all synthetic, hand built to the closed field sets of brief section 3, because no real R-79 stage bundle exists to copy:

- passing_minimal.json: the smallest passing bundle, same shape as the helpers base bundle.
- missing_claim.json: the passing bundle with the claim section removed.
- unknown_top_field.json: the passing bundle with one unknown top level field.
- empty_steps.json: the passing bundle with an empty layout steps list.
- duplicate_key.json, nan_token.json, infinity_token.json, not_json.txt, top_level_list.json, deep_nesting.json, surrogate_value.json: raw gate and strictness fixtures.

Artifact fixtures, fixtures/artifacts/, synthetic except the two copied excerpts:

- artifact1.txt: two lines, trailing newline, digest recorded in oracle_literals.json as artifact_one.
- empty.txt, no_trailing_newline.txt, crlf.txt (carriage return at each line end, synthetic), exact_line.txt, non_utf8.bin.
- copied_brief_excerpt.txt and copied_plan_excerpt.txt: copied real text, first 40 lines of the three-checks brief and plan in the build-flow-skills design folder, frozen at creation on 2026-11-14 and never refreshed. Traits checked against their bytes and listed in fixtures/FIXTURE_NOTE.md: each ends with a trailing newline and contains no carriage return. No copied fixture contains a carriage return line end, so no test claims that trait for a copied fixture.
- fixtures/expected_final_newline.txt: the hand written expected file pinning the OP-3 choice, a single line ending with exactly one final newline.

Unreadable and unwritable cases use a directory path or a missing file, never permission bits, because this environment runs as uid 0 and a mode 0 file still reads there (condition C-5). Each such case is covered by the fixture note.

Most program exercising tests build their bundle in a temporary directory from the helpers base bundle with one named change per case, so each case stays minimal and its change is stated in the test. Generated artifact contents in test_t18_artifacts.py (the over limit block, the non UTF-8 block, and the symlink to bundle case) have their digests computed in the test only to construct the input bundle. In the terms of the oracle rule of plan part 4, those computations are construction only: they state an input, and no expected outcome is derived from them. Expected digests are the literals recorded in transcriptions/oracle_literals.json, computed outside the tool, and one T18 standing test takes its stated digest from the artifact_one oracle literal in that file. The T14 form and relation cases are driven by the recorded table in transcriptions/time_pairs.json, which states each pair, its expected relation, and its expected parse success.

## Examples pair and README

The hand authored examples pair is not written at this stage; it lands at build step 10, with the shipped README. The regeneration test in test_t21_report_results.py, the README content test in the same module, and all ten cases in test_mutations.py are present now and fail only because that pair, the README, or the program is missing. Their failure messages name the missing companion file.

## Suite result after the stage 19 fix round

- Ran 510 tests. Result: FAILED, failures 1, errors 0. The count is the 469 tests of the stage 19 audit plus the 41 tests of test_stage19_coverage.py (U1 10, U2 2, U3 2, U4 1, U5 1, U6 18, U7 2, U8 5).
- The one failure is the U4 test, test_over_limit_and_digest_mismatch_both_entries_stand in test_stage19_coverage.py. On an artifact of 2000001 bytes whose stated digest does not match its bytes, the run produced exactly one COMP-ARTIFACT entry for the artifact, the size entry, and no digest entry, where the brief and the plan state that every failing standing test is reported as its own entry. The test stands as written and the failure is recorded in the stage 19 fix record as a suspected program defect. No program file was changed in this round.

## Suite result after the stage 14 test repair round

- Ran 432 tests. Result: OK, all passing, failures 0, errors 0. Recorded after the stage 14 test repair round that repaired defects D-1, D-2, and D-3 in the tests only, with no change to the program.

## Suite result at stage 13

Recorded on 2026-11-14, after the stage 13 test audit fix round, with three_checks.py, the examples pair, and the shipped README all absent, using the full suite command above:

- Ran 425 tests. Result: FAILED, failures 416 entries, errors 0.
- 12 tests pass: the 11 pure tests in test_transcriptions.py and the time pair table shape test in test_t14_unparseable.py.
- 413 test cases fail. Every failure entry traces to the missing program (404 entries, including the 4 subtest entries of the one boundary absence case in test_t16_boundary.py) or to a missing shipped companion (12 entries: the 10 named mutations, the examples regeneration test, and the README content test). No failure has any other cause, and there are no errors.

## Test counts by group

Counts of test cases per module, 425 in total: T1 usage 15, T2 reading gates 15, T3 scalar kinds 11, T4 field validation 28, T5 duplicates 16, T6 property validation 31, T7 absence 19, T8 conditional 9, T9 barred 15, T10 authenticity binding 12, T11 roster 10, T12 republication and part 14, T13 origin and push 18, T14 unparseable 34, T15 chain 16, T16 boundary 14, T17 matching 17, T18 artifacts 37, T19 ledger 6, T20 consequence and ordering 31, T21 report and results 20, T22 closure and delivery 8, T23 limits 8, named mutations 10, transcriptions 11.

## Genuine gaps recorded

- Cross suite output scans: plan group T23 speaks of scans across the suite outputs. A single unittest process cannot see the outputs other modules produced in their own processes and temporary folders, so test_t23_limits.py scans the outputs it produces itself, and the wording assertions it can make locally. A literal whole suite scan would need a shared output registry the plan does not name. Recorded as a gap, not silently claimed.
- Mutation 3: recheck completed at step 10 against the actual pair, per the build record. The moved roster entry is the single authorising entry for the mutated seat in the examples pair, and moving its recorded time to one second after the S1 link ran_at produces AUTH-LATE-RECORD with exit status 1, as stated. The case outcome stands as rechecked. Its code set assertion was corrected in the stage 14 test repair round to include the cascade codes the brief mandates.
- Shape level assertions: plan part 5 scopes the shape aspects of groups T10 to T19 to steps 5 to 7 against the program internal shapes. This suite exercises the program only as a subprocess, as the brief invocation fixes, so those groups here assert the entry codes, subjects, checks, consequences, and results fields that the shapes determine, and the golden files pin the shape content. Direct internal shape tests are a stage 14 step concern, recorded here so the deferral is visible. Carry forward condition for this gap (G-3): the golden files are subsets of the plan shapes, as recorded in the golden shape files section above, so the stage 14 steps 5 to 7 shape tests must assert the full field lists of plan parts 2.3 to 2.5, not only the golden subsets, or the deferral becomes a permanent weakening.
- Recorded reading for the republication subtest (F-04): the brief and the plan agree. A seat stands in the advance layout for a link only where an origin layout entry for the seat has recorded_at not later than ran_at. A layout entry recorded after ran_at is a later layout entry: it never makes the seat stand and never exempts the seat from the republication subtest (d). The case test_later_layout_entry_addition_still_needs_repub in test_t12_repub_part.py carries this reading, with its layout entry recorded at 2026-01-01T13:00:00Z, after ran_at, and the AUTH-NO-REPUB expectation stands for it.
- No other gap was found between the plan test plan and what could be written. Every case named in groups T1 to T23 and every named mutation has a test above.
