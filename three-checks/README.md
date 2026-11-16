# three-checks

## What it is

three-checks runs the three checks of R-80, authenticity, chain, and completeness, in that order, over the records of one stage closure, and reports the result in two roster parts together with every missing or broken link. A verifier other than the performer can rely on the recomputed result instead of on the filings taken at face value. The tool checks records. It does not perform the steps it checks, does not close the stage, does not record the stage state, and does not judge the quality of any artifact.

One run checks one stage closure. A whole build is checked by separate runs, one per stage, each producing its own report and results, and, on a full pass, its closure record. The program is one Python file, standard library only. A run makes no network call and reads no database. It reads only the bundle file and the artifact files the bundle names, and writes only its three named outputs.

### The three checks

Authenticity applies to every presented link. Each link must bind to exactly one spawn record for its performer identity, the spawn record creation time must stand at or before the step run time, a roster entry must authorise the seat for the performer at or before the run time, and a seat added under R-50 outside the advance layout must carry a republication at or before the run time. Origin tests run for the roster and push record kinds: the roster must come from runtime spawn records and the push record from API verification at assembly.

Chain compares each pair of consecutive layout steps: the outputs of the earlier step matching links must match the inputs of the later step matching links on every material name and digest. Where the claim names predecessor inputs, the boundary comparison checks them against the previous stage outputs under the same rule.

Completeness has three subresults. Links: every layout step needs at least one matching link, where a matching link passes authenticity and was produced within the step run and completion times, with a production time present. Artifacts: every required artifact must stand at its path, within the size limit, with the stated digest, be named by a presented link with the stated digest, and hold every stated property. Ledger: every element the claim asserts must appear in the path ledger entries.

### Bundle format in summary

The bundle is one JSON object in one file, read once as bytes under a limit of 2000000 bytes. Field sets are closed at every level: a field outside its set is an input error. The top level sections, in order, are layout, roster, links, spawn_records, identities, claim, push_record, previous_stage, and ledger_entries. The first six are required. A required section that is absent is reported under the code ABSENT-SECTION and the affected checks cannot run or fail, as the absence rules state. Times are strings in ISO 8601 UTC form with a Z suffix. Digests are compared in the form of SHA-256 as 64 lowercase hex characters.

#### Field lists per section

The lists below give the fields of every section and of every nested form. The closed set rule stated above applies at every level: a field outside its closed set is an input error naming the field by its full path. General rules that apply with the lists: times are strings in ISO 8601 UTC form with a Z suffix; digest fields are strings compared in the form of SHA-256 as 64 lowercase hex characters; a JSON boolean is never an integer.

Section layout, fields: stage_id (string, required); steps (list, required, at least one entry); required_artifacts (list, may be empty); record_sources (list, may be empty).

Nested layout steps entry, fields: step_id (string); seat (string); predicate_type (string).

Nested layout required_artifacts entry, fields: artifact_id (string); path (string, relative paths resolve against the directory containing the bundle file); sha256 (digest string); properties (list, may be empty).

Nested layout properties entry, fields: kind (string); line (string); count (integer at least 0); sha256 (digest string). Which of line, count, and sha256 a given kind may carry is stated in the property kinds table below.

Nested layout record_sources entry, fields: record_kind (string, one of roster, push, links, claim, ledger); source (string, from the closed set for its kind: roster takes runtime-spawn-records or self-reported-file; push takes api-verification or self-reported-file; links, claim, and ledger take stage-record or self-reported-file).

Section roster, fields: entries (list, required); republications (list, may be empty).

Nested roster entries entry, fields: seat (string); agent_id (string); recorded_at (time string); origin (string, one of layout, addition).

Nested roster republications entry, fields: seat (string); republished_at (time string).

Section links, a list, required. Each entry fields: step_id (string); predicate_type (string); performer_spawn_id (string); builder (string); produced_at (time string, the one optional field in this set, may be absent); ran_at (time string); inputs (material list); outputs (material list); subject_artifacts (list, may be empty).

Nested material list entry, used by inputs, outputs, claim predecessor_inputs, and previous_stage outputs, fields: name (string); sha256 (digest string).

Nested subject_artifacts entry, fields: artifact_id (string); sha256 (digest string).

Section spawn_records, fields: exporter (string, required); exported_at (time string, required); source_database (string, required, with the convention stated in the spawn export specification section below); scoping (object, required); records (list, required).

Nested scoping object, fields: method (string, one of identity_list, parent_subtree, time_window); detail (string).

Nested records entry, fields: agent_id (string); parent_agent_id (string); depth (integer at least 0); kind (string); agent_type (string or null); session_id (string); created_at (time string).

Section identities, fields, all required: coordinator (string); commissioner_stage (string); commissioner_work (string).

Section claim, fields: stage_id (string, must equal layout stage_id); steps_claimed (list of strings); step_completions (list, required); gate_context (string or null, may be absent and then treated as null); push_link (object or null); predecessor_inputs (material list or null); ledger_claims (list of strings, may be empty).

Nested step_completions entry, fields: step_id (string); completed_at (time string).

Nested push_link object, fields: repo (string); head_sha (string); tree_sha (string).

Section push_record, conditional, fields: repo (string); branch (string); head_sha (string); tree_sha (string); verified_by (string); verified_at (time string).

Section previous_stage, conditional, fields: stage_id (string); outputs (material list).

Section ledger_entries, conditional, a list. Each entry fields: entry_id (string); text (string).

#### Property kinds

The evaluated property kinds are exactly seven: exists, sha256_equals, contains_line, first_line_equals, line_count_at_least, line_count_at_most, and byte_size_at_most. A property whose kind is none of the seven is an unsupported property: it fails the artifacts subresult under code COMP-UNSUPPORTED-PROPERTY at check time, and it is never an input error at validation, because kind is a plain string at validation.

Per kind fields, from the closed property field set of kind, line, count, and sha256:

- Kind exists carries no other field. Only kind is present. Meaning: the file is readable.
- Kind sha256_equals requires sha256, and carries no line and no count. Meaning: the SHA-256 of the file bytes equals the property sha256.
- Kind contains_line requires line, and carries no count and no sha256. Meaning: some line of the file equals the stated line.
- Kind first_line_equals requires line, and carries no count and no sha256. Meaning: the first line equals the stated line and an empty file fails.
- Kind line_count_at_least requires count, and carries no line and no sha256. Meaning: the line count is compared with the stated count.
- Kind line_count_at_most requires count, and carries no line and no sha256. Meaning: the line count is compared with the stated count.
- Kind byte_size_at_most requires count, and carries no line and no sha256. Meaning: the byte size is compared with the stated count.

A missing required field for an evaluated kind, or a field present that its kind does not carry, is an input error naming the field path.

A line is the file bytes decoded as UTF-8 and split on the newline character, a carriage return at the end of a line is not part of the line, a trailing newline adds no empty final line, and an empty file has zero lines and no first line.

#### Reading the two roster parts

The report lists steps in two parts by seat origin. Part 1, advance layout seats, lists the steps whose seat authorising entry has origin layout. Part 2, seats added under R-50, lists the steps whose seat first authorisation came by an entry with origin addition, and its step lines for a seat outside the advance layout carry a republished field before the authenticity field. A seat appears in exactly one part, and a step is listed in the part of its seat. Chain join lines are printed after the step lines of the part that holds the earlier step of the join. A part with no steps prints its heading and no lines, so an empty part 2 is the normal form for a stage with no added seats, and an empty part 1 is the normal form for a stage whose seats were all added.

### Spawn export specification in summary

The spawn_records section is the runtime spawn export. Its join to the bundle is the performer identity: a link performer_spawn_id must equal the agent_id of exactly one record in the export. Each record carries agent_id, parent_agent_id, depth, kind, agent_type, session_id, and created_at. The creation time conversion is the anchor of the time test: created_at is read as an ISO 8601 UTC instant and must stand at or before the ran_at of every link that binds the record. The scoping record states how the export was scoped: the scoping method, one of identity_list, parent_subtree, or time_window, with its detail, alongside the exporter identity, the exported_at time, and the source_database name, all printed in the report provenance block. The seat mapping bound: the export carries no seat. The association of a performer identity with a seat rests on the roster record, and no report text describes that association as runtime captured.

The source_database field is a provenance string naming the database the spawn export was taken from, as the export itself records it. It carries no closed set of allowed values, no check reads it, and it is printed unchanged in the report provenance block and in the results provenance object. Convention for this estate: where the export comes from the runtime database and that database carries no formal name of its own, write the value runtime. Where an export source does carry a formal database name, copy that name exactly. The shipped example bundle value spawn-db is an example placeholder only and must not be copied into a real bundle.

### Push assembly verification in summary

The push record is verified at bundle assembly, outside the tool, through two API reads: one read of the repository head, giving the head commit, and one read of the tree it points to. The attestation fields recorded in push_record are repo, branch, head_sha, tree_sha, verified_by, and verified_at. Branch is assembly provenance and is never a check input. Where the claim names a push link, its repo, head_sha, and tree_sha must equal the push record fields. The report provenance line states the push origin as api-verification at assembly.

### Strength bound

The checks count at the closure record L2 grade and no higher, and only where the origin tests passed. The seat association rests on the roster record. The spawn export is assembled under the verifier's direction, and the tool cannot prove an export genuine: it recomputes the checks over the records it is given, and its result is only as strong as the assembly that produced the bundle. Provenance attests how the stage artifacts were produced; it is not evidence of their quality. No strength above grade L2 is claimed, and the tool never issues per link grade labels.

### Output format notes

Interpretation (OP-3): the brief fixes the report content in its fixed lines and fixes the write order, and does not state line endings, a final newline, or JSON indentation. This build reads OP-3 as follows: every output file is UTF-8 without a byte order mark, uses the newline character alone as its line ending, and ends with exactly one final newline. The results file is JSON written with two space indentation, with keys in the order the brief lists them, and non ASCII characters written directly rather than escaped. This paragraph is marked as an interpretation under OP-3, as the plan requires.

### Discrepancy codes

The discrepancy code list lives in this README. It changes only by adding codes, never by reusing one.

- ABSENT-SECTION: a required section absent, subject the section name.
- AUTH-NO-SPAWN: no spawn record, or more than one, for a link performer identity, or a duplicated export identity.
- AUTH-NO-ROSTER: no roster entry authorising the link seat for its performer.
- AUTH-STEP-TIME: spawn creation later than the step run time, or a time anchor that cannot be made.
- AUTH-LATE-RECORD: roster recording later than the step run time, where an authorising entry exists only late.
- AUTH-NO-REPUB: no republication at or before the step run time for an outside seat.
- AUTH-NO-PUSH: a push link in play with no push record.
- AUTH-ORIGIN: a record kind failing its origin test, a kind with no origin pass where one is required, or a push field mismatch.
- LINK-NO-STEP: a presented link naming no layout step.
- CHAIN-JOIN: a step join failing, or unable to run for a missing link.
- CHAIN-BOUNDARY: the stage boundary comparison failing or unable to run.
- COMP-NO-LINK: a layout step with no matching link, or a claim and layout step divergence.
- COMP-RECONSTRUCTED: a presented link that is not a link, produced after the step completion, produced before the step ran, carrying no production time, or untestable for want of a recorded completion time.
- COMP-ARTIFACT: a required artifact failing a standing test or its layout link coverage.
- COMP-PROPERTY: a stated property failing.
- COMP-UNSUPPORTED-PROPERTY: a stated property outside the evaluated kinds.
- COMP-LEDGER: a closure claim element with no path ledger entry.
- LINK-PREDICATE: a presented link whose predicate type differs from its layout step.
- ANOM-MULTI-LINK: more than one matching link for a step, reported, not a failure.

## Example

Warm up on the shipped example before checking a real stage. From the tool folder, run:

```
python3 three_checks.py examples/example_bundle.json warm_report.txt warm_results.json warm_closure.txt --verifier verifier-1
```

The verifier identity verifier-1 is the identity the shipped expected pair was authored with, as the expected report shows. The expected result is exit status 0, warm_report.txt equal to examples/expected_report.txt byte for byte, warm_results.json equal to examples/expected_results.json field for field, and a closure record written to warm_closure.txt. The warm up output paths must not name any input file, in line with the output path rule in How to use it.

## How to use it

```
three-checks BUNDLE REPORT RESULTS CLOSURE --verifier IDENTITY
```

BUNDLE is the stage record bundle. REPORT is the text report path, RESULTS the JSON results path, and CLOSURE the attested closure record path. The closure file is written only on a full pass. A failing or barred run creates no closure file and leaves any existing file at that path untouched. IDENTITY is the verifier identity, supplied as a run argument and never read from the bundle. Output files are written only to the named paths and never overwrite an input file. The write order is fixed: REPORT first, then RESULTS, then CLOSURE.

The tool is a single Python file and no install step exists. Run it as `python3 three_checks.py BUNDLE REPORT RESULTS CLOSURE --verifier IDENTITY`, working in the folder that holds three_checks.py, or naming the full path to three_checks.py in place of the file name. The bare form three-checks in the usage line above is a shorthand for that file invocation, not a separately installed command. The exit statuses and argument rules in this section apply unchanged to this form.

Exit statuses:

- 0: full pass.
- 1: checks failed, consequence PARTIAL.
- 2: input error, delivery failure, or usage error, each named distinctly on standard error.
- 3: checks failed, consequence UNVERIFIABLE.
- 4: barred run. The verifier is the performer, the coordinator, or a commissioner, so the run is barred and issues no check results. A barred run writes the barred report to REPORT and no results file.

### Assembly checklist

Work through this checklist when assembling a bundle. A conditionally required section that is absent makes the affected check fail under its own code; it is never an input refusal.

- Always include layout, roster, links, spawn_records, identities, and claim.
- Include push_record when the claim names a push link (claim push_link is not null), and when layout record_sources names the push kind. Where neither stands, push_record is not required, and a present push_record with no push link in play is reported as supplied and not tested.
- Include previous_stage when the claim names predecessor inputs (claim predecessor_inputs is not null). Where predecessor_inputs is null or an empty list, no boundary comparison arises.
- Include ledger_entries when the claim ledger_claims list is not empty. Where ledger_claims is empty, ledger_entries is not required.
- In layout record_sources, name the roster kind with source runtime-spawn-records and, where a push link is in play, the push kind with source api-verification. A kind named self-reported-file fails its origin test, and a roster kind with no entry fails for want of an origin pass.
- Give every layout step a step_id, a seat, and a predicate_type, in step order, with no duplicated step_id.
- Give every required artifact an artifact_id, a path, and the SHA-256 of its bytes. A relative artifact path resolves against the directory containing the bundle file.
- Record a completion time in claim step_completions for every claimed step, or the reconstruction test cannot run for that step and its links do not count as matching.
- Keep the bundle at or under 2000000 bytes, as UTF-8 text without a byte order mark.

## For agents

Agent use differs because the verifier is an agent acting on a stage it did not perform. The agent assembles the bundle under its own direction, working through the assembly checklist, supplies its own identity as the `--verifier` argument (the identity is never read from the bundle), and relies on the recomputed result instead of on the filings taken at face value. An agent that performed a step in the stage, coordinated it, or commissioned it cannot verify that stage: such a run is barred, exits with status 4, writes the barred report, and issues no check results.

Example: a verifier agent that took no part in a stage assembles the stage's bundle, then runs `python3 three_checks.py bundle.json report.txt results.json closure.txt --verifier verifier-1`. Exit status 0 is a full pass, and the closure record stands at closure.txt. Had the same agent coordinated the stage, the run would have been barred at exit status 4.
